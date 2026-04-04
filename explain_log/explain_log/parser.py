import re
import sys
from typing import Optional


# ── log type detection patterns ───────────────────────────────────────────────

LOG_TYPE_PATTERNS = {
    "windows":  [
        r"Event ID",
        r"Faulting application",
        r"Exception code",
        r"Service Control Manager",
        r"The system cannot find",
        r"Faulting module",
        r"\.dll",
    ],
    "nginx":    [r"nginx", r"\[error\]", r"upstream", r"GET |POST |PUT |DELETE ", r"HTTP/1"],
    "systemd":  [r"systemd\[", r"\.service:", r"Started |Stopped |Failed ", r"journalctl"],
    "python":   [r"Traceback \(most recent call last\)", r"^\s+File \"", r"Error:", r"Exception:"],
    "kernel":   [r"kernel:", r"\[\s*\d+\.\d+\]", r"Out of memory", r"segfault at", r"oom_reaper"],
    "apache":   [r"apache2?", r"\[warn\]", r"\[crit\]", r"AH\d{5}"],
    "postgres": [r"postgres", r"LOG:", r"FATAL:", r"pg_ctl", r"PANIC:"],
    "ssh":      [r"sshd\[", r"Failed password", r"Invalid user", r"Accepted publickey"],
    "docker":   [r"dockerd", r"containerd", r"container \w+ died", r"OCI runtime"],
}


# ── error patterns ────────────────────────────────────────────────────────────

ERROR_PATTERNS = [
    r"\b(error|err)\b",
    r"\b(warn|warning)\b",
    r"\bcritical\b",
    r"\bfatal\b",
    r"\bfailed?\b",
    r"\bpanic\b",
    r"\bexception\b",
    r"\btraceback\b",
    r"\bkilled\b",
    r"\bsegfault\b",
    r"\bcore dumped\b",
    r"\boom\b",
    r"\bdenied\b",
    r"\brefused\b",
    r"\btimeout\b",
    r"\bcrash\b",
    r"\babort\b",
    r"\bcannot\b",
    r"\bunable to\b",
    r"\bno such file\b",
    r"\bpermission denied\b",
    r"\bconnection refused\b",
    r"\baddress already in use\b",
]

_ERROR_RE = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)

_TYPE_RES = {
    log_type: [re.compile(p, re.IGNORECASE) for p in patterns]
    for log_type, patterns in LOG_TYPE_PATTERNS.items()
}


# ── noise filter ──────────────────────────────────────────────────────────────

_NOISE_RE = re.compile(
    r"^\s*$"
    r"|--+ (BEGIN|END) --+"
    r"|\[\s*ok\s*\]"
    r"|Started.*\.$"
    r"|Reached target"
    r"|systemd\[1\]: Starting ",
    re.IGNORECASE
)


# ── public api ────────────────────────────────────────────────────────────────

def preprocess(
    raw_text: str,
    last_n: Optional[int] = None,
    max_tokens: int = 3000,
) -> dict:

    if not raw_text or not raw_text.strip():
        raise EmptyLogError("Log input is empty.")

    all_lines = raw_text.splitlines()
    original_count = len(all_lines)

    if last_n is not None:
        all_lines = all_lines[-last_n:]

    log_type = _detect_log_type(all_lines)
    filtered = _filter_lines(all_lines)

    if not filtered:
        filtered = [l for l in all_lines[-30:] if not _NOISE_RE.search(l)]

    filtered, truncated = _apply_token_budget(filtered, max_tokens)

    return {
        "lines": filtered,
        "log_type": log_type,
        "line_count": original_count,
        "truncated": truncated,
    }


# ── detection logic ───────────────────────────────────────────────────────────

def _detect_log_type(lines: list[str]) -> str:
    sample_text = "\n".join(lines[:200])

    scores = {}
    for log_type, patterns in _TYPE_RES.items():
        score = sum(1 for p in patterns if p.search(sample_text))
        if score:
            scores[log_type] = score

    if not scores:
        return "unknown"

    return max(scores, key=scores.get)


# ── filtering ─────────────────────────────────────────────────────────────────

def _filter_lines(lines: list[str]) -> list[str]:
    kept = []
    keep_next = False

    for line in lines:
        if _NOISE_RE.search(line):
            keep_next = False
            continue

        if keep_next:
            kept.append(line)
            keep_next = False
            continue

        if _ERROR_RE.search(line):
            kept.append(line)
            keep_next = True

    return kept


# ── token control ─────────────────────────────────────────────────────────────

def _apply_token_budget(lines: list[str], max_tokens: int):
    char_budget = max_tokens * 4
    total_chars = sum(len(l) for l in lines)

    if total_chars <= char_budget:
        return lines, False

    kept = []
    chars = 0

    for line in reversed(lines):
        if chars + len(line) > char_budget:
            break
        kept.append(line)
        chars += len(line)

    return list(reversed(kept)), True


# ── errors ────────────────────────────────────────────────────────────────────

class ExplainLogError(Exception):
    pass


class EmptyLogError(ExplainLogError):
    pass


# ── test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = """
    Event ID: 7000
    The system cannot find the file specified.
    Faulting application name: python.exe
    Exception code: 0xc0000005
    """

    import json
    print(json.dumps(preprocess(sample), indent=2))
