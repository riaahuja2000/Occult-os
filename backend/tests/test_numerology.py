import pytest
from unittest.mock import patch
from numerology import reading, _build_reading_data

def test_reading_invalid_date_format():
    with pytest.raises(ValueError, match="Could not build reading:.*"):
        reading("Ria Ahuja", "notadate")

def test_reading_invalid_date_values():
    with pytest.raises(ValueError, match="Could not build reading:.*"):
        reading("Ria Ahuja", "2000-13-40")

def test_reading_empty_name():
    with pytest.raises(ValueError, match="Could not build reading:.*"):
        reading("", "2000-11-29")

def test_reading_whitespace_name():
    with pytest.raises(ValueError, match="Could not build reading:.*"):
        reading("   ", "2000-11-29")

def test_reading_no_letters_name():
    with pytest.raises(ValueError, match="Could not build reading:.*"):
        reading("123", "2000-11-29")

@patch("numerology._build_reading_data")
def test_reading_general_exception(mock_build_reading_data):
    mock_build_reading_data.side_effect = Exception("Some arbitrary error")
    with pytest.raises(ValueError, match="Could not build reading: Some arbitrary error"):
        reading("Valid Name", "2000-01-01")
