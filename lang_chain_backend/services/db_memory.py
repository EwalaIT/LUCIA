# services/db_memory.py
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from db.memory import (
    insert_memory_entry,
    get_memory_entries,
    clear_memory_for_session,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SQLiteMemoryAdapter:
    """
    SQLite-backed memory adapter.

    - session_id: an identifier for conversation/session (used to scope memory rows)
    - history_key: the memory variable key returned by load_memory_variables (defaults to "history")
    """

    def __init__(self, session_id: str, history_key: str = "history"):
        self.session_id = session_id
        self.history_key = history_key

        # Validate DB helper availability
        if insert_memory_entry is None or get_memory_entries is None:
            logger.error(
                "services.db_tools memory helper functions not found. "
                "Expected insert_memory_entry/get_memory_entries."
            )
        else:
            logger.debug("SQLiteMemoryAdapter initialized for session_id=%s", self.session_id)

    # Required by LangChain BaseMemory API
    @property
    def memory_variables(self) -> List[str]:
        return [self.history_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if get_memory_entries is None:
            logger.error("Cannot load memory: get_memory_entries function not available in services.db_tools")
            return {self.history_key: []}

        try:
            history = get_memory_entries(self.session_id)  # type: ignore
            return {self.history_key: history or []}
        except Exception as e:
            logger.exception(
                "Error loading memory for session %s: %s",
                self.session_id, e
            )
            return {self.history_key: []}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save a memory entry representing the last turn (inputs -> outputs),
        serializing the data as JSON strings.
        """
        if insert_memory_entry is None:
            logger.error("Cannot save memory: insert_memory_entry function not available in services.db_tools")
            return

        try:
            # Serialize clean JSON for DB storage
            input_json = json.dumps(inputs, ensure_ascii=False)
            output_json = json.dumps(outputs, ensure_ascii=False)

            insert_memory_entry(
                self.session_id,
                input_json,
                output_json
            )  # type: ignore

        except Exception as e:
            logger.exception(
                "Error inserting memory entry for session %s: %s",
                self.session_id, e
            )

    def clear(self) -> None:
        if clear_memory_for_session is None:
            logger.debug(
                "clear() called but clear_memory_for_session not available in services.db_tools"
            )
            return

        try:
            clear_memory_for_session(self.session_id)  # type: ignore
            logger.info("Cleared memory for session %s", self.session_id)
        except Exception as e:
            logger.exception(
                "Failed to clear memory for session %s: %s",
                self.session_id, e
            )
