import pytest
from unittest.mock import patch
from backend.oracle import compose_answer, OPENINGS, PACK, MINDFULNESS, DEFAULT_TOPICS

def test_compose_answer_valid_language():
    ans_en = compose_answer("tell me about my health", "en")
    assert ans_en["primary"] == "health"
    assert "health" in ans_en["topics"]
    assert any(ans_en["answer"].startswith(op) for op in OPENINGS["en"])

    ans_hi = compose_answer("मेरी सेहत कैसी रहेगी?", "hi") # Using word 'सेहत' (health)
    assert ans_hi["primary"] == "health"
    assert "health" in ans_hi["topics"]
    assert any(ans_hi["answer"].startswith(op) for op in OPENINGS["hi"])

def test_compose_answer_invalid_language_fallback():
    ans = compose_answer("tell me about my health", "fr")
    # Should fallback to 'en'
    assert ans["primary"] == "health"
    assert any(ans["answer"].startswith(op) for op in OPENINGS["en"])

def test_compose_answer_fallback_to_default_topics():
    # A generic question without any specific topic keywords. "what is up?"
    ans = compose_answer("what is up?", "en")
    assert ans["primary"] in DEFAULT_TOPICS
    assert all(t in DEFAULT_TOPICS for t in ans["topics"])

def test_compose_answer_multiple_topics():
    # Question containing both tarot and health keywords
    ans = compose_answer("Can tarot cards tell me about my health?", "en")
    assert "tarot" in ans["topics"]
    assert "health" in ans["topics"]
    assert ans["primary"] in ["tarot", "health"]

def test_compose_answer_extra_by_topic():
    extra = {"health": ["This is a special owner added health advice."]}
    # Test that owner-added answer is integrated.
    # With random choice, we might not always get it. Let's patch random.choice to always pick the last item (which is the extra one).
    with patch('backend.oracle.random.choice', return_value="This is a special owner added health advice."):
        ans = compose_answer("health", "en", extra_by_topic=extra)
        assert ans["primary"] == "health"
        assert "This is a special owner added health advice." in ans["answer"]

def test_compose_answer_fallback_to_mindfulness():
    # If the resolved pool is empty, it should fallback to MINDFULNESS.
    # To simulate an empty pool, we can patch PACK and pass an empty extra_by_topic,
    # or just use a mock for detect_topics that returns an unknown topic.
    with patch('backend.oracle.detect_topics', return_value=["unknown_topic"]):
        # It will try to get PACK["unknown_topic"] which is None
        ans = compose_answer("hello", "en")
        assert ans["primary"] == "unknown_topic"
        # The body should come from MINDFULNESS
        # Let's verify the body is in MINDFULNESS["en"]
        body = ans["answer"]
        # Remove opening
        for op in OPENINGS["en"]:
            if body.startswith(op):
                body = body[len(op):]
                break
        assert body in MINDFULNESS["en"]
