import pytest
from numerology import _letters

def test_letters_happy_path():
    assert _letters('John Doe') == 'JOHNDOE'
    assert _letters('Jane') == 'JANE'

def test_letters_edge_cases():
    assert _letters(None) == ''
    assert _letters('') == ''
    assert _letters(' ') == ''

def test_letters_special_characters():
    assert _letters('John Doe 123!') == 'JOHNDOE'
    assert _letters('áéíóú') == ''
    assert _letters('J@ne D0e') == 'JNEDE'
