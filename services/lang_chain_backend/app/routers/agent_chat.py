import logging
from fastapi import Request, APIRouter
from app.models import ChatRequest
from services.agent_chat_commander import run_chat_commander

router = APIRouter()

logger = logging.getLogger("router.decisor")


@router.post("/chat")
async def chat_commander_route(request: Request, body: ChatRequest):
    """
    Ruta principal para recibir instrucciones del usuario y ejecutar el agente de chat.
    FastMCP expondrá esta ruta como una única herramienta.
    """
    logger.info(f"Received instruction: {body.instruction}")
    
    if "chat_commander" not in getattr(request.app.state, "agents", {}):
        return {
            "status": "ERROR", 
            "reason": "Agent not initialized. Check server startup logs."
        }
    
    try:
        # Llama a la lógica del agente, pasando la aplicación para acceder al agente inicializado.
        result = await run_chat_commander(request.app, body.instruction)
        
        # FastMCP espera el resultado de la llamada a la herramienta del agente
        return result

    except Exception as e:
        logger.exception(f"Error processing chat instruction: {e}")
        return {
            "status": "ERROR", 
            "reason": f"An unexpected error occurred during agent execution: {e}"
        }