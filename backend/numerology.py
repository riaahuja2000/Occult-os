"""TAROMAYA numerology engine + knowledge (Pythagorean system).

Pure data + calculation, no interface. Computes the core chart from a person's
full birth name and date of birth, and returns plain, easy-to-understand meanings.
"""
from __future__ import annotations
import re
from datetime import date

# Pythagorean letter -> number
_LETTER = {}
for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    _LETTER[ch] = (i % 9) + 1
VOWELS = set("AEIOU")
MASTERS = {11, 22, 33}


def _reduce(n: int) -> int:
    while n > 9 and n not in MASTERS:
        n = sum(int(d) for d in str(n))
    return n


def _letters(name: str) -> str:
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def _sum_letters(name: str, which: str = "all") -> int:
    total = 0
    for ch in _letters(name):
        if which == "vowels" and ch not in VOWELS:
            continue
        if which == "consonants" and ch in VOWELS:
            continue
        total += _LETTER[ch]
    return _reduce(total)


def life_path(d: date) -> int:
    parts = [_reduce(d.month), _reduce(d.day), _reduce(sum(int(x) for x in str(d.year)))]
    return _reduce(sum(parts))


# ---- knowledge (essence per number) --------------------------------------
NUMBER_ESSENCE = {
    1: {"title": "The Leader", "keywords": ["independent", "bold", "pioneering"],
        "meaning": "You lead best when you trust yourself. Start things, stand tall, and don't wait for permission."},
    2: {"title": "The Peacemaker", "keywords": ["gentle", "cooperative", "sensitive"],
        "meaning": "Your gift is harmony. Listen, team up, and let patience win — small kindness carries you far."},
    3: {"title": "The Creative", "keywords": ["expressive", "joyful", "social"],
        "meaning": "You shine when you create and share. Speak, make, and play — your joy is your power."},
    4: {"title": "The Builder", "keywords": ["steady", "practical", "loyal"],
        "meaning": "You win by being steady. Make a simple plan and do a little every day — brick by brick."},
    5: {"title": "The Free Spirit", "keywords": ["adventurous", "curious", "flexible"],
        "meaning": "You need freedom and change. Try new things, but pick one to finish so your energy counts."},
    6: {"title": "The Nurturer", "keywords": ["caring", "responsible", "loving"],
        "meaning": "You care for people and home. Give love, but keep a little for yourself too."},
    7: {"title": "The Seeker", "keywords": ["thoughtful", "spiritual", "wise"],
        "meaning": "You love to understand life. Take quiet time to think and trust your inner voice."},
    8: {"title": "The Achiever", "keywords": ["ambitious", "capable", "abundant"],
        "meaning": "You can build real success. Stay honest and balanced, and money and power will follow."},
    9: {"title": "The Humanitarian", "keywords": ["compassionate", "giving", "wise"],
        "meaning": "You are here to help and heal. Let go of the old, give freely, and lead with a big heart."},
    11: {"title": "The Intuitive (Master)", "keywords": ["inspired", "sensitive", "visionary"],
         "meaning": "You feel more than most. Trust your intuition and share your light to inspire others."},
    22: {"title": "The Master Builder", "keywords": ["visionary", "practical", "powerful"],
         "meaning": "You can turn big dreams into real things. Think big, but build it one careful step at a time."},
    33: {"title": "The Master Teacher", "keywords": ["loving", "healing", "devoted"],
         "meaning": "You uplift people through love and care. Serve with joy and remember to rest."},
}

DIMENSIONS = {
    "life_path": "Your main life journey and lessons.",
    "expression": "Your natural talents and how you show up in the world (from your full name).",
    "soul_urge": "What your heart truly wants (from the vowels in your name).",
    "personality": "How others first see you (from the consonants in your name).",
    "birthday": "A special gift you were born with (from your day of birth).",
    "maturity": "Who you grow into later in life (life path + expression).",
}


def _entry(num: int) -> dict:
    e = NUMBER_ESSENCE.get(num) or NUMBER_ESSENCE.get(_reduce(num))
    if not e:  # e.g. a name missing all vowels/consonants reduces to 0
        num, e = 9, NUMBER_ESSENCE[9]
    return {"number": num, "title": e["title"], "keywords": e["keywords"], "meaning": e["meaning"]}


def _build_reading_data(full_name: str, dob_iso: str) -> dict:
    """Helper to return the full numerology chart. dob_iso = 'YYYY-MM-DD'."""
    y, m, d = (int(x) for x in dob_iso.split("-"))
    dob = date(y, m, d)

    if not _letters(full_name):
        raise ValueError("Please provide the full birth name")

    lp = life_path(dob)
    expr = _sum_letters(full_name, "all")
    soul = _sum_letters(full_name, "vowels")
    pers = _sum_letters(full_name, "consonants")
    bday = _reduce(dob.day)
    maturity = _reduce(lp + expr)

    numbers = {
        "life_path": lp,
        "expression": expr,
        "soul_urge": soul,
        "personality": pers,
        "birthday": bday,
        "maturity": maturity,
    }
    chart = {}
    for key, num in numbers.items():
        item = _entry(num)
        item["dimension"] = DIMENSIONS[key]
        chart[key] = item
        numbers[key] = item["number"]  # keep numbers in sync with any safe fallback
    return {"name": full_name.strip(), "dob": dob_iso, "numbers": numbers, "chart": chart}


def reading(full_name: str, dob_iso: str) -> dict:
    try:
        data = _build_reading_data(full_name, dob_iso)
        return data
    except Exception as e:
        raise ValueError(f"Could not build reading: {e}")
