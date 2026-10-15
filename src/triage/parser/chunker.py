"""Reverse-tail sliding window log chunker."""

from typing import List, Tuple

# Anchor keywords commonly found near root cause failures in CI
ERROR_ANCHORS = [
    "Traceback (most recent call last):",
    "FAILURES",
    "FAILURE:",
    "BUILD FAILED",
    "npm ERR!",
    "yarn error",
    "panic:",
    "fatal error:",
    "exit code 137",
    "JavaScript heap out of memory",
    "OutOfMemoryError",
    "Segmentation fault",
    "AssertionError:",
    "##[error]",
    "FATAL:",
    "ERROR:",
    "pytest.fail",
    "Error: Process completed with exit code",
]


def extract_high_signal_window(
    log_text: str,
    max_lines: int = 200,
    context_before: int = 50
) -> Tuple[str, int, int]:
    """
    Scans the log in reverse (from bottom up) to identify the latest failure anchor.
    Extracts a high-signal slice (context before + error details) to minimize token usage.

    Returns:
        (extracted_snippet, total_lines, extracted_lines)
    """
    if not log_text:
        return "", 0, 0

    lines: List[str] = log_text.splitlines()
    total_lines = len(lines)

    if total_lines <= max_lines:
        return log_text, total_lines, total_lines

    # Find the latest (closest to EOF) error anchor line index
    anchor_idx = -1
    for i in range(total_lines - 1, -1, -1):
        line = lines[i]
        for anchor in ERROR_ANCHORS:
            if anchor in line:
                anchor_idx = i
                break
        if anchor_idx != -1:
            break

    # If an anchor is found, create the window around it
    if anchor_idx != -1:
        start_idx = max(0, anchor_idx - context_before)
        end_idx = min(total_lines, start_idx + max_lines)
        # If we hit the end of the file, slide start_idx back to capture full max_lines if available
        if end_idx - start_idx < max_lines and total_lines >= max_lines:
            start_idx = max(0, end_idx - max_lines)
    else:
        # Fallback to the last max_lines of the log
        start_idx = max(0, total_lines - max_lines)
        end_idx = total_lines

    selected_lines = lines[start_idx:end_idx]
    snippet = "\n".join(selected_lines)
    return snippet, total_lines, len(selected_lines)
