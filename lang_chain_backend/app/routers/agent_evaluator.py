from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse # Importación necesaria para devolver JSONResponse
from typing import List, Dict
import logging

from db.rules import (
    create_new_rule,
    modify_existing_rule,
    delete_rule_by_id
)

from db.decisions import update_decision_rule_status


router = APIRouter()
logger = logging.getLogger("router.decisor")


@router.post("/rules/generate")
async def trigger_rule_generation(payload: Dict, request: Request): # AÑADIR request: Request
    """
    Endpoint llamado por el Setup-Wizard para iniciar la tarea de generación de reglas.
    """
    decision_id = payload.get("decision_id")
    user_score = payload.get("user_score")
    user_note = payload.get("user_note")

    if not all([decision_id, user_score is not None, user_note is not None]):
        raise HTTPException(status_code=400, detail="Missing required parameters.")
    
    # ACCESO CORREGIDO: usar request.app.state
    eval_q = request.app.state.eval_queue 
    if eval_q is None:
        logger.error("Evaluator queue is not initialized.")
        raise HTTPException(status_code=500, detail="Rule Agent is offline. (Queue not found)")
    
    # ... (el resto del código es correcto)
    await eval_q.put({
        "decision_id": decision_id, 
        "user_score": user_score, 
        "user_note": user_note
    })

    # Devolvemos 202 ACCEPTED para indicar que la tarea fue aceptada y se está procesando.
    return JSONResponse(
        status_code=202, 
        content={"message": "Rule generation started in background.", "decision_id": decision_id}
    )
    
@router.post("/rules/apply")
async def apply_rules(payload: Dict):
    """
    Endpoint llamado por el Setup-Wizard cuando el usuario aprueba
    las propuestas de reglas generadas por el Agente Evaluador.
    """
    decision_id = payload.get("decision_id")
    accepted_proposals: List[Dict] = payload.get("accepted_proposals", [])

    if decision_id is None:
        raise HTTPException(status_code=400, detail="Missing decision_id.")

    if not isinstance(accepted_proposals, list):
        raise HTTPException(status_code=400, detail="accepted_proposals must be a list.")

    logger.info(
        f"🔧 Applying {len(accepted_proposals)} rule proposals for decision {decision_id}"
    )

    try:
        for proposal in accepted_proposals:
            action = proposal.get("action_type")

            if action == "CREATE":
                create_new_rule(
                    rule_text=proposal["rule_text"],
                    priority=proposal["priority"],
                    expires_at=proposal.get("expires_at"),
                    origin_decision_id=decision_id,
                    created_by="evaluator"
                )

            elif action == "MODIFY":
                modify_existing_rule(
                    rule_id=proposal["rule_id"],
                    new_rule_text=proposal["rule_text"],
                    new_priority=proposal["priority"],
                    new_expires_at=proposal.get("expires_at")
                )

            elif action == "DELETE":
                delete_rule_by_id(proposal["rule_id"])

            else:
                raise HTTPException(
                    # status_code=400,
                    detail=f"Invalid action_type: {action}"
                )

        # Marcar la decisión como “reglas aplicadas”
        update_decision_rule_status(decision_id, rule_status="RULES_APPLIED")

        logger.info(f"✅ Rules applied successfully for decision {decision_id}")

        return {"status": "success", "decision_id": decision_id}

    except Exception as e:
        logger.exception(f"❌ Failed applying rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))
