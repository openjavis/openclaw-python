#!/usr/bin/env python3
"""OpenClaw deployment validator for VM runtime and Vertex upstream."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


def load_simple_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def request_json(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any] | str]:
    data = None
    req_headers = headers.copy() if headers else {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url=url, method=method, headers=req_headers, data=data)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if not body:
                return resp.status, {}
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return e.code, parsed


def get_metadata_token() -> str:
    status, body = request_json(
        "GET",
        METADATA_TOKEN_URL,
        headers={"Metadata-Flavor": "Google"},
        timeout=10,
    )
    if status != 200 or not isinstance(body, dict) or not body.get("access_token"):
        raise RuntimeError(f"metadata token request failed: status={status}, body={body}")
    return str(body["access_token"])


def get_api_key() -> str:
    env_key = os.getenv("OPENCLAW_API_KEY")
    if env_key:
        return env_key.strip()

    key_file = Path.home() / ".openclaw" / "api_key"
    if key_file.exists():
        key = key_file.read_text().strip()
        if key:
            return key

    raise RuntimeError("API key not found (set OPENCLAW_API_KEY or ~/.openclaw/api_key)")


def check_vertex_upstream(base_url: str, model: str) -> tuple[bool, str]:
    token = get_metadata_token()
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "reply exactly: ok"}],
        "max_tokens": 256,
    }
    status, body = request_json(
        "POST",
        url,
        headers={"Authorization": f"Bearer {token}"},
        payload=payload,
        timeout=60,
    )
    if status != 200 or not isinstance(body, dict):
        return False, f"status={status}, body={body}"

    try:
        message = body["choices"][0].get("message", {})
        content = message.get("content")
        reasoning_content = message.get("reasoning_content")
    except Exception:
        message = {}
        content = None
        reasoning_content = None

    response_text = ""
    if isinstance(content, str) and content.strip():
        response_text = content.strip()
    elif isinstance(reasoning_content, str) and reasoning_content.strip():
        # Some upstream models stream reasoning only when max_tokens is small.
        response_text = reasoning_content.strip()

    if not response_text:
        return False, f"no content/reasoning_content in response: {body}"

    preview = response_text[:120] + ("..." if len(response_text) > 120 else "")
    return True, f"status={status}, text={preview!r}"


def check_openclaw_service(api_base: str, service_model: str) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    key = get_api_key()

    status, body = request_json("GET", f"{api_base.rstrip('/')}/health/live", timeout=10)
    results.append(("service_live", status == 200, f"status={status}, body={body}"))

    status, body = request_json(
        "GET",
        f"{api_base.rstrip('/')}/agent/sessions",
        headers={"x-api-key": key},
        timeout=10,
    )
    results.append(("agent_auth", status == 200, f"status={status}, body={body}"))

    status, body = request_json(
        "POST",
        f"{api_base.rstrip('/')}/agent/chat",
        headers={"x-api-key": key},
        payload={
            "session_id": "00000000-0000-4000-8000-000000000101",
            "message": "ตอบสั้นๆ คำว่า ok เท่านั้น",
            "model": service_model,
            "max_tokens": 256,
        },
        timeout=90,
    )

    basic_ok = False
    if status == 200 and isinstance(body, dict):
        basic_ok = bool(str(body.get("response", "")).strip())
    results.append(("agent_chat_basic", basic_ok, f"status={status}, body={body}"))

    status, body = request_json(
        "POST",
        f"{api_base.rstrip('/')}/agent/chat",
        headers={"x-api-key": key},
        payload={
            "session_id": "00000000-0000-4000-8000-000000000102",
            "message": "Use bash tool to run command pwd and return only the command output.",
            "model": service_model,
            "max_tokens": 512,
        },
        timeout=120,
    )

    tool_ok = False
    if status == 200 and isinstance(body, dict):
        response_text = str(body.get("response", "")).strip()
        tool_ok = response_text.startswith("/") and "workspace" in response_text
    results.append(("agent_chat_tool", tool_ok, f"status={status}, body={body}"))

    return results


def main() -> int:
    env_file = load_simple_env(Path.home() / ".env")

    base_url = os.getenv("OPENAI_BASE_URL") or env_file.get("OPENAI_BASE_URL")
    model = os.getenv("LLM_MODEL") or env_file.get("LLM_MODEL") or "zai-org/glm-5-maas"
    service_model = os.getenv("OPENCLAW_VALIDATE_MODEL") or "google/gemini-3-flash-preview"
    api_base = os.getenv("OPENCLAW_API_URL") or "http://127.0.0.1:8000"

    if not base_url:
        print("[FAIL] OPENAI_BASE_URL is not set in env or ~/.env")
        return 1

    print(f"Vertex base URL : {base_url}")
    print(f"Vertex model    : {model}")
    print(f"Service API URL : {api_base}")
    print(f"Service model   : {service_model}")
    print()

    failures = 0

    ok, detail = check_vertex_upstream(base_url, model)
    print(f"[{'PASS' if ok else 'FAIL'}] vertex_upstream: {detail}")
    if not ok:
        failures += 1

    for name, passed, detail in check_openclaw_service(api_base, service_model):
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        if not passed:
            failures += 1

    print()
    if failures:
        print(f"Validation failed: {failures} check(s) failed")
        return 1

    print("Validation passed: all checks succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
