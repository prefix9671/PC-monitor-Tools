from __future__ import annotations

import logging
from functools import wraps

from tornado.iostream import StreamClosedError
from tornado.websocket import WebSocketClosedError, WebSocketProtocol13


LOGGER = logging.getLogger(__name__)
_PATCH_APPLIED = False


def _consume_known_websocket_disconnect(future) -> None:
    try:
        future.result()
    except (WebSocketClosedError, StreamClosedError):
        # A browser tab closing mid-rerun is normal for Streamlit/Tornado.
        # Consume the disconnect so asyncio does not emit "Task exception was never retrieved".
        return
    except Exception:
        LOGGER.exception("Unexpected websocket write failure while applying runtime patch.")


def apply_streamlit_runtime_patches() -> None:
    global _PATCH_APPLIED

    if _PATCH_APPLIED:
        return

    original_write_message = WebSocketProtocol13.write_message

    @wraps(original_write_message)
    def patched_write_message(self, message, binary: bool = False):
        future = original_write_message(self, message, binary=binary)
        if future is not None:
            future.add_done_callback(_consume_known_websocket_disconnect)
        return future

    WebSocketProtocol13.write_message = patched_write_message
    _PATCH_APPLIED = True
