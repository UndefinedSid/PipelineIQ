"""Unit tests for reverse-tail chunking and sliding window logic."""

from triage.parser.chunker import extract_high_signal_window


def test_chunker_small_log():
    log = "Line 1\nLine 2\nLine 3"
    snippet, total, extracted = extract_high_signal_window(log, max_lines=10)
    assert total == 3
    assert extracted == 3
    assert snippet == log


def test_chunker_reverse_anchor_search():
    # Construct a log of 500 lines with an error anchor around line 450
    lines = [f"Step {i}: normal execution log message" for i in range(500)]
    lines[450] = "Traceback (most recent call last):"
    lines[451] = "  File 'app/main.py', line 10, in <module>"
    lines[452] = "ZeroDivisionError: division by zero"
    lines[480] = "##[error]Process completed with exit code 1."

    log_text = "\n".join(lines)
    snippet, total, extracted = extract_high_signal_window(log_text, max_lines=100, context_before=30)

    assert total == 500
    assert extracted == 100
    assert "ZeroDivisionError: division by zero" in snippet
    assert "Traceback (most recent call last):" in snippet
    assert "Step 0:" not in snippet  # Initial noise successfully stripped
