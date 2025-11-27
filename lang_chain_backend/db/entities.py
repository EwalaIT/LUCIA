# db/entities.py (o el módulo que uses para las consultas)

import sqlite3
import os
import logging
from typing import List, Optional

from config import settings

logger = logging.getLogger(__name__)

# Asegúrate de que settings.db_path es accesible y apunta a tu BBDD
DB_PATH = str(settings.db_path) 

def get_selected_entity_ids() -> List[str]:
    """
    Obtiene todas las entity_id donde el campo 'selected' es True (1).
    Esto incluirá tanto dispositivos como entidades de zona (si están marcadas como seleccionadas).
    """
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file not found at {DB_PATH}")
        return []
    
    entity_ids = []
    
    # 💡 La lógica clave es filtrar por selected = 1
    query = "SELECT entity_id FROM entity WHERE selected = 1;"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Obtenemos una lista de tuplas (entity_id, ) y la convertimos a List[str]
        entity_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Database error fetching selected entities: {e}")
        return []
        
    logger.debug(f"Fetched {len(entity_ids)} selected entity IDs.")
    return entity_ids