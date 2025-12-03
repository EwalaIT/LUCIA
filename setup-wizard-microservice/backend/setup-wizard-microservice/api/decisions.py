from flask import jsonify, request
import requests
from . import bp, session

from models import Decision
from config import LANGCHAIN_BACKEND_URL

import logging

logger = logging.getLogger(__name__)


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
            "rule_proposals_json": d.rule_proposals_json, 
            "rule_cot": d.rule_cot,
            "role_status": d.rule_status,
            "created_at": d.created_at
        } for d in decisions
    ]
    
    db.close()
    
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
    
    # 1. Validación de Payload
    if not payload or "id" not in payload:
        return jsonify({"error": "Missing required field: id"}), 400
    
    decision_id = payload["id"]
    confidence = payload.get("confidence")
    notes = payload.get("notes")
    
    decision = db.query(Decision).filter(Decision.id == decision_id).first()
    
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
    
    # 2. Persistir el feedback del usuario en DB local
    if confidence is not None:
        decision.confidence = float(confidence)
    
    if notes is not None:
        decision.notes = notes
    
    # Opcional: Establecer un estado intermedio para el polling del frontend
    # decision.status = "RULES_PENDING" 
    
    db.commit()
    
    extracted_id = decision.id
    extracted_confidence = decision.confidence
    extracted_notes = decision.notes
    
    db.close()
    
    # 3. Llamar al LangChain Backend para iniciar la generación de reglas
    try:
        LANGCHAIN_TRIGGER_URL = f"{LANGCHAIN_BACKEND_URL}/api/rules/generate"
        
        # El payload debe coincidir con los parámetros que espera el endpoint de LangChain
        trigger_payload = {
            "decision_id": extracted_id,
            "user_score": extracted_confidence, 
            "user_note": extracted_notes
        }
        
        logger.info("Triggering rule generation for Decision %s", decision.id)
        
        response = requests.post(
            LANGCHAIN_TRIGGER_URL,
            json=trigger_payload,
            timeout=5 # Tiempo de espera para la aceptación de la tarea
        )

        if response.status_code == 202:
            # Tarea aceptada por el LangChain Backend
            message = "Rule generation triggered successfully."
            is_triggered = True
        else:
            # Error al aceptar la tarea (e.g., LangChain Backend offline, error 500)
            message = f"LangChain Backend failed to accept task: {response.status_code} - {response.text}"
            logger.error(message)
            is_triggered = False
            
    except requests.exceptions.RequestException as e:
        # Error de conexión o timeout
        message = f"Connection error calling LangChain Backend: {e}"
        logger.error(message)
        is_triggered = False
        
    # 4. Devolver la respuesta al frontend (incluyendo el estado del trigger)
    return jsonify({
        "updated": True,
        "id": extracted_id,
        "confidence": extracted_confidence,
        "notes": extracted_notes,
        "rule_generation_triggered": is_triggered,
        "message": message
    })  


# ============================================================
#   HITL FLOW — RULES DRAFTING AND APPROVAL
# ============================================================

@bp.route("/decisions/proposals", methods=["POST"])
def get_rule_proposals():
    """
    Endpoint para el frontend para hacer 'polling' y obtener las propuestas
    de reglas (el borrador) y el CoT generado por el LangChain Backend.
    Body: { "decision_id": 123 }
    """
    db = session()
    payload = request.json
    
    if not payload or "decision_id" not in payload:
        return jsonify({"error": "Missing required field: decision_id"}), 400
    
    decision_id = payload["decision_id"]
    
    # Asegúrate de que tu modelo 'Decision' tiene los campos
    # rule_proposals_json, rule_cot, y status.
    decision = db.query(Decision).filter(Decision.id == decision_id).first()
    
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
        
    # El Frontend espera recibir las propuestas si el estado es RULES_READY
    is_ready = decision.status == "RULES_READY"
    
    db.close()

    return jsonify({
        "decision_id": decision.id,
        "status": decision.status,
        "is_ready": is_ready,
        # Devolvemos el borrador (JSON string) y el CoT
        "rule_proposals_json": decision.rule_proposals_json,
        "rule_cot": decision.rule_cot,
        "rule_status": decision.rule_status
    })


@bp.route("/decisions/apply_proposals", methods=["POST"])
def apply_rule_proposals():
    """
    Proxy que reenvía las propuestas de reglas aprobadas por el usuario
    al LangChain Backend para su ejecución final (persistencia en DB de reglas).
    Body: { "decision_id": 123, "accepted_proposals": [...] }
    """
    payload = request.json
    
    if not payload or "decision_id" not in payload or "accepted_proposals" not in payload:
        return jsonify({"error": "Missing required fields: decision_id and accepted_proposals"}), 400
        
    # 1. Llamar al LangChain Backend para ejecutar la aplicación
    try:
        LANGCHAIN_APPLY_URL = f"{LANGCHAIN_BACKEND_URL}/api/rules/apply"
        
        logger.info("Applying rule proposals for Decision %s", payload["decision_id"])
        
        response = requests.post(
            LANGCHAIN_APPLY_URL,
            json=payload, # Enviamos el mismo payload (decision_id + accepted_proposals)
            timeout=10 # Esperar más tiempo, ya que esto ejecuta la DB write
        )

        if response.status_code == 200:
            # LangChain Backend confirmó la ejecución y actualizó el estado a RULES_APPLIED
            return jsonify({
                "applied": True,
                "message": "Rules applied successfully.",
                "details": response.json()
            })
        else:
            # Error en la ejecución final en LangChain
            message = f"LangChain Backend execution failed: {response.status_code} - {response.text}"
            logger.error(message)
            return jsonify({
                "applied": False, 
                "error": message, 
                "details": response.json()
            }), 502 # Bad Gateway / Error del servicio externo
            
    except requests.exceptions.RequestException as e:
        message = f"Connection error calling LangChain Backend for apply: {e}"
        logger.error(message)
        return jsonify({"applied": False, "error": message}), 503
