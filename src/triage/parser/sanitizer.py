"""ANSI escape code stripper and terminal output normalizer."""

import re

# Comprehensive ANSI escape sequence regex
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CARRIAGE_RETURN_RE = re.compile(r"\r\n|\r")


def sanitize_log(raw_log: str) -> str:
    """Strips ANSI formatting, color codes, and normalizes line endings."""
    if not raw_log:
        return ""

    # Normalize line breaks
    normalized = CARRIAGE_RETURN_RE.sub("\n", raw_log)

    # Strip ANSI escape sequences
    cleaned = ANSI_ESCAPE_RE.sub("", normalized)

    # Strip non-printable control characters except newline and tab
    cleaned = "".join(ch for ch in cleaned if ch in ("\n", "\t") or (ord(ch) >= 32 and ord(ch) != 127))

    return cleaned.strip()
