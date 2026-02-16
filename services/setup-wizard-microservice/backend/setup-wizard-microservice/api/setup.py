import json
from flask import jsonify, request
from datetime import datetime

from models import (Company, Zone, Device, Entity, Setup, SetupSchedule, TemperatureRule, Rule)
from . import bp, session
from ha_ws_client import get_ha_areas, get_ha_devices, get_ha_entities
from utils import generate_natural_language_rules
from ha_client import get_states
import logging

logger = logging.getLogger(__name__)


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
    
    db.close()
    
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
    id = company.id
    db.commit()
    db.close()

    return jsonify({"created": True, "company_id": id})


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

    db.close()
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
    db = session()

    company = db.query(Company).first()
    if not company:
        return jsonify({"error": "No company defined"}), 400

    # ----- Try to get HA data -----
    try:
        logger.info("[HA] Fetching areas, devices, entities, and states from Home Assistant...")

        areas = get_ha_areas()
        logger.info(f"[HA] Retrieved {len(areas)} areas: {areas[:3]}...")  # mostrar solo 3 para no saturar logs

        devices_reg = get_ha_devices()
        logger.info(f"[HA] Retrieved {len(devices_reg)} devices: {devices_reg[:3]}...")

        entities_reg = get_ha_entities()
        logger.info(f"[HA] Retrieved {len(entities_reg)} entities: {entities_reg[:3]}...")

        states = get_states()
        logger.info(f"[HA] Retrieved {len(states)} states from /api/states: {states[:3]}...")

    except Exception as e:
        logger.exception("[HA] Error fetching data from Home Assistant, falling back to DB")
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
                logger.debug(f"[HA] Device {dev.name} ({ha_dev_id}) assigned to entity {eid}")
                dev.last_sync = now
                db.add(dev)

        # ---- ENTITY ----
        ent = db_entities.get(eid)
        if not ent:
            logger.debug(f"[HA] Creating entity: {eid}, device_id: {ha_dev_id}, friendly_name: {friendly}")
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
            logger.debug(f"[HA] Updating entity: {eid}, device_id: {ha_dev_id}")
            ent.device = dev
            ent.friendly_name = friendly
            ent.unit = unit or ent.unit
            ent.last_state = last_state
            ent.last_updated = now
            db.add(ent)

    db.commit()

    # ---------------------------------------------------------
    #  BUILD + UPSERT ZONES
    # ---------------------------------------------------------
    zones_final = []
    area_to_db_id = {}
    existing_zones = {z.area_id: z for z in db.query(Zone).filter(Zone.company_id == company.id)}

    for a in areas:
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
            "devices": [],
            "entities_without_device": []
        })

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
        else:
            # ENTIDAD SIN DEVICE → colgar de la zona correspondiente
            if area_id and area_id in area_to_db_id:
                zid = area_to_db_id[area_id]
                zone = next(z for z in zones_final if z["id"] == zid)
                zone["entities_without_device"].append(payload)

    # ---------------------------------------------------------
    # Attach devices to zones
    # ---------------------------------------------------------
    for d in devices_map.values():
        area = d["area_id"]
        dev = db.query(Device).filter(Device.id == d["id"]).first()
        if area and area in area_to_db_id:
            zid = area_to_db_id[area]
            dev.zone_id = zid
            zone = next(z for z in zones_final if z["id"] == zid)
            zone["devices"].append(d)
        else:
            dev.zone_id = None

    db.commit()
    db.close()

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
    
    db.close()

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
    db.close()
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
    
    db.close()

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
    db.close()
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
    db.close()
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
    db.close()
    return jsonify({"updated": True})


@bp.route("/setup/temperature-rules/<int:rule_id>", methods=["DELETE"])
def delete_temperature_rule(rule_id):
    db = session()
    rule = db.query(TemperatureRule).filter(TemperatureRule.id == rule_id).first()

    if not rule:
        return jsonify({"error": "Rule not found"}), 404

    db.delete(rule)
    db.commit()
    db.close()
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

    # Asegurar que exista company
    company = db.query(Company).first()
    if not company:
        return jsonify({"error": "No company defined"}), 400

    # Obtener o crear Setup asociado a Company
    setup = db.query(Setup).filter(Setup.company_id == company.id).first()
    if not setup:
        setup = Setup(company_id=company.id, config_name="default")
        db.add(setup)
        db.flush()

    # Empezamos transacción atómica
    try:
        # Borrar schedules anteriores del setup
        db.query(SetupSchedule).filter(SetupSchedule.setup_id == setup.id).delete()

        inserted_objs = []

        # Insertar nuevos schedules
        for s in schedules:
            # Validaciones mínimas y parseo de tiempos
            try:
                start_t = datetime.strptime(s["start_time"], "%H:%M").time()
                end_t = datetime.strptime(s["end_time"], "%H:%M").time()
            except Exception:
                db.rollback()
                return jsonify({"error": f"Invalid time format in: {s}"}), 400

            # normalizar days como string (guardamos tal cual)
            days_field = s.get("days", "")
            # guardamos en minúsculas para consistencia
            if isinstance(days_field, str):
                days_field_db = days_field.lower()
            else:
                # si viene lista -> convertir a "a,b"
                if isinstance(days_field, (list, tuple, set)):
                    days_field_db = ",".join([d.lower() for d in days_field])
                else:
                    days_field_db = str(days_field).lower()

            schedule = SetupSchedule(
                setup_id=setup.id,
                zone_id=int(s["zone_id"]),
                days=days_field_db,
                start_time=start_t,
                end_time=end_t,
                temp_min=float(s["temp_min"]),
                temp_max=float(s["temp_max"]),
                active=True,
            )
            db.add(schedule)
            inserted_objs.append(schedule)

        # Necesitamos flush para que los objetos tengan estado persistente (y, si hay triggers/constraints, fallen ahora)
        db.flush()

        # Generar reglas en lenguaje natural basadas en los schedules recién insertados
        rules_to_insert = generate_natural_language_rules(inserted_objs, db)

        # Insertar reglas en tabla rules
        for r in rules_to_insert:
            rule = Rule(
                rule_text=r["rule_text"],
                priority="long_term",
                created_by="user",
                active=True,
                expires_at=None,
            )
            db.add(rule)

        # Commit final (schedules + rules en una sola transacción)
        db.commit()
        db.close()

        return jsonify({
            "saved": True,
            "schedules_count": len(inserted_objs),
            "rules_generated": len(rules_to_insert),
        })

    except Exception as exc:
        # Rollback y log
        try:
            db.rollback()
        except Exception:
            pass
        print("❌ ERROR in bulk_setup_schedules:", exc)
        return jsonify({"error": "Internal server error"}), 500


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

    db.close()
    return jsonify(out)