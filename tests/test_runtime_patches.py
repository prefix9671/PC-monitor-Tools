import asyncio
import os
import sys
import unittest
from unittest.mock import patch

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

    def test_apply_streamlit_runtime_patches_is_idempotent(self):
        original_write_message = WebSocketProtocol13.write_message

        with patch.object(runtime_patches, "_PATCH_APPLIED", False):
            runtime_patches.apply_streamlit_runtime_patches()
            first_patch = WebSocketProtocol13.write_message
            runtime_patches.apply_streamlit_runtime_patches()
            second_patch = WebSocketProtocol13.write_message

        self.assertIs(first_patch, second_patch)
        self.assertIsNot(original_write_message, first_patch)
        WebSocketProtocol13.write_message = original_write_message


if __name__ == "__main__":
    unittest.main()
