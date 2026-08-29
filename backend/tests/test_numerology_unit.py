from numerology import _reduce, _letters

def test_reduce_single_digit():
    for i in range(1, 10):
        assert _reduce(i) == i

def test_reduce_master_numbers():
    assert _reduce(11) == 11
    assert _reduce(22) == 22
    assert _reduce(33) == 33

def test_reduce_normal_numbers():
    assert _reduce(10) == 1
    assert _reduce(12) == 3
    assert _reduce(28) == 1  # 28 -> 10 -> 1
    assert _reduce(99) == 9  # 99 -> 18 -> 9
    assert _reduce(1990) == 1 # 1990 -> 19 -> 10 -> 1

def test_reduce_large_number():
    assert _reduce(9999999999) == 9

def test_letters():
    assert _letters("Ria Ahuja") == "RIAAHUJA"
    assert _letters("Ria Ahuja 123") == "RIAAHUJA"
    assert _letters("Ria-Ahuja") == "RIAAHUJA"
    assert _letters("ria ahuja") == "RIAAHUJA"
    assert _letters("") == ""
    assert _letters(None) == ""
    assert _letters("1234!@#$") == ""
