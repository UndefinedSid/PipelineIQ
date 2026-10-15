"""Unit tests for ANSI stripping and log sanitization."""

import pytest
from triage.parser.sanitizer import sanitize_log


def test_sanitize_ansi_color_codes():
    raw = "\x1b[31m[ERROR]\x1b[0m \x1b[1;33mAssertion failed\x1b[0m\r\nLine 42"
    cleaned = sanitize_log(raw)
    assert "\x1b[" not in cleaned
    assert "[ERROR] Assertion failed\nLine 42" == cleaned


def test_sanitize_empty_and_normal_text():
    assert sanitize_log("") == ""
    assert sanitize_log("Just normal log text") == "Just normal log text"


def test_sanitize_carriage_returns():
    raw = "Building layer 1\r\nBuilding layer 2\r\nDone"
    cleaned = sanitize_log(raw)
    assert "\r" not in cleaned
    assert "Building layer 1\nBuilding layer 2\nDone" == cleaned
