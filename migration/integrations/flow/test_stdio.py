"""Real MCP subprocess smoke test: the five tools, and flow_status on a profile nobody signed in to (no browser, no
network). Needs the mcp package (the PC's venv has it)."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from mcp import Client, StdioServerParameters
except ImportError:  # pragma: no cover
    Client = None


@unittest.skipIf(Client is None, "mcp is not installed")
class Stdio(unittest.TestCase):
    def test_tools_and_status_without_login(self):
        async def run(data_dir):
            params = StdioServerParameters(command=sys.executable,
                                           args=[str(Path(__file__).with_name("mcp_server.py"))],
                                           env={**os.environ, "FLOW_DATA": data_dir, "FLOW_PROFILE": data_dir})
            async with Client(params) as session:
                tools = {t.name: t for t in (await session.list_tools()).tools}
                self.assertEqual(set(tools), {"flow_status", "flow_quote", "flow_generate", "flow_job",
                                              "flow_download"})
                for name, tool in tools.items():
                    self.assertEqual(tool.annotations.read_only_hint, name not in ("flow_generate", "flow_download"))
                status = await session.call_tool("flow_status", {})
                data = json.loads(status.content[0].text)
                self.assertEqual(data["state"], "NOT_LOGGED_IN")
                self.assertEqual(data["daily_cap"], 4)
                bad = await session.call_tool("flow_generate", {"quote_id": "", "prompt": "x"})
                self.assertEqual(json.loads(bad.content[0].text)["state"], "REFUSED")
        with tempfile.TemporaryDirectory() as d:
            asyncio.run(run(d))


if __name__ == "__main__":
    unittest.main()
