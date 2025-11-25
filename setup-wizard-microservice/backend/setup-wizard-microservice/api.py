import json
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from datetime import datetime

from models import (
    Base, Company, Zone, Device, Entity,
    Setup, SetupSchedule, TemperatureRule, Decision, Rule
)
from config import SQLALCHEMY_DATABASE_URI
from ha_ws_client import get_ha_areas, get_ha_devices, get_ha_entities
from ha_client import get_states, extract_device_id

bp = Blueprint("api", __name__, url_prefix="/api")

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False}
)
Base.metadata.create_all(engine)

def session():
    return Session(engine)


# ============================================================
#   COMPANY — STEP 1 OF SETUP
# ============================================================
@bp.route("/setup/company", methods=["GET"])
def get_company():
    """Return the (single) company if exists."""
    db = session()
    company = db.query(Company).first()

    if not company:
        return jsonify({"exists": False})

    return jsonify({
        "exists": True,
        "company": {
            "id": company.id,
            "name": company.name,
            "address": company.address,
            "phone": company.phone,
            "email": company.email,
            "city": company.city,
            "country": company.country
        }
    })


@bp.route("/setup/company", methods=["POST"])
def create_company():
    """
    Create the single company.
    Only allowed if no company exists.
    """
    db = session()
    exists = db.query(Company).count() > 0
    if exists:
        return jsonify({"error": "Company already exists"}), 400

    payload = request.json
    if not payload.get("name"):
        return jsonify({"error": "company name required"}), 400

    company = Company(
        name=payload.get("name"),
        address=payload.get("address"),
        phone=payload.get("phone"),
        email=payload.get("email"),
        city=payload.get("city"),
        country=payload.get("country")
    )
    db.add(company)
    db.commit()

    return jsonify({"created": True, "company_id": company.id})


@bp.route("/setup/company", methods=["PUT"])
def update_company():
    """Update only modified fields in the existing company."""
    db = session()
    company = db.query(Company).first()

    if not company:
        return jsonify({"error": "Company not found"}), 404

    payload = request.json
    updated = False

    for field in ["name", "address", "phone", "email", "city", "country"]:
        if field in payload and getattr(company, field) != payload[field]:
            setattr(company, field, payload[field])
            updated = True

    if updated:
        company.updated_at = datetime.utcnow()
        db.commit()

    return jsonify({"updated": updated})

# ---------------------------------------------------------
#               HOME ASSISTANT SUMMARY
# ---------------------------------------------------------
@bp.route("/ha/summary", methods=["POST"])
def ha_summary():
    """
    Returns a complete HA summary:
    Zones -> Devices -> Entities

    - Uses HA registries (areas, devices, entities) as the source of truth
      for the hierarchy and relations.
    - Persists Device.ha_device_id as the canonical Home Assistant device_registry.id.
    - Uses /api/states only for dynamic data: state, friendly_name, unit, etc.
    """

    # -----------------------------------------------------
    # Parse and validate input
    # -----------------------------------------------------
    db = session()

    company = db.query(Company).first()
    if not company:
        return jsonify({"error": "No company defined"}), 400

    # ----- Try to get HA data -----
    try:
        areas = get_ha_areas()
        devices_reg = get_ha_devices()
        entities_reg = get_ha_entities()
        states = get_states()
    except Exception:
        return build_db_fallback(db)

    now = datetime.utcnow()

    # Lookup maps
    state_map = {s["entity_id"]: s for s in states}
    dev_reg_map = {d["id"]: d for d in devices_reg}
    ent_reg_map = {e["entity_id"]: e for e in entities_reg}

    db_devices = {d.ha_device_id: d for d in db.query(Device).all()}
    db_entities = {e.entity_id: e for e in db.query(Entity).all()}

    # ---------------------------------------------------------
    #  UPSERT DEVICES + ENTITIES
    # ---------------------------------------------------------
    for ent_reg in entities_reg:
        eid = ent_reg.get("entity_id")
        if not eid:
            continue

        ha_dev_id = ent_reg.get("device_id")
        state = state_map.get(eid)
        attrs = state.get("attributes", {}) if state else {}

        friendly = attrs.get("friendly_name") or ent_reg.get("name") or eid
        unit = attrs.get("unit_of_measurement") or ""
        last_state = state["state"] if state else None

        # ---- DEVICE ----
        dev = None
        if ha_dev_id:
            dev = db_devices.get(ha_dev_id)
            if not dev:
                reg = dev_reg_map.get(ha_dev_id, {})
                dev = Device(
                    ha_device_id=ha_dev_id,
                    name=reg.get("name") or ha_dev_id,
                    type=eid.split(".")[0],
                    last_sync=now
                )
                db.add(dev)
                db.flush()
                db_devices[ha_dev_id] = dev
            else:
                dev.last_sync = now
                db.add(dev)

        # ---- ENTITY ----
        ent = db_entities.get(eid)
        if not ent:
            ent = Entity(
                device=dev,
                entity_id=eid,
                friendly_name=friendly,
                unit=unit,
                last_state=last_state,
                last_updated=now
            )
            db.add(ent)
            db_entities[eid] = ent
        else:
            ent.device = dev
            ent.friendly_name = friendly
            ent.unit = unit or ent.unit
            ent.last_state = last_state
            ent.last_updated = now
            db.add(ent)

    db.commit()

    # ---------------------------------------------------------
    #  BUILD devices_map + ENTITIES OUT
    # ---------------------------------------------------------
    devices_map = {}
    entities_out = []

    for e in db.query(Entity).all():
        dev = e.device
        ha_dev_id = dev.ha_device_id if dev else None
        reg_ent = ent_reg_map.get(e.entity_id, {})
        reg_dev = dev_reg_map.get(ha_dev_id, {}) if ha_dev_id else {}

        area_id = reg_ent.get("area_id") or reg_dev.get("area_id")

        if dev:
            devices_map.setdefault(dev.id, {
                "id": dev.id,
                "name": dev.name,
                "ha_device_id": ha_dev_id,
                "type": dev.type,
                "area_id": area_id,
                "entities": []
            })

        payload = {
            "id": e.id,
            "entity_id": e.entity_id,
            "friendly_name": e.friendly_name,
            "unit": e.unit,
            "selected": bool(e.selected),
            "device_id": e.device_id
        }
        entities_out.append(payload)

        if dev:
            devices_map[dev.id]["entities"].append(payload)

    # ---------------------------------------------------------
    #  BUILD + UPSERT ZONES
    # ---------------------------------------------------------
    zones_final = []
    area_to_db_id = {}
    existing_zones = {z.area_id: z for z in db.query(Zone).filter(Zone.company_id == company.id)}

    for i, a in enumerate(areas, start=1):
        area_id = a.get("area_id")
        if not area_id:
            continue

        area_id = str(area_id).strip()

        if area_id in existing_zones:
            zone = existing_zones[area_id]
        else:
            zone = Zone(
                company_id=company.id,
                area_id=area_id,
                name=a.get("name") or area_id,
                description=a.get("description")
            )
            db.add(zone)
            db.flush()
            existing_zones[area_id] = zone

        area_to_db_id[area_id] = zone.id

        zones_final.append({
            "id": zone.id,
            "area_id": area_id,
            "name": zone.name,
            "description": zone.description,
            "devices": []
        })

    # -------------------------------
    # Attach devices to zones
    # -------------------------------
    for d in devices_map.values():
        area = d["area_id"]
        dev = db.query(Device).filter(Device.id == d["id"]).first()

        if area and area in area_to_db_id:
            zid = area_to_db_id[area]
            dev.zone_id = zid
            for z in zones_final:
                if z["id"] == zid:
                    z["devices"].append(d)
        else:
            dev.zone_id = None

    db.commit()

    return jsonify({
        "zones": zones_final,
        "devices": list(devices_map.values()),
        "entities": entities_out
    })


# ---------------------------------------------------------
# Fallback: no HA available
# ---------------------------------------------------------
def build_db_fallback(db):
    devices = []
    entities_out = []

    devices_map = {}
    for d in db.query(Device).all():
        devices_map[d.id] = {
            "id": d.id,
            "name": d.name,
            "ha_device_id": d.ha_device_id,
            "type": d.type,
            "area_id": None,
            "entities": []
        }

    for e in db.query(Entity).all():
        payload = {
            "id": e.id,
            "entity_id": e.entity_id,
            "friendly_name": e.friendly_name,
            "unit": e.unit,
            "selected": bool(e.selected),
            "device_id": e.device_id
        }
        entities_out.append(payload)
        if e.device_id in devices_map:
            devices_map[e.device_id]["entities"].append(payload)

    zones = [
        {
            "id": z.id,
            "area_id": z.area_id,
            "name": z.name,
            "description": z.description,
            "devices": []
        }
        for z in db.query(Zone).all()
    ]

    return jsonify({
        "zones": zones,
        "devices": list(devices_map.values()),
        "entities": entities_out
    })

# ---------------------------------------------------------
# Fallback: no HA available
# ---------------------------------------------------------
def build_db_fallback(db):
    devices = []
    entities_out = []

    devices_map = {}
    for d in db.query(Device).all():
        devices_map[d.id] = {
            "id": d.id,
            "name": d.name,
            "ha_device_id": d.ha_device_id,
            "type": d.type,
            "area_id": None,
            "entities": []
        }

    for e in db.query(Entity).all():
        payload = {
            "id": e.id,
            "entity_id": e.entity_id,
            "friendly_name": e.friendly_name,
            "unit": e.unit,
            "selected": bool(e.selected),
            "device_id": e.device_id
        }
        entities_out.append(payload)
        if e.device_id in devices_map:
            devices_map[e.device_id]["entities"].append(payload)

    zones = [
        {
            "id": z.id,
            "area_id": z.area_id,
            "name": z.name,
            "description": z.description,
            "devices": []
        }
        for z in db.query(Zone).all()
    ]

    return jsonify({
        "zones": zones,
        "devices": list(devices_map.values()),
        "entities": entities_out
    })


# ============================================================
#   SELECT ENTITIES (Step 2)
# ============================================================
@bp.route("/setup/entities", methods=["PUT"])
def update_selected_entities():
    """
    Body:
    { "selected": [entity_ids] }
    """
    db = session()

    selected = request.json.get("selected", [])
    all_entities = db.query(Entity).all()

    for e in all_entities:
        e.selected = e.id in selected

    db.commit()
    return jsonify({"ok": True})


# ============================================================
#   TEMPERATURE RULES — STEP 3
# ============================================================
@bp.route("/setup/temperature-rules", methods=["GET"])
def get_temperature_rules():
    db = session()
    rules = db.query(TemperatureRule).all()

    out = []
    for r in rules:
        out.append({
            "id": r.id,
            "zone_id": r.zone_id,
            "temp_min": r.temp_min,
            "temp_max": r.temp_max,
            "days": json.loads(r.days),
            "start_time": r.start_time,
            "end_time": r.end_time
        })

    return jsonify(out)


@bp.route("/setup/temperature-rules", methods=["POST"])
def create_temperature_rule():
    db = session()
    payload = request.json

    rule = TemperatureRule(
        zone_id=payload["zone_id"],
        temp_min=payload["min_temp"],
        temp_max=payload["max_temp"],
        days=json.dumps(payload["days"]),
        start_time=payload["start_time"],
        end_time=payload["end_time"]
    )
    db.add(rule)
    db.commit()

    return jsonify({"created": True, "id": rule.id})


@bp.route("/setup/temperature-rules/bulk", methods=["POST"])
def bulk_temperature_rules():
    """
    Replace ALL rules with the provided array.
    Used by SetupWizard step 3.
    """
    db = session()
    payload = request.json

    rules = payload.get("rules", [])

    # Clear table (SQLite OK)
    db.query(TemperatureRule).delete()

    # Insert new rules
    for r in rules:
        rule = TemperatureRule(
            zone_id=r["zone_id"],
            temp_min=r["temp_min"],
            temp_max=r["temp_max"],
            days = json.dumps([r["day_of_week"]]),
            start_time=r["start_time"],
            end_time=r["end_time"],
        )
        db.add(rule)

    db.commit()
    return jsonify({"saved": True, "count": len(rules)})


@bp.route("/setup/temperature-rules/<int:rule_id>", methods=["PUT"])
def update_temperature_rule(rule_id):
    db = session()
    rule = db.query(TemperatureRule).filter(TemperatureRule.id == rule_id).first()

    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    payload = request.json
    for field in ["zone_id", "min_temp", "max_temp", "days", "start_time", "end_time"]:
        if field in payload:
            setattr(rule, field, payload[field])
    
    if "days" in payload:
        rule.days = json.dumps(payload["days"])

    db.commit()
    return jsonify({"updated": True})


@bp.route("/setup/temperature-rules/<int:rule_id>", methods=["DELETE"])
def delete_temperature_rule(rule_id):
    db = session()
    rule = db.query(TemperatureRule).filter(TemperatureRule.id == rule_id).first()

    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    db.delete(rule)
    db.commit()
    return jsonify({"deleted": True})


@bp.route("/setup/schedules/bulk", methods=["POST"])
def bulk_setup_schedules():
    """
    Reemplaza todos los SetupSchedule del Setup activo
    con los schedules enviados en el body.
    Body esperado:
    {
      "schedules": [
        {
          "zone_id": 1,
          "days": "monday",
          "start_time": "08:00",
          "end_time": "12:00",
          "temp_min": 19,
          "temp_max": 22
        },
        ...
      ]
    }
    """
    db = session()
    payload = request.json or {}
    schedules = payload.get("schedules", [])

     # --- DEBUG: print input payload ---
    try:
        payload = request.get_json(force=True)
        print("\n📥 PAYLOAD /setup/schedules/bulk:")
        print(json.dumps(payload, indent=2))
    except Exception as e:
        print("❌ JSON parse error:", e)
        return jsonify({"error": "Invalid JSON"}), 400

    schedules = payload.get("schedules")
    if schedules is None:
        print("❌ schedules missing in payload")
        return jsonify({"error": "Missing field: schedules"}), 400

    if not isinstance(schedules, list):
        print("❌ schedules is not a list!")
        return jsonify({"error": "Field schedules must be list"}), 400

    if len(schedules) == 0:
        print("❌ schedules is empty")
        return jsonify({"error": "No schedules provided"}), 400
    if not schedules:
        return jsonify({"saved": False, "error": "No schedules provided"}), 400

    # Asegurar que exista company
    company = db.query(Company).first()
    if not company:
        return jsonify({"error": "No company defined"}), 400

    # Obtener o crear Setup asociado a Company
    setup = (
        db.query(Setup)
        .filter(Setup.company_id == company.id)
        .first()
    )
    if not setup:
        setup = Setup(company_id=company.id, config_name="default")
        db.add(setup)
        db.flush()

    # Borrar schedules anteriores
    db.query(SetupSchedule).filter(SetupSchedule.setup_id == setup.id).delete()

    # Insertar nuevos schedules
    inserted = 0
    for s in schedules:
        try:
            start_t = datetime.strptime(s["start_time"], "%H:%M").time()
            end_t = datetime.strptime(s["end_time"], "%H:%M").time()
        except Exception:
            return jsonify({"error": f"Invalid time format in: {s}"}), 400

        schedule = SetupSchedule(
            setup_id=setup.id,
            zone_id=int(s["zone_id"]),
            days=s["days"],  # string: "monday"
            start_time=start_t,
            end_time=end_t,
            temp_min=float(s["temp_min"]),
            temp_max=float(s["temp_max"]),
            active=True,
        )
        db.add(schedule)
        inserted += 1

    db.commit()
    return jsonify({"saved": True, "count": inserted})


@bp.route("/setup/schedules", methods=["GET"])
def get_setup_schedules():
    """
    Devuelve todos los schedules del Setup de la company.
    """
    db = session()

    company = db.query(Company).first()
    if not company:
        return jsonify([])

    setup = (
        db.query(Setup)
        .filter(Setup.company_id == company.id)
        .first()
    )
    if not setup:
        return jsonify([])

    rows = db.query(SetupSchedule).filter(SetupSchedule.setup_id == setup.id).all()

    out = []
    for s in rows:
        out.append({
            "id": s.id,
            "zone_id": s.zone_id,
            "days": s.days,
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "temp_min": s.temp_min,
            "temp_max": s.temp_max,
            "active": s.active
        })

    return jsonify(out)


# ============================================================
#   DECISIONS — AI AGENT MANAGEMENT
# ============================================================
@bp.route("/decisions/list", methods=["POST"])
def list_decisions():
    """
    Returns paginated AI agent decisions ordered by creation date
    POST method for enhanced security
    Body: { "date": "2025-11-21", "page": 1, "per_page": 10, "sort": "desc" }
    """
    db = session()
    payload = request.json or {}
    date_filter = payload.get("date")
    page = int(payload.get("page", 1))
    per_page = int(payload.get("per_page", 10))
    sort = payload.get("sort", "desc").lower()
    
    if sort not in ("asc", "desc"):
        return jsonify({"error": "Invalid sort parameter"}), 400
    
    query = db.query(Decision)
    
    if date_filter:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d")
            start_of_day = filter_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = filter_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(
                Decision.created_at >= start_of_day.isoformat(),
                Decision.created_at <= end_of_day.isoformat()
            )
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    query = query.order_by(Decision.created_at.asc() if sort == "asc" else Decision.created_at.desc())
    total = query.count()
    decisions = query.offset((page - 1) * per_page).limit(per_page).all()
    
    out = [
        {
            "id": d.id,
            "goal": d.goal,
            "reasoning": d.reasoning,
            "decision_package_json": d.decision_package_json,
            "action_summary": d.action_summary,
            "status": d.status,
            "executed_action": d.executed_action,
            "target_entity": d.target_entity,
            "action_result": d.action_result,
            "confidence": d.confidence,
            "notes": d.notes,
            "created_at": d.created_at
        } for d in decisions
    ]
    
    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "decisions": out
    })


@bp.route("/decisions/update", methods=["POST"])
def update_decision():
    """
    Update decision confidence and notes
    POST method for enhanced security
    Body: { "id": 1, "confidence": 0.8, "notes": "some notes" }
    """
    db = session()
    payload = request.json
    
    if not payload or "id" not in payload:
        return jsonify({"error": "Missing required field: id"}), 400
    
    decision_id = payload["id"]
    decision = db.query(Decision).filter(Decision.id == decision_id).first()
    
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
    
    if "confidence" in payload:
        decision.confidence = float(payload["confidence"])
    
    if "notes" in payload:
        decision.notes = payload["notes"]
    
    db.commit()
    
    return jsonify({
        "updated": True,
        "id": decision.id,
        "confidence": decision.confidence,
        "notes": decision.notes
    })


# ============================================================
#   RULES — AI EVALUATOR RULE MANAGEMENT (FIXED & IMPROVED)
# ============================================================
@bp.route("/rules/list", methods=["POST"])
def list_rules():
    """
    Returns rules with optional filtering and ordering.
    Body:
    {
        "priority": "...",
        "active": true/false,
        "created_by": "...",
        "order_by": "created_at|priority|expires_at",
        "order_dir": "asc|desc"
    }
    """
    db = session()
    payload = request.json or {}

    query = db.query(Rule)

    # ---- FILTERS ----
    if "priority" in payload and payload["priority"]:
        if payload["priority"] not in ("immediate", "mid_term", "long_term"):
            return jsonify({"error": "Invalid priority"}), 400
        query = query.filter(Rule.priority == payload["priority"])

    if "active" in payload:
        query = query.filter(Rule.active == payload["active"])

    if "created_by" in payload and payload["created_by"]:
        if payload["created_by"] not in ("user", "decisor", "evaluator"):
            return jsonify({"error": "Invalid created_by"}), 400
        query = query.filter(Rule.created_by == payload["created_by"])

    # ---- ORDERING ----
    order_by = payload.get("order_by", "created_at")
    order_dir = payload.get("order_dir", "desc")

    order_map = {
        "priority": Rule.priority,
        "created_at": Rule.created_at,
        "expires_at": Rule.expires_at,
        "id": Rule.id
    }

    if order_by in order_map:
        col = order_map[order_by]
        query = query.order_by(col.asc() if order_dir == "asc" else col.desc())

    rules = query.all()

    out = [{
        "id": r.id,
        "origin_decision_id": r.origin_decision_id,
        "rule_text": r.rule_text,
        "priority": r.priority,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "created_by": r.created_by,
        "active": r.active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "last_modified": r.last_modified.isoformat() if r.last_modified else None
    } for r in rules]

    return jsonify({
        "rules": out,
        "total": len(out)
    })


# ============================================================
#   CREATE RULE
# ============================================================

@bp.route("/rules/create", methods=["POST"])
def create_rule():
    db = session()
    payload = request.json

    if not payload:
        return jsonify({"error": "Missing body"}), 400

    if "rule_text" not in payload or "priority" not in payload:
        return jsonify({"error": "Missing rule_text or priority"}), 400

    if payload["priority"] not in ("immediate", "mid_term", "long_term"):
        return jsonify({"error": "Invalid priority"}), 400

    created_by = payload.get("created_by", "user")
    if created_by not in ("user", "decisor", "evaluator"):
        return jsonify({"error": "Invalid created_by"}), 400
    
    expires_at_raw = payload.get("expires_at")
    expires_at = None

    if expires_at_raw:
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
        except ValueError:
            return jsonify({"error": "Invalid ISO datetime format for expires_at"}), 400

    rule = Rule(
        origin_decision_id=payload.get("origin_decision_id"),
        rule_text=payload["rule_text"],
        priority=payload["priority"],
        expires_at=expires_at,
        created_by=created_by,
        active=True,
        last_modified=datetime.utcnow(),
    )

    db.add(rule)
    db.commit()

    return jsonify({"created": True, "id": rule.id})


# ============================================================
#   UPDATE RULE
# ============================================================

@bp.route("/rules/update", methods=["POST"])
def update_rule():
    db = session()
    payload = request.json

    if not payload or "id" not in payload:
        return jsonify({"error": "Missing id"}), 400

    rule = db.query(Rule).filter_by(id=payload["id"]).first()
    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    if "rule_text" in payload:
        rule.rule_text = payload["rule_text"]

    if "priority" in payload:
        if payload["priority"] not in ("immediate", "mid_term", "long_term"):
            return jsonify({"error": "Invalid priority"}), 400
        rule.priority = payload["priority"]

    if "active" in payload:
        rule.active = payload["active"]

    if "expires_at" in payload:
        expires_raw = payload["expires_at"]
        if expires_raw:
            try:
                rule.expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                return jsonify({"error": "Invalid expires_at datetime"}), 400
        else:
            rule.expires_at = None

    rule.last_modified = datetime.utcnow()
    db.commit()

    return jsonify({"updated": True, "id": rule.id})


# ============================================================
#   DELETE RULE
# ============================================================

@bp.route("/rules/delete", methods=["POST"])
def delete_rule():
    db = session()
    payload = request.json

    if not payload or "id" not in payload:
        return jsonify({"error": "Missing id"}), 400

    rule = db.query(Rule).filter_by(id=payload["id"]).first()
    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    if payload.get("hard_delete", False):
        db.delete(rule)
    else:
        rule.active = False
        rule.last_modified = datetime.utcnow()

    db.commit()

    return jsonify({"deleted": True, "id": rule.id})


# ============================================================
#   TOGGLE ACTIVE
# ============================================================

@bp.route("/rules/toggle", methods=["POST"])
def toggle_rule():
    db = session()
    payload = request.json

    if not payload or "id" not in payload:
        return jsonify({"error": "Missing id"}), 400

    rule = db.query(Rule).filter_by(id=payload["id"]).first()
    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    rule.active = not rule.active
    rule.last_modified = datetime.utcnow()
    db.commit()

    return jsonify({"toggled": True, "id": rule.id, "active": rule.active})
