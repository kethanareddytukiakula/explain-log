import os
import json
import sys

try:
    from groq import Groq
except ImportError:
    print("Error: groq not installed. Run: pip install groq")
    sys.exit(1)


# ── UPDATED SYSTEM PROMPT ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert systems engineer and debugger.

You analyze logs from:
- Linux systems (systemd, kernel, nginx)
- Python applications (tracebacks)
- Windows systems (Event Viewer, Service Control Manager, DLL errors)

Given a log excerpt, respond ONLY with a valid JSON object — no markdown, no explanation outside the JSON.

Schema:
{
  "diagnosis": "2-3 sentence plain-English explanation of the root cause",
  "fixes": ["fix 1", "fix 2", "fix 3"],
  "severity": "critical | warn | info"
}

Rules:
- If logs contain "Event ID", "Faulting application", "Exception code" → treat as Windows errors
- If logs contain "Traceback" → treat as Python errors
- Otherwise assume Linux/system logs

- severity is "critical" if system crashed, OOM killed, or service failed
- severity is "warn" for recoverable errors or warnings  
- severity is "info" if there are no real errors

- fixes must be specific and actionable — no generic advice like "check config"
- if no errors are found:
  diagnosis = "No errors found."
  fixes = []

Return ONLY JSON.
"""


# ── BUILD USER MESSAGE ────────────────────────────────────────────────────────

def _build_user_message(parsed: dict) -> str:
    log_type = parsed.get("log_type", "unknown")
    lines = parsed.get("lines", [])
    truncated = parsed.get("truncated", False)

    header = f"Log type: {log_type}\n"
    if truncated:
        header += f"(Log was truncated to {len(lines)} most relevant lines)\n"
    header += "\n--- LOG START ---\n"

    return header + "\n".join(lines) + "\n--- LOG END ---"


# ── CLIENT SETUP ──────────────────────────────────────────────────────────────

def _get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set.\n"
            "Set it using:\n"
            "  setx GROQ_API_KEY \"your_key_here\"\n"
            "Get a free key at: https://console.groq.com/keys"
        )
    return Groq(api_key=api_key)


# ── MAIN ANALYSIS FUNCTION ────────────────────────────────────────────────────

def analyze(parsed: dict, stream: bool = True) -> dict:
    client = _get_client()
    user_message = _build_user_message(parsed)

    try:
        if stream:
            return _analyze_streaming(client, user_message)
        else:
            return _analyze_blocking(client, user_message)

    except EnvironmentError:
        raise
    except RateLimitError:
        raise
    except Exception as e:
        err_str = str(e).lower()

        if any(kw in err_str for kw in ("rate limit", "429", "quota", "too many requests")):
            raise RateLimitError(
                "Groq free tier rate limit hit.\n"
                "Try again in a few seconds or upgrade your plan."
            ) from e

        raise APIError(f"Groq API call failed: {e}") from e


# ── BLOCKING CALL ─────────────────────────────────────────────────────────────

def _analyze_blocking(client: Groq, user_message: str) -> dict:
    model = os.environ.get("EXPLAIN_LOG_MODEL", "llama-3.3-70b-versatile")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    return _parse_response(response.choices[0].message.content)


# ── STREAMING CALL ────────────────────────────────────────────────────────────

def _analyze_streaming(client: Groq, user_message: str) -> dict:
    model = os.environ.get("EXPLAIN_LOG_MODEL", "llama-3.3-70b-versatile")

    full_text = ""
    print("  analyzing", end="", file=sys.stderr, flush=True)

    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=1024,
        stream=True,
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            full_text += token
            print(".", end="", file=sys.stderr, flush=True)

    print(" done", file=sys.stderr, flush=True)
    return _parse_response(full_text)


# ── PARSE RESPONSE ────────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    cleaned = raw.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model returned non-JSON response.\nRaw output:\n{raw}\nParse error: {e}"
        )

    return {
        "diagnosis": result.get("diagnosis", "Could not determine root cause."),
        "fixes": result.get("fixes", []),
        "severity": result.get("severity", "warn")
        if result.get("severity") in ("critical", "warn", "info")
        else "warn",
    }


# ── CUSTOM ERRORS ─────────────────────────────────────────────────────────────

class ExplainLogError(Exception):
    pass


class APIError(ExplainLogError):
    pass


class RateLimitError(ExplainLogError):
    pass


# ── TEST BLOCK ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fake_parsed = {
        "log_type": "windows",
        "truncated": False,
        "lines": [
            "Faulting application name: python.exe",
            "Exception code: 0xc0000005",
            "Event ID: 7000",
            "The system cannot find the file specified."
        ]
    }

    result = analyze(fake_parsed, stream=True)
    print("\n--- RESULT ---")
    print(json.dumps(result, indent=2))
