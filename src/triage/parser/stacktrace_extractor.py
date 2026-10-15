"""Multi-language stack trace and error extractor."""

import re
from typing import Optional


# Regex extractors for various runtime languages
PYTHON_TRACEBACK_RE = re.compile(
    r"(Traceback \(most recent call last\):[\s\S]*?(?:^[A-Za-z_]+Error:[^\n]+|AssertionError:[^\n]+))",
    re.MULTILINE
)

JAVA_STACKTRACE_RE = re.compile(
    r"((?:Exception in thread|java\.lang\.\w+Exception|org\.\w+\.[\w\.]+Exception):[^\n]+(?:\n\s+at [^\n]+)+)",
    re.MULTILINE
)

NPM_ERROR_RE = re.compile(
    r"(npm ERR![\s\S]*?npm ERR! A complete log of this run can be found in:)",
    re.MULTILINE
)

GO_PANIC_RE = re.compile(
    r"(panic:[^\n]+(?:\n\ngoroutine \d+ [^\n]+:\n[\s\S]*?(?=\n\n|\Z)))",
    re.MULTILINE
)


def extract_stacktrace(snippet: str) -> Optional[str]:
    """Tries to extract the precise stack trace block from the snippet."""
    if not snippet:
        return None

    # Check Python Traceback
    match = PYTHON_TRACEBACK_RE.search(snippet)
    if match:
        return match.group(1).strip()

    # Check Java Stack Trace
    match = JAVA_STACKTRACE_RE.search(snippet)
    if match:
        return match.group(1).strip()

    # Check Go Panic
    match = GO_PANIC_RE.search(snippet)
    if match:
        return match.group(1).strip()

    # Check NPM Error
    match = NPM_ERROR_RE.search(snippet)
    if match:
        return match.group(1).strip()

    return None
