import pytest
from backend.oracle import clean_for_tts

def test_clean_for_tts_normal():
    assert clean_for_tts("Hello world.") == "Hello world."

def test_clean_for_tts_strip_asterisks():
    assert clean_for_tts("This is **bold** and *italic*") == "This is bold and italic"

def test_clean_for_tts_strip_hashes():
    assert clean_for_tts("### Header #") == "Header"

def test_clean_for_tts_combined():
    text = "Hello! *Check* #out#"
    expected = "Hello! Check out"
    assert clean_for_tts(text) == expected

def test_clean_for_tts_strip_urls():
    assert clean_for_tts("Check https://example.com") == "Check"

def test_clean_for_tts_strip_code():
    assert clean_for_tts("Code `print(1)` block ```python\npass\n```") == "Code block"

def test_clean_for_tts_whitespace():
    assert clean_for_tts("A  b   \n c") == "A b c"
