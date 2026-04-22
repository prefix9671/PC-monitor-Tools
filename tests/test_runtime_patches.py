import asyncio
import os
import sys
import unittest
from io import BytesIO
from unittest.mock import patch

from tornado.iostream import StreamClosedError
from tornado.web import RequestHandler
from tornado.websocket import WebSocketClosedError, WebSocketProtocol13


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import runtime_patches


class TestRuntimePatches(unittest.TestCase):
    def test_consume_known_websocket_disconnect_swallows_disconnect_noise(self):
        loop = asyncio.new_event_loop()
        try:
            future = loop.create_future()
            future.set_exception(WebSocketClosedError())

            runtime_patches._consume_known_websocket_disconnect(future)
        finally:
            loop.close()

    def test_consume_known_websocket_disconnect_logs_unexpected_errors(self):
        loop = asyncio.new_event_loop()
        try:
            future = loop.create_future()
            future.set_exception(RuntimeError("boom"))

            with self.assertLogs(runtime_patches.LOGGER.name, level="ERROR") as captured:
                runtime_patches._consume_known_websocket_disconnect(future)

            self.assertIn("Unexpected websocket write failure", "\n".join(captured.output))
        finally:
            loop.close()

    def test_wrap_flush_future_swallows_cancelled_disconnect_and_cleans_gzip_state(self):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            future = loop.create_future()
            future.set_exception(asyncio.CancelledError())

            class DummyGzipFile:
                def __init__(self):
                    self.fileobj = BytesIO()

            class DummyTransform:
                def __init__(self):
                    self._gzip_file = DummyGzipFile()
                    self._gzip_value = BytesIO()

            class DummyHandler:
                def __init__(self):
                    self._transforms = [DummyTransform()]

            handler = DummyHandler()
            wrapped = runtime_patches._wrap_flush_future(handler, future)
            loop.run_until_complete(wrapped)

            self.assertIsNone(handler._transforms[0]._gzip_file)
            self.assertIsNone(handler._transforms[0]._gzip_value)
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    def test_wrap_flush_future_swallows_stream_closed_disconnect(self):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            future = loop.create_future()
            future.set_exception(StreamClosedError())

            class DummyHandler:
                _transforms = []

            wrapped = runtime_patches._wrap_flush_future(DummyHandler(), future)
            loop.run_until_complete(wrapped)
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    def test_apply_streamlit_runtime_patches_is_idempotent(self):
        original_write_message = WebSocketProtocol13.write_message
        original_flush = RequestHandler.flush

        with patch.object(runtime_patches, "_PATCH_APPLIED", False):
            runtime_patches.apply_streamlit_runtime_patches()
            first_patch = WebSocketProtocol13.write_message
            first_flush_patch = RequestHandler.flush
            runtime_patches.apply_streamlit_runtime_patches()
            second_patch = WebSocketProtocol13.write_message
            second_flush_patch = RequestHandler.flush

        self.assertIs(first_patch, second_patch)
        self.assertIs(first_flush_patch, second_flush_patch)
        self.assertIsNot(original_write_message, first_patch)
        self.assertIsNot(original_flush, first_flush_patch)
        WebSocketProtocol13.write_message = original_write_message
        RequestHandler.flush = original_flush


if __name__ == "__main__":
    unittest.main()
