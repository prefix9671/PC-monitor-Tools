from __future__ import annotations

import asyncio
import logging
from functools import wraps

from tornado.iostream import StreamClosedError
from tornado.web import RequestHandler
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


def _dispose_gzip_transform_state(handler: object) -> None:
    for transform in getattr(handler, "_transforms", []) or []:
        gzip_file = getattr(transform, "_gzip_file", None)
        if gzip_file is not None:
            try:
                gzip_file.fileobj = None
            except Exception:
                pass
            try:
                setattr(transform, "_gzip_file", None)
            except Exception:
                pass

        gzip_value = getattr(transform, "_gzip_value", None)
        if gzip_value is not None:
            try:
                gzip_value.close()
            except Exception:
                pass
            try:
                setattr(transform, "_gzip_value", None)
            except Exception:
                pass


def _wrap_flush_future(handler: object, future):
    async def guarded_flush():
        try:
            return await future
        except (asyncio.CancelledError, StreamClosedError):
            # Static asset requests can be cancelled while the browser tab is closing.
            # Treat that as a normal disconnect and tear down any in-flight gzip state
            # so Tornado/asyncio do not emit noisy shutdown tracebacks.
            _dispose_gzip_transform_state(handler)
            return None
        except Exception:
            LOGGER.exception("Unexpected HTTP flush failure while applying runtime patch.")
            raise

    return asyncio.ensure_future(guarded_flush())


def apply_streamlit_runtime_patches() -> None:
    global _PATCH_APPLIED

    if _PATCH_APPLIED:
        return

    original_write_message = WebSocketProtocol13.write_message
    original_flush = RequestHandler.flush

    @wraps(original_write_message)
    def patched_write_message(self, message, binary: bool = False):
        future = original_write_message(self, message, binary=binary)
        if future is not None:
            future.add_done_callback(_consume_known_websocket_disconnect)
        return future

    @wraps(original_flush)
    def patched_flush(self, include_footers: bool = False):
        future = original_flush(self, include_footers=include_footers)
        if future is None:
            return None
        return _wrap_flush_future(self, future)

    WebSocketProtocol13.write_message = patched_write_message
    RequestHandler.flush = patched_flush
    _PATCH_APPLIED = True
