from flask import jsonify, request
from datetime import datetime

from . import bp, session

from models import Rule
import logging

logger = logging.getLogger(__name__)


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
        if payload["created_by"] not in ("user", "decisor", "evaluator", "chat"):
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
    
    db.close()

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
    
    id = rule.id
    db.add(rule)
    db.commit()
    db.close()

    return jsonify({"created": True, "id": id})


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
    id = rule.id
    db.commit()
    db.close()

    return jsonify({"updated": True, "id": id})


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

    id = rule.id
    db.commit()
    db.close()
    
    return jsonify({"deleted": True, "id": id})


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

    active = rule.active = not rule.active
    id = rule.id
    rule.last_modified = datetime.utcnow()
    db.commit()
    db.close()

    return jsonify({"toggled": True, "id": id, "active": active})
