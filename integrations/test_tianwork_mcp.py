import unittest

from tianwork_mcp import TOOLS, command_for_tool, handle_message


class TianWorkMcpTests(unittest.TestCase):
    def test_list_tools_excludes_raw_activity(self):
        names = {tool["name"] for tool in TOOLS}
        self.assertNotIn("tianwork_activity_events", names)
        self.assertIn("tianwork_work_context", names)
        self.assertIn("tianwork_dam_evidence", names)

    def test_days_are_bounded(self):
        with self.assertRaises(ValueError):
            command_for_tool("tianwork_work_context", {"days": 0})
        with self.assertRaises(ValueError):
            command_for_tool("tianwork_work_context", {"days": 91})

    def test_initialize_echoes_protocol_version(self):
        response = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            }
        )
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(response["result"]["serverInfo"]["name"], "tianwork-mcp")

    def test_tools_list(self):
        response = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(response["result"]["tools"], TOOLS)

    def test_unknown_method_returns_method_not_found(self):
        response = handle_message({"jsonrpc": "2.0", "id": 3, "method": "unknown"})
        self.assertEqual(response["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
