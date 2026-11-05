#!/usr/bin/env python3
"""Stdio MCP "heroverse-flow" (UNOFFICIAL Google Flow) for a Claude session on the owner's PC.

Each tool runs runner.py in its own process, so its lock, owner-idle check, cool-down, quote, daily cap, free-credit
guard and ledger apply exactly as on the command line. Register it once on the PC (user scope):
  claude mcp add --scope user heroverse-flow -- C:\\HeroVerse\\flow-runner\\.venv\\Scripts\\python.exe C:\\HeroVerse\\flow-runner\\mcp_server.py
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def run(args, timeout=900):
    p = subprocess.run([sys.executable, str(HERE / "runner.py"), *args], capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    lines = [l for l in (p.stdout or "").splitlines() if l.strip()]
    for line in reversed(lines):
        if line.startswith("RESULT "):
            out = json.loads(line[len("RESULT "):])
            out["exit"] = p.returncode
            return out
    return {"state": "ERROR", "exit": p.returncode, "log": lines[-5:]}


def setting(model, seconds, resolution, aspect, mode, ingredients, character=None):
    args = ["--model", model, "--seconds", str(seconds), "--resolution", resolution, "--aspect", aspect, "--mode", mode]
    if ingredients:
        args += ["--ingredient", *ingredients]
    if character:
        args += ["--character", character]
    return args


def build():
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations
    mcp = MCPServer("heroverse-flow", instructions=(
        "Unofficial Google Flow route in the owner's own account (he accepted the account risk on 2026-11-05). Free "
        "daily credits only: never buy, upgrade or start a trial. flow_generate needs a fresh flow_quote. Never retry "
        "an uncertain submission: read it with flow_job. A CAPTCHA, unusual-activity, come-back-tomorrow, login or 2FA "
        "page stops everything for 24 h; report it."))
    read = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
    write = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True)

    @mcp.tool(annotations=read)
    def flow_status() -> dict:
        """Logged in, plan hint, credits left today, cool-down and today's usage."""
        return run(["status"], timeout=300)

    @mcp.tool(annotations=read)
    def flow_quote(model: str = "veo-3.1-lite", seconds: int = 8, resolution: str = "720p", aspect: str = "16:9",
                   mode: str = "text", ingredients: list[str] | None = None) -> dict:
        """The exact credit cost of one output for this setting, read from Flow's UI; nothing is submitted. Returns a
        quote_id valid 15 minutes for the same setting."""
        return run(["quote", *setting(model, seconds, resolution, aspect, mode, ingredients)], timeout=600)

    @mcp.tool(annotations=write)
    def flow_generate(quote_id: str, prompt: str, model: str = "veo-3.1-lite", seconds: int = 8,
                      resolution: str = "720p", aspect: str = "16:9", mode: str = "text",
                      ingredients: list[str] | None = None, character: str | None = None) -> dict:
        """ONE silent-acting generation with a fresh matching quote, within today's free credits and the daily cap.
        The prompt says 'centred in the frame', asks for no speech, never shows God's face. Returns job_id."""
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(prompt)
        try:
            return run(["generate", "--quote", quote_id, "--prompt", fh.name,
                        *setting(model, seconds, resolution, aspect, mode, ingredients, character)], timeout=900)
        finally:
            Path(fh.name).unlink(missing_ok=True)

    @mcp.tool(annotations=read)
    def flow_job(job_id: str) -> dict:
        """Read a job's state from the project (RUNNING / COMPLETED / FAILED / UNCERTAIN); never resubmits."""
        return run(["job", job_id], timeout=600)

    @mcp.tool(annotations=write)
    def flow_download(job_id: str) -> dict:
        """Save a completed job to C:\\HeroVerse\\flow\\<job>.mp4 with its sha256, ffprobe summary and 4 frames."""
        return run(["download", job_id], timeout=900)

    return mcp


if __name__ == "__main__":
    build().run()
