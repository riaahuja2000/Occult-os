import pytest
from oracle import clean_for_tts

def test_clean_for_tts_removes_urls():
    assert clean_for_tts("Check this http://example.com and this https://secure.com out") == "Check this and this out"
    assert clean_for_tts("URL at the end https://test.com") == "URL at the end"
    assert clean_for_tts("https://test.com URL at the beginning") == "URL at the beginning"

def test_clean_for_tts_removes_code_blocks():
    assert clean_for_tts("Run `npm install` first") == "Run first"
    assert clean_for_tts("Here is some code ```python\nprint('hello')\n``` wow") == "Here is some code wow"
    assert clean_for_tts("Inline `code` and block ```more code```") == "Inline and block"

def test_clean_for_tts_removes_markdown_chars():
    assert clean_for_tts("This is *bold* and _italic_") == "This is bold and italic"
    assert clean_for_tts("# Heading 1") == "Heading 1"
    assert clean_for_tts("> Blockquote") == "Blockquote"
    assert clean_for_tts("~Strikethrough~ and |Pipe|") == "Strikethrough and Pipe"

def test_clean_for_tts_fixes_whitespace():
    assert clean_for_tts("  Too   many \n spaces \t here  ") == "Too many spaces here"
    assert clean_for_tts("One\nTwo\n\nThree") == "One Two Three"

def test_clean_for_tts_combined():
    text = "  # Hello! \n Check out `my code` here: https://github.com/abc \n It is *awesome_stuff* ~right~? > yes | no \n\n"
    expected = "Hello! Check out here: It is awesomestuff right? yes no"
    assert clean_for_tts(text) == expected
