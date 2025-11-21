# services/db_memory.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Lazy import of db functions so this module imports even if db_tools changes slightly.
try:
    # Prefer the more explicit names if present
    from db.contexts import (insert_memory_entry,get_memory_entries,clear_memory_for_session)
except ImportError as e:
    # If imports failed entirely, raise an informative ImportError at runtime (lazy)
    
    insert_memory_entry = None  # type: ignore
    get_memory_entries = None  # type: ignore
    clear_memory_for_session = None  # type: ignore
    logger.warning(
    "DB helper functions could not be imported from db.contexts. "
    "Memory operations will fail. ImportError: %s", e
    )


class SQLiteMemoryAdapter():
    """
    SQLite-backed memory adapter.

    - session_id: an identifier for conversation/session (used to scope memory rows)
    - history_key: the memory variable key returned by load_memory_variables (defaults to "history")
    """

    def __init__(self, session_id: str, history_key: str = "history"):
        super().__init__()
        self.session_id = session_id
        self.history_key = history_key

        # Validate availability of DB helper functions at construction time and log helpful messages
        if insert_memory_entry is None or get_memory_entries is None:
            logger.error(
                "services.db_tools memory helper functions not found. "
                "Expected insert_memory_entry/get_memory_entries or insert_context/get_contexts_by_type."
            )
            # We do NOT raise here to allow import in tests, but operations will fail later with clear log.
        else:
            logger.debug("SQLiteMemoryAdapter initialized for session_id=%s", self.session_id)

    # Required by BaseMemory API in LangChain
    @property
    def memory_variables(self) -> List[str]:
        """
        The keys this memory implementation will add to `inputs` when loaded.
        For us, it's a single key (history) that returns a list/dict with past entries.
        """
        return [self.history_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load past memory for this session and return it as a mapping to be merged into chain inputs.
        This method is synchronous (calls synchronous db_tools functions). When calling from async
        code, use: await asyncio.to_thread(adapter.load_memory_variables, inputs)
        """
        if get_memory_entries is None:
            logger.error("Cannot load memory: get_memory_entries function not available in services.db_tools")
            return {self.history_key: []}

        try:
            # get_memory_entries(session_id: str, limit: Optional[int] = None) -> List[dict]
            # We call with session_id only; db_tools implementation decides default limit.
            history = get_memory_entries(self.session_id)  # type: ignore
            # Normalize to a structure LangChain expects (list of dicts or strings)
            return {self.history_key: history or []}
        except Exception as e:
            logger.exception("Error loading memory for session %s: %s", self.session_id, e)
            return {self.history_key: []}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save a new memory entry representing the last turn (inputs -> outputs).
        This is synchronous. When calling from async code, use asyncio.to_thread.
        """
        if insert_memory_entry is None:
            logger.error("Cannot save memory: insert_memory_entry function not available in services.db_tools")
            return

        try:
            # insert_memory_entry(session_id: str, input_text: str, output_text: str, metadata: Optional[dict] = None) -> int | None
            # We'll store a simple record: inputs and outputs stringified; db_tools may accept metadata.
            input_repr = str(inputs)
            output_repr = str(outputs)
            # Some db helpers accept only (session_id, system_state) or similar. Try common signatures.
            try:
                # Preferred: insert_memory_entry(session_id, input_text, output_text)
                insert_memory_entry(self.session_id, input_repr, output_repr)  # type: ignore
            except TypeError:
                # Fallback: insert_context(context_type, system_state) style - attempt to use session_id as type
                try:
                    insert_memory_entry(self.session_id, f"IN:{input_repr} | OUT:{output_repr}")  # type: ignore
                except Exception as e2:
                    logger.exception("Failed fallback insert_memory_entry: %s", e2)
            except Exception as e:
                logger.exception("Error inserting memory entry for session %s: %s", self.session_id, e)
        except Exception as e:
            logger.exception("Unexpected error saving memory context for session %s: %s", self.session_id, e)

    def clear(self) -> None:
        """
        Optional: clear memory for this session. If services.db_tools exposes a clear function,
        use it. Otherwise this is a no-op.
        """
        if clear_memory_for_session is None:
            logger.debug("clear() called but no clear_memory_for_session implementation available in services.db_tools")
            return

        try:
            clear_memory_for_session(self.session_id)  # type: ignore
            logger.info("Cleared memory for session %s", self.session_id)
        except Exception as e:
            logger.exception("Failed to clear memory for session %s: %s", self.session_id, e)