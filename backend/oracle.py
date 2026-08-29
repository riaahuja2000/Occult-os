"""VELORA oracle engine.

The complete knowledge base (oracle-pack.json + the source PDF) lives ONLY on the
server and is never shipped to the client. Answers are produced strictly from this
stored knowledge pack: question -> topic detection -> knowledge-base answer -> verified
final answer text (which is then spoken).
"""
import json
import random
import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

with open(KNOWLEDGE_DIR / "oracle-pack.json", "r", encoding="utf-8") as _f:
    PACK: dict = json.load(_f)

LANGS = ("en", "hi", "hng")

OPENINGS = {
    "en": ["Here's the simple truth: ", "In easy words: ", "Simply put: "],
    "hi": ["आसान भाषा में: ", "सीधी बात: ", "सरल शब्दों में: "],
    "hng": ["Simple baat: ", "Aasan bhaasha mein: ", "Seedhi baat: "],
}

METHOD_KEYWORDS = {
    "tarot": ["tarot", "card", "major arcana", "minor arcana", "spread", "fool", "magician",
              "high priestess", "empress", "emperor", "hierophant", "lovers", "chariot",
              "strength", "hermit", "wheel", "justice", "hanged", "death", "temperance",
              "devil", "tower", "star", "cups", "swords", "wands", "pentacles", "टैरो", "पत्ते"],
    "astrology": ["astrology", "zodiac", "planet", "saturn", "venus", "mars", "mercury",
                  "jupiter", "rising", "ascendant", "horoscope", "navagraha", "nakshatra",
                  "panchanga", "houses", "aspects", "aries", "taurus", "gemini", "cancer",
                  "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius",
                  "pisces", "retrograde", "transit", "jyotish", "kundli", "graha",
                  "ज्योतिष", "कुंडली", "राशि", "ग्रह"],
    "numerology": ["numerology", "number", "life path", "destiny number", "birth number",
                   "chaldean", "pythagorean", "lo shu", "gematria", "अंक", "अंकज्योतिष"],
    "runes": ["rune", "elder futhark", "ogham", "runes", "runic", "रून"],
    "crystals": ["crystal", "gem", "stone", "amethyst", "quartz", "rose quartz", "obsidian",
                 "citrine", "moonstone", "labradorite", "clear quartz", "क्रिस्टल", "रत्न"],
    "aura": ["chakra", "aura", "energy", "subtle body", "kundalini", "prana", "seven chakras",
             "root chakra", "heart chakra", "third eye", "आभा", "चक्र"],
    "palmistry": ["palmistry", "palm", "hand", "life line", "heart line", "head line",
                  "fate line", "mounts", "हस्तरेखा", "हथेली"],
    "feng-shui": ["feng shui", "vastu", "direction", "space", "bagua", "trigram",
                  "five phases", "five elements", "compass", "वास्तु", "फेंग शुई"],
    "kabbalah": ["kabbalah", "sefirot", "sephiroth", "hermetic", "alchemy", "tree of life",
                 "qabalah", "agrippa", "कब्बाला"],
    "i-ching": ["i ching", "yijing", "hexagram", "iching", "yi jing", "आई चिंग"],
}

LIFE_KEYWORDS = {
    "relationships": ["relationship", "love", "partner", "marriage", "spouse", "boyfriend",
                      "girlfriend", "husband", "wife", "breakup", "ex", "commitment", "date",
                      "dating", "pyaar", "ishq", "shaadi", "rishta", "प्यार", "शादी", "रिश्ता"],
    "career": ["career", "job", "work", "promotion", "boss", "office", "profession",
               "business", "kaam", "naukri", "नौकरी", "काम", "बिज़नेस"],
    "money": ["money", "finance", "financial", "wealth", "rich", "debt", "loan", "invest", "income",
              "paisa", "dhan", "पैसा", "धन", "लोन"],
    "health": ["health", "sick", "illness", "disease", "wellness", "healing", "body",
               "sehat", "bimari", "सेहत", "बीमारी"],
    "purpose": ["purpose", "calling", "destiny", "soul", "meaning", "path", "spiritual",
                "dharma", "spirit", "journey", "why am i", "life mission", "धर्म", "आत्मा"],
    "mindfulness": ["mindful", "mindfulness", "meditate", "meditation", "breath", "breathe",
                    "calm", "peace", "peaceful", "stress", "anxiety", "anxious", "worry",
                    "present", "presence", "stillness", "grounded", "let go", "overthink",
                    "shanti", "dhyan", "shaanti", "मन", "ध्यान", "शांति", "तनाव", "चिंता"],
    "timing": ["when", "timing", "soon", "wait", "how long", "kab", "कब", "समय"],
    "daily": ["aaj", "today", "daily", "day", "din", "tomorrow", "kal", "आज", "दिन", "रोज़"],
}

# Occult / aura / mindfulness default pool — used instead of any generic answer.
MINDFULNESS = {
    "en": [
        "Stop and take three slow breaths. Feel your feet on the floor. Now your mind is calmer, and the next step feels clear.",
        "You don't have to fix everything right now. Do one small kind thing for yourself and breathe. That is enough for today.",
    ],
    "hi": [
        "रुको और तीन धीमी साँसें लो। पैर ज़मीन पर महसूस करो। अब मन शांत है और अगला कदम साफ़ लगेगा।",
        "सब कुछ अभी ठीक करना ज़रूरी नहीं। खुद के लिए एक छोटा अच्छा काम करो और साँस लो। आज के लिए इतना काफ़ी है।",
    ],
    "hng": [
        "Ruko aur teen dheemi saansein lo. Pair zameen par feel karo. Ab mann calm hai aur agla step clear lagega.",
        "Sab kuch abhi fix karna zaroori nahi. Khud ke liye ek chhota accha kaam karo aur saans lo. Aaj ke liye itna kaafi hai.",
    ],
}
PACK["mindfulness"] = MINDFULNESS

# ELI5 override — every answer is short, plain and easy to understand (occult / aura / mindfulness only).
ELI5 = {
    "tarot": {
        "en": ["the cards say a new chapter is starting. Don't be scared — pick one small thing to try today and you'll feel better.",
               "the cards say you already know the answer inside. Trust it, take one tiny step, and see what happens."],
        "hi": ["पत्ते कहते हैं एक नई शुरुआत हो रही है। डरो मत — आज एक छोटा काम करो, अच्छा लगेगा।",
               "पत्ते कहते हैं उत्तर तुम्हारे अंदर है। भरोसा करो और एक छोटा कदम बढ़ाओ।"],
        "hng": ["cards kehte hain ek nayi shuruaat ho rahi hai. Daro mat — aaj ek chhota kaam karo, accha lagega.",
                "cards kehte hain jawab tumhare andar hai. Bharosa karo aur ek chhota step lo."]},
    "astrology": {
        "en": ["the stars say this is a slow time, not a bad time. Be patient, do a little each day, and things will line up.",
               "the sky says focus on one goal, not ten. Pick the one that matters most and give it your energy."],
        "hi": ["तारे कहते हैं यह धीमा समय है, बुरा नहीं। धैर्य रखो, रोज़ थोड़ा करो, सब ठीक होगा।",
               "आकाश कहता है एक लक्ष्य चुनो, दस नहीं। सबसे ज़रूरी पर ध्यान दो।"],
        "hng": ["sitare kehte hain yeh slow time hai, bura nahi. Patience rakho, roz thoda karo, sab set ho jayega.",
                "aasman kehta hai ek goal chuno, das nahi. Sabse zaroori par focus karo."]},
    "numerology": {
        "en": ["your numbers say keep things simple. Do one clear task well today instead of many at once.",
               "your numbers say a fresh start is near. Finish one old thing first, then begin the new."],
        "hi": ["तुम्हारे अंक कहते हैं चीज़ें सरल रखो। आज एक काम अच्छे से करो।",
               "तुम्हारे अंक कहते हैं नई शुरुआत पास है। पहले एक पुराना काम पूरा करो।"],
        "hng": ["tumhare numbers kehte hain cheezein simple rakho. Aaj ek kaam acche se karo.",
                "tumhare numbers kehte hain nayi shuruaat paas hai. Pehle ek purana kaam poora karo."]},
    "runes": {
        "en": ["the runes say wait a little and stay calm. The right moment is coming very soon.",
               "the runes say be brave in one small way today. One honest step opens the door."],
        "hi": ["रून कहते हैं थोड़ा रुको और शांत रहो। सही समय बहुत जल्द आ रहा है।",
               "रून कहते हैं आज एक छोटी हिम्मत दिखाओ। एक सच्चा कदम रास्ता खोलता है।"],
        "hng": ["runes kehte hain thoda ruko aur calm raho. Sahi time bahut jald aa raha hai.",
                "runes kehte hain aaj ek chhoti himmat dikhao. Ek sachcha step darwaza kholta hai."]},
    "crystals": {
        "en": ["hold a calm stone in your mind. Breathe slow. When you feel calm, the answer feels clear.",
               "picture a bright crystal. Put your worry into it, take a breath, and let the worry go."],
        "hi": ["मन में एक शांत पत्थर सोचो। धीरे साँस लो। शांत होते ही उत्तर साफ़ लगेगा।",
               "एक चमकीला क्रिस्टल सोचो। चिंता उसमें डालो, साँस लो और छोड़ दो।"],
        "hng": ["mann mein ek calm stone socho. Dheere saans lo. Calm hote hi jawab clear lagega.",
                "ek bright crystal socho. Worry usme daalo, saans lo aur chhod do."]},
    "aura": {
        "en": ["your energy is a little tired. Rest, drink water, and take slow breaths. You'll feel brighter soon.",
               "your energy shines when you relax. Let go of one heavy thought and you'll feel lighter."],
        "hi": ["तुम्हारी ऊर्जा थोड़ी थकी है। आराम करो, पानी पिओ, धीरे साँस लो। जल्द अच्छा लगेगा।",
               "जब तुम आराम करते हो तो ऊर्जा चमकती है। एक भारी विचार छोड़ो, हल्का लगेगा।"],
        "hng": ["tumhari energy thodi thaki hai. Rest karo, paani pio, dheere saans lo. Jald accha lagega.",
                "jab tum relax karte ho energy chamakti hai. Ek heavy thought chhodo, halka lagega."]},
    "palmistry": {
        "en": ["your hand shows you are strong. The lines are hints, not rules — your choices matter most.",
               "your hand says your heart is kind. Follow that kindness and good things follow you."],
        "hi": ["तुम्हारा हाथ कहता है तुम मज़बूत हो। रेखाएँ इशारा हैं, नियम नहीं — तुम्हारे चुनाव सबसे ज़रूरी।",
               "तुम्हारा हाथ कहता है तुम्हारा दिल अच्छा है। उसी अच्छाई पर चलो।"],
        "hng": ["tumhara haath kehta hai tum strong ho. Lines hints hain, rules nahi — tumhare choices sabse zaroori.",
                "tumhara haath kehta hai tumhara dil accha hai. Usi kindness par chalo."]},
    "feng-shui": {
        "en": ["tidy one small corner of your room today. A clear space makes a clear mind.",
               "let fresh air and light in. When your space feels good, your day feels good."],
        "hi": ["आज कमरे का एक कोना साफ़ करो। साफ़ जगह से मन भी साफ़।",
               "ताज़ी हवा और रोशनी आने दो। जगह अच्छी तो दिन अच्छा।"],
        "hng": ["aaj room ka ek corner saaf karo. Saaf jagah se mann bhi saaf.",
                "fresh air aur light aane do. Jagah acchi to din accha."]},
    "kabbalah": {
        "en": ["big idea made simple: balance kindness with rules. Be gentle, but also be fair to yourself.",
               "as inside, so outside — keep your heart calm and your day will feel calmer too."],
        "hi": ["सरल बात: दया और नियम में संतुलन रखो। खुद के साथ नरम पर सही रहो।",
               "जैसा भीतर, वैसा बाहर — दिल शांत रखो, दिन भी शांत लगेगा।"],
        "hng": ["simple baat: kindness aur rules mein balance rakho. Khud ke saath naram par fair raho.",
                "jaisa andar, waisa bahar — dil calm rakho, din bhi calm lagega."]},
    "i-ching": {
        "en": ["things are changing. Go with the change slowly, don't fight it, and it gets easier.",
               "pause before you act. A short wait now saves trouble later."],
        "hi": ["चीज़ें बदल रही हैं। बदलाव के साथ धीरे चलो, लड़ो मत, आसान हो जाएगा।",
               "करने से पहले रुको। थोड़ा इंतज़ार अभी, परेशानी बाद में बचाता है।"],
        "hng": ["cheezein badal rahi hain. Change ke saath dheere chalo, lado mat, aasan ho jayega.",
                "karne se pehle ruko. Thoda wait ab, tension baad mein bachata hai."]},
    "relationships": {
        "en": ["talk kindly and listen more. Say how you feel in simple words, and things get better.",
               "love grows with small kind acts. Do one nice thing today without expecting anything back."],
        "hi": ["प्यार से बात करो और ज़्यादा सुनो। सरल शब्दों में भावना कहो, सब ठीक होगा।",
               "प्यार छोटे अच्छे कामों से बढ़ता है। आज बिना उम्मीद एक अच्छा काम करो।"],
        "hng": ["pyaar se baat karo aur zyada suno. Simple words mein feeling bolo, sab better ho jayega.",
                "pyaar chhote acche kaamon se badhta hai. Aaj bina expect kiye ek accha kaam karo."]},
    "career": {
        "en": ["you're on the right track. Do one useful task today and keep going — small steps win.",
               "pick the work goal that feels true. Work on it a little each day and people will notice."],
        "hi": ["तुम सही रास्ते पर हो। आज एक उपयोगी काम करो और चलते रहो — छोटे कदम जीतते हैं।",
               "जो लक्ष्य सच्चा लगे उसे चुनो। रोज़ थोड़ा करो, लोग ध्यान देंगे।"],
        "hng": ["tum sahi track par ho. Aaj ek useful kaam karo aur chalte raho — chhote steps jeette hain.",
                "jo goal sachcha lage use chuno. Roz thoda karo, log notice karenge."]},
    "money": {
        "en": ["keep money simple: spend a little less, save a little more. Small habits add up.",
               "don't rush money choices. Wait, think for a day, then decide with a calm mind."],
        "hi": ["पैसा सरल रखो: थोड़ा कम खर्च, थोड़ा ज़्यादा बचत। छोटी आदतें बड़ी बनती हैं।",
               "पैसे के फैसले जल्दी मत करो। एक दिन सोचो, फिर शांत मन से तय करो।"],
        "hng": ["paisa simple rakho: thoda kam kharch, thoda zyada save. Chhoti habits badi banti hain.",
                "paise ke decisions jaldi mat karo. Ek din socho, phir calm mann se decide karo."]},
    "health": {
        "en": ["rest, water, and slow breaths help a lot. Be gentle with your body today. For real problems, see a doctor.",
               "small healthy steps beat big ones. Sleep well tonight and move a little tomorrow."],
        "hi": ["आराम, पानी और धीमी साँस बहुत मदद करते हैं। शरीर के साथ नरम रहो। असली दिक्कत हो तो डॉक्टर से मिलो।",
               "छोटे स्वस्थ कदम बड़े से बेहतर। आज अच्छी नींद लो, कल थोड़ा चलो।"],
        "hng": ["rest, paani aur dheemi saans bahut help karte hain. Body ke saath naram raho. Asli problem ho to doctor se milo.",
                "chhote healthy steps bade se behtar. Aaj acchi neend lo, kal thoda chalo."]},
    "purpose": {
        "en": ["your purpose is found by doing, not just thinking. Try one thing you love this week.",
               "you matter. Follow what makes you feel alive, one small step at a time."],
        "hi": ["उद्देश्य करने से मिलता है, सिर्फ सोचने से नहीं। इस हफ्ते एक पसंद की चीज़ करो।",
               "तुम महत्वपूर्ण हो। जो जीवंत महसूस कराए उसे एक छोटे कदम से अपनाओ।"],
        "hng": ["purpose karne se milta hai, sirf sochne se nahi. Is hafte ek pasand ki cheez karo.",
                "tum important ho. Jo alive feel karaye use ek chhote step se apnao."]},
    "timing": {
        "en": ["not yet — but soon. Keep getting ready, and the right time will come.",
               "good things need a little patience. Stay calm and keep going; timing is on your side."],
        "hi": ["अभी नहीं — पर जल्द। तैयारी करते रहो, सही समय आएगा।",
               "अच्छी चीज़ों को थोड़ा धैर्य चाहिए। शांत रहो और चलते रहो; समय तुम्हारे साथ है।"],
        "hng": ["abhi nahi — par jald. Ready rehte raho, sahi time aayega.",
                "acchi cheezon ko thoda patience chahiye. Calm raho aur chalte raho; timing tumhare saath hai."]},
}
for _tk, _val in ELI5.items():
    PACK[_tk] = _val

# Topics considered on-theme (occult sciences A-Z + aura + mindfulness). "general" is never surfaced.
DEFAULT_TOPICS = ["aura", "mindfulness"]


def detect_topics(question: str) -> list[str]:
    t = (question or "").lower()
    found: list[str] = []
    for topic, words in METHOD_KEYWORDS.items():
        if any(w in t for w in words):
            found.append(topic)
    for topic, words in LIFE_KEYWORDS.items():
        if any(w in t for w in words):
            found.append(topic)
    if not found:
        found.append("general")
    return found


def _pick_opening(lang: str) -> str:
    return random.choice(OPENINGS.get(lang, OPENINGS["en"]))


def compose_answer(question: str, lang: str, extra_by_topic: dict | None = None, user_id: str = None) -> dict:
    """Return the verified final answer built strictly from the knowledge pack
    (plus any owner-added answers passed in ``extra_by_topic``).

    Answers stay within occult sciences (A-Z), aura, and mindfulness. A question
    that matches no specific tradition is grounded in the aura/mindfulness pool —
    never a generic reply.
    """
    if lang not in LANGS:
        lang = "en"
    extra_by_topic = extra_by_topic or {}
    topics = detect_topics(question)

    if "daily" in topics:
        import datetime
        seed = f"{user_id or 'anon'}:{datetime.datetime.now(datetime.timezone.utc).date()}:{lang}"
        ans = daily_reading(seed, lang)
        return {"answer": f"{_pick_opening(lang)}{ans}", "topics": topics, "primary": "daily"}

    if topics == ["general"] or "general" in topics:
        topics = [t for t in topics if t != "general"] or list(DEFAULT_TOPICS)
    primary = topics[0]

    pool: list[str] = []
    for tp in topics:
        pack = PACK.get(tp)
        if pack:
            pool.extend(pack.get(lang) or pack.get("en") or [])
        # owner-added answers for this topic + language
        pool.extend(extra_by_topic.get(tp, []))
    if not pool:
        pool = (MINDFULNESS.get(lang) or MINDFULNESS["en"])[:]

    body = random.choice(pool)
    answer = f"{_pick_opening(lang)}{body}"
    return {"answer": answer.strip(), "topics": topics, "primary": primary}


def daily_reading(seed: str, lang: str) -> str:
    """A short, deterministic aura + mindfulness reading for the day (stable per seed)."""
    if lang not in LANGS:
        lang = "en"
    pool = (PACK["aura"].get(lang) or PACK["aura"]["en"]) + (MINDFULNESS.get(lang) or MINDFULNESS["en"])
    rng = random.Random(seed)
    return rng.choice(pool).strip()


def clean_for_tts(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"[*_#>~|]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
