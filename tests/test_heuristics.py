"""Unit tests for the deterministic heuristic classifier engine."""

from triage.classifier.heuristic_engine import HeuristicEngine
from triage.models import ErrorCategory


def test_classify_oom():
    engine = HeuristicEngine()
    log = "Building container... \nKilled process 999\nOOMKilled: true\nexit code 137"
    match = engine.classify(log)
    assert match is not None
    assert match.category == ErrorCategory.OUT_OF_MEMORY_OOM
    assert match.confidence >= 0.95


def test_classify_dependency_conflict():
    engine = HeuristicEngine()
    log = "Traceback:\nModuleNotFoundError: No module named 'pydantic_settings'"
    match = engine.classify(log)
    assert match is not None
    assert match.category == ErrorCategory.DEPENDENCY_CONFLICT


def test_classify_syntax_error():
    engine = HeuristicEngine()
    log = "File 'app.py', line 12\n  def foo(:\n          ^\nSyntaxError: invalid syntax"
    match = engine.classify(log)
    assert match is not None
    assert match.category == ErrorCategory.SYNTAX_COMPILE_ERROR


def test_classify_permission_denied():
    engine = HeuristicEngine()
    log = "Pushing image to registry... HTTP 403 Forbidden: AccessDeniedException"
    match = engine.classify(log)
    assert match is not None
    assert match.category == ErrorCategory.PERMISSION_SECRET_MISSING


def test_classify_test_assertion_failure():
    engine = HeuristicEngine()
    log = "=== FAILURES ===\n_ test_login _\nAssertionError: assert False is True"
    match = engine.classify(log)
    assert match is not None
    assert match.category == ErrorCategory.TEST_ASSERTION_FAILURE
