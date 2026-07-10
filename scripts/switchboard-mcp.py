#!/usr/bin/env python3
"""Switchboard (taikun-plan) client for Helm Cloud Agents.

Uses SWITCHBOARD_TOKEN or PM_MCP_TOKEN from the environment. Cloud Agents do not
always expose native MCP tools in the Cursor UI; this CLI is the supported
fallback and matches the taikun-plan MCP tool surface via HTTP/SSE.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

MCP_URL = os.environ.get("SWITCHBOARD_MCP_URL", "https://plan.taikunai.com/mcp")
REST_BASE = os.environ.get("SWITCHBOARD_REST_BASE", "https://plan.taikunai.com")
DEFAULT_PROJECT = "helm"


def token() -> str:
    for name in ("SWITCHBOARD_TOKEN", "PM_MCP_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    print(
        "Missing SWITCHBOARD_TOKEN (or PM_MCP_TOKEN).\n"
        "Add it once in Cursor: Dashboard → Cloud Agents → Secrets.\n"
        "See docs/CLOUD-AGENT-SWITCHBOARD.md",
        file=sys.stderr,
    )
    sys.exit(2)


def parse_sse(body: str) -> dict[str, Any]:
    for line in body.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise RuntimeError(f"No SSE data frame in MCP response: {body[:500]!r}")


def mcp_call(tool: str, arguments: dict[str, Any] | None = None) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments or {}},
    }
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token()}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        frame = parse_sse(resp.read().decode())
    if "error" in frame:
        raise RuntimeError(json.dumps(frame["error"], indent=2))
    result = frame.get("result", {})
    if result.get("isError"):
        text = result.get("content", [{}])[0].get("text", "")
        raise RuntimeError(text or "MCP tool returned isError")
    content = result.get("content", [])
    if not content:
        return result
    text = content[0].get("text", "")
    if not text:
        return result
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def rest(method: str, path: str, body: dict[str, Any] | None = None, project: str = DEFAULT_PROJECT) -> Any:
    url = f"{REST_BASE}{path}"
    if "?" in url:
        url = f"{url}&project={project}" if "project=" not in url else url
    else:
        url = f"{url}?project={project}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token()}",
        },
        method=method.upper(),
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def cmd_doctor(_: argparse.Namespace) -> int:
    try:
        me = rest("GET", "/api/auth/me")
        print(json.dumps({"ok": True, "auth_me": me}, indent=2))
        summary = mcp_call("board_summary", {"project": DEFAULT_PROJECT})
        if isinstance(summary, str):
            print(summary[:2000])
        else:
            print(json.dumps(summary, indent=2)[:2000])
        return 0
    except (urllib.error.HTTPError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


def cmd_call(args: argparse.Namespace) -> int:
    tool_args = json.loads(args.args_json) if args.args_json else {}
    out = mcp_call(args.tool, tool_args)
    print(json.dumps(out, indent=2) if isinstance(out, (dict, list)) else out)
    return 0


def cmd_boot(args: argparse.Namespace) -> int:
    agent_id = args.agent_id
    common = {
        "runtime": args.runtime,
        "agent_id": agent_id,
        "project": DEFAULT_PROJECT,
        "model": args.model,
    }
    if args.task_id:
        common["task_id"] = args.task_id
    if args.lane:
        common["lane"] = args.lane

    steps = [
        ("prepare_agent_session", common),
        ("get_working_agreement", {"project": DEFAULT_PROJECT}),
        (
            "register_agent",
            {
                "project": DEFAULT_PROJECT,
                "agent_id": agent_id,
                "runtime": args.runtime,
                "model": args.model,
                "lane": args.lane or "",
                "task_id": args.task_id or "",
                "control_json": json.dumps({"mode": "advisory_poll"}),
                "protocol_json": json.dumps(
                    {
                        "compatible_versions": ["ixp.v1"],
                        "name": "switchboard",
                        "version": "ixp.v1",
                    }
                ),
            },
        ),
        ("list_unacked_messages", {"project": DEFAULT_PROJECT, "to_agent": agent_id}),
        ("board_summary", {"project": DEFAULT_PROJECT}),
    ]
    for name, arguments in steps:
        print(f"=== {name} ===")
        out = mcp_call(name, arguments)
        print(json.dumps(out, indent=2) if isinstance(out, (dict, list)) else out)
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Switchboard client for Helm Cloud Agents")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Verify token and board access")
    doctor.set_defaults(func=cmd_doctor)

    call = sub.add_parser("call", help="Call one MCP tool")
    call.add_argument("tool", help="MCP tool name, e.g. get_task")
    call.add_argument(
        "args_json",
        nargs="?",
        default="",
        help='JSON object of tool args, e.g. \'{"task_id":"CI-1","project":"helm"}\'',
    )
    call.set_defaults(func=cmd_call)

    boot = sub.add_parser("boot", help="Run standard Helm agent session handshake")
    boot.add_argument("--agent-id", default="cursor/cloud-agent")
    boot.add_argument("--runtime", default="cursor")
    boot.add_argument("--model", default="composer")
    boot.add_argument("--task-id", default="")
    boot.add_argument("--lane", default="")
    boot.set_defaults(func=cmd_boot)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
