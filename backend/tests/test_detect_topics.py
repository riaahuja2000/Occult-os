import pytest
from backend.oracle import detect_topics

def test_detect_topics_empty_or_none():
    assert detect_topics(None) == ["general"]
    assert detect_topics("") == ["general"]
    assert detect_topics("   ") == ["general"]

def test_detect_topics_method_match():
    assert "tarot" in detect_topics("tell me about my tarot cards")
    assert "astrology" in detect_topics("what is my zodiac sign")

def test_detect_topics_life_match():
    assert "relationships" in detect_topics("will I find love?")
    assert "career" in detect_topics("what about my career path")

def test_detect_topics_multiple_matches():
    topics = detect_topics("I want a tarot reading about my love life and career")
    assert "tarot" in topics
    assert "relationships" in topics
    assert "career" in topics

def test_detect_topics_case_insensitive():
    topics = detect_topics("TAROT and LOVE")
    assert "tarot" in topics
    assert "relationships" in topics

def test_detect_topics_no_match_returns_general():
    assert detect_topics("what color is the sky") == ["general"]
    assert detect_topics("random nonsense string xyz abc") == ["general"]
