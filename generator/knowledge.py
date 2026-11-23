"""
Traditional (Jyotish / Muhurta) lookup tables and rules used for the guidance text.

These encode commonly cited rules. Lineages differ on details, so treat the output
as traditional guidance, not prediction. Edit freely: the weights in SCORE are the
only "opinion" in the scoring, everything else is a table.
"""

# ---- planets, days, horas -------------------------------------------------
CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]   # hora order
DAY_LORD = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]   # Python weekday(): Mon=0
VARA = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
VARA_SANSKRIT = ["Somavara", "Mangalavara", "Budhavara", "Guruvara", "Shukravara", "Shanivara", "Ravivara"]
GLYPH = {"Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿", "Jupiter": "♃",
         "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"}
SANSKRIT = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangala", "Mercury": "Budha",
            "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"}

# Which eighth of the daytime (1..8) is Rahu Kaal / Yamaganda / Gulika, by Python weekday (Mon=0)
RAHU_PART = [2, 7, 5, 6, 4, 3, 8]
YAMA_PART = [4, 3, 2, 1, 7, 6, 5]
GULIKA_PART = [6, 5, 4, 3, 2, 1, 7]

# Day flavour: deity, colours, theme (traditional associations)
VARA_INFO = {
    "Sun": {"deity": "Surya", "colors": "red, orange, gold", "theme": "vitality, authority and clarity"},
    "Moon": {"deity": "Shiva / Chandra", "colors": "white, silver", "theme": "emotions, home and nourishment"},
    "Mars": {"deity": "Hanuman / Kartikeya", "colors": "red", "theme": "energy, courage and decisive action (watch for friction)"},
    "Mercury": {"deity": "Vishnu / Ganesha", "colors": "green", "theme": "communication, learning and trade"},
    "Jupiter": {"deity": "Brihaspati / Vishnu", "colors": "yellow", "theme": "wisdom, guidance and growth"},
    "Venus": {"deity": "Lakshmi / Devi", "colors": "white, pastels", "theme": "harmony, relationships, art and comfort"},
    "Saturn": {"deity": "Shani / Hanuman", "colors": "black, dark blue", "theme": "discipline, service and patience"},
}

# What each hora is traditionally good for / best avoided for
HORA = {
    "Sun": {"nature": "authority, vitality and visibility", "base": 0,
            "best": ["dealing with officials, government or seniors", "leadership tasks and visible decisions", "health routines and exercise"],
            "avoid": ["ego clashes and power struggles", "rushing into confrontation"]},
    "Moon": {"nature": "nurture, intuition and the public", "base": 1,
             "best": ["home, family and caring for others", "travel and public-facing work", "creative or intuitive work"],
             "avoid": ["big decisions made on a passing mood", "overthinking"]},
    "Mars": {"nature": "drive, courage and competition", "base": -1,
             "best": ["physical effort, sport and competition", "repairs, machinery and construction", "bold, decisive action"],
             "avoid": ["negotiations and signing agreements", "arguments and impulsive spending"]},
    "Mercury": {"nature": "communication, learning and commerce", "base": 1,
                "best": ["writing, calls and messages", "study, exams and learning", "trade, accounts and contracts"],
                "avoid": ["careless speech", "over-committing"]},
    "Jupiter": {"nature": "wisdom, growth and guidance", "base": 2,
                "best": ["learning, teaching and spiritual practice", "finance, planning and advisory or legal matters", "new beginnings and asking for guidance"],
                "avoid": ["over-promising", "overindulgence"]},
    "Venus": {"nature": "harmony, beauty and relationships", "base": 2,
              "best": ["relationships, romance and social time", "art, music and comfort", "buying vehicles, clothes or luxuries"],
              "avoid": ["overspending", "heavy conflict talks"]},
    "Saturn": {"nature": "discipline, structure and patience", "base": -1,
               "best": ["steady routine work needing patience", "organising, cleaning and long-term planning", "service, elders and manual labour"],
               "avoid": ["celebrations and flashy new ventures", "shortcuts and rushing"]},
}

# Natural planetary friendship (Parashara). Rahu/Ketu are treated as neutral here.
FRIENDS = {
    "Sun": {"friends": {"Moon", "Mars", "Jupiter"}, "enemies": {"Venus", "Saturn"}},
    "Moon": {"friends": {"Sun", "Mercury"}, "enemies": set()},
    "Mars": {"friends": {"Sun", "Moon", "Jupiter"}, "enemies": {"Mercury"}},
    "Mercury": {"friends": {"Sun", "Venus"}, "enemies": {"Moon"}},
    "Jupiter": {"friends": {"Sun", "Moon", "Mars"}, "enemies": {"Mercury", "Venus"}},
    "Venus": {"friends": {"Mercury", "Saturn"}, "enemies": {"Sun", "Moon"}},
    "Saturn": {"friends": {"Mercury", "Venus"}, "enemies": {"Sun", "Moon", "Mars"}},
}

LORD_THEME = {
    "Ketu": "detachment, insight and endings",
    "Venus": "pleasure, relationships and creativity",
    "Sun": "confidence, purpose and authority",
    "Moon": "nurture, feeling and receptivity",
    "Mars": "drive, courage and friction",
    "Rahu": "ambition, restlessness and the unconventional",
    "Jupiter": "growth, wisdom and guidance",
    "Saturn": "discipline, patience and structure",
    "Mercury": "intellect, speech and commerce",
}

# ---- nakshatras: (name, Vimshottari lord, muhurta group) ------------------
NAKSHATRAS = [
    ("Ashwini", "Ketu", "Kshipra"), ("Bharani", "Venus", "Ugra"), ("Krittika", "Sun", "Mishra"),
    ("Rohini", "Moon", "Dhruva"), ("Mrigashira", "Mars", "Mridu"), ("Ardra", "Rahu", "Tikshna"),
    ("Punarvasu", "Jupiter", "Chara"), ("Pushya", "Saturn", "Kshipra"), ("Ashlesha", "Mercury", "Tikshna"),
    ("Magha", "Ketu", "Ugra"), ("Purva Phalguni", "Venus", "Ugra"), ("Uttara Phalguni", "Sun", "Dhruva"),
    ("Hasta", "Moon", "Kshipra"), ("Chitra", "Mars", "Mridu"), ("Swati", "Rahu", "Chara"),
    ("Vishakha", "Jupiter", "Mishra"), ("Anuradha", "Saturn", "Mridu"), ("Jyeshtha", "Mercury", "Tikshna"),
    ("Mula", "Ketu", "Tikshna"), ("Purva Ashadha", "Venus", "Ugra"), ("Uttara Ashadha", "Sun", "Dhruva"),
    ("Shravana", "Moon", "Chara"), ("Dhanishta", "Mars", "Chara"), ("Shatabhisha", "Rahu", "Chara"),
    ("Purva Bhadrapada", "Jupiter", "Ugra"), ("Uttara Bhadrapada", "Saturn", "Dhruva"), ("Revati", "Mercury", "Mridu"),
]

NAK_GROUP = {
    "Dhruva": {"label": "fixed", "delta": 1,
               "do": "foundations, commitments and long-term work",
               "text": "steady and lasting — good for foundations, commitments and long-term work"},
    "Chara": {"label": "movable", "delta": 1,
               "do": "travel, errands, vehicles and change",
              "text": "mobile and changeable — good for travel, errands, vehicles and change"},
    "Kshipra": {"label": "swift", "delta": 1,
               "do": "fresh starts, trade, learning and skill work",
                "text": "quick and light — good for fresh starts, trade, learning and skill work"},
    "Mridu": {"label": "soft", "delta": 1,
               "do": "the arts, friendships, romance and joyful occasions",
              "text": "gentle and friendly — good for the arts, friendships, romance and joyful occasions"},
    "Mishra": {"label": "mixed", "delta": 0,
               "do": "routine tasks",
               "text": "mixed results — fine for routine tasks, less so for important beginnings"},
    "Ugra": {"label": "fierce", "delta": -1,
               "do": "bold effort and, if needed, confrontation",
             "text": "intense — suits confrontation and bold effort, not gentle or auspicious starts"},
    "Tikshna": {"label": "sharp", "delta": -1,
               "do": "clearing out, cutting away and deep research",
                "text": "sharp — suits clearing, cutting away or deep research, not new ventures"},
}

# ---- tithi -----------------------------------------------------------------
TITHI_NAMES = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
               "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
TITHI_CATEGORY = ["Nanda", "Bhadra", "Jaya", "Rikta", "Purna"]
TITHI_CAT_INFO = {
    "Nanda": {"delta": 0, "do": "celebrations, the arts and enjoyable projects",
              "text": "joyful — celebrations, arts and enjoyable projects"},
    "Bhadra": {"delta": 0, "do": "health, daily life, ceremonies and steady work",
               "text": "supportive — health, daily life, ceremonies and steady work"},
    "Jaya": {"delta": 0, "do": "competition, negotiation, legal matters and study",
             "text": "victory — competition, negotiation, legal matters and study"},
    "Rikta": {"delta": -1, "do": "clearing, finishing and solitary work",
              "text": "empty — poor for auspicious beginnings, good for clearing, finishing and solitary work"},
    "Purna": {"delta": 1, "do": "completion, worship and auspicious beginnings",
              "text": "full — completion, worship and auspicious beginnings"},
}


def tithi_info(idx: int):
    """idx 0..29 -> dict(n, name, paksha, category)"""
    n = idx + 1
    paksha = "Shukla" if n <= 15 else "Krishna"
    k = (n - 1) % 15
    if n == 15:
        name = "Purnima"
    elif n == 30:
        name = "Amavasya"
    else:
        name = TITHI_NAMES[k]
    cat = TITHI_CATEGORY[k % 5]
    return {"n": n, "name": name, "paksha": paksha, "category": cat}


# ---- yoga ------------------------------------------------------------------
YOGA_NAMES = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti",
              "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata",
              "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra",
              "Vaidhriti"]
YOGA_CHALLENGING = {"Vishkambha", "Atiganda", "Shula", "Ganda", "Vyaghata", "Vajra", "Vyatipata",
                    "Parigha", "Vaidhriti"}

# ---- karana ----------------------------------------------------------------
MOVABLE_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]


def karana_name(idx: int) -> str:
    """idx 0..59 over the lunar month (half-tithis)."""
    if idx == 0:
        return "Kimstughna"
    if idx >= 57:
        return ["Shakuni", "Chatushpada", "Naga"][idx - 57]
    return MOVABLE_KARANAS[(idx - 1) % 7]


# ---- rashi -----------------------------------------------------------------
RASHI = [("Mesha", "Aries"), ("Vrishabha", "Taurus"), ("Mithuna", "Gemini"), ("Karka", "Cancer"),
         ("Simha", "Leo"), ("Kanya", "Virgo"), ("Tula", "Libra"), ("Vrishchika", "Scorpio"),
         ("Dhanu", "Sagittarius"), ("Makara", "Capricorn"), ("Kumbha", "Aquarius"), ("Meena", "Pisces")]

# ---- personal: Tarabala / Chandrabala (optional) ---------------------------
TARA_NAMES = {1: "Janma", 2: "Sampat", 3: "Vipat", 4: "Kshema", 5: "Pratyari",
              6: "Sadhaka", 7: "Vadha", 8: "Mitra", 9: "Parama Mitra"}
TARA_BAD = {3, 5, 7}
CHANDRA_GOOD_HOUSES = {1, 3, 6, 7, 10, 11}

# ---- scoring weights (the only opinionated part; tweak to taste) ------------
SCORE = {
    "rahu_kaal": -2, "yamaganda": -1, "gulika": -1,
    "abhijit": 2,
    "vishti": -2, "yoga_challenging": -1, "amavasya": -1,
    "lord_friend": 1, "lord_enemy": -1,
    "tara_good": 1, "tara_bad": -1, "chandra_good": 1, "chandra_bad": -1,
    "waxing_moon_hora": 1,
}


def rating_for(score: int) -> str:
    if score >= 3:
        return "Favorable"
    if score >= 1:
        return "Good"
    if score == 0:
        return "Neutral"
    if score >= -2:
        return "Caution"
    return "Avoid"


def find_nakshatra(name: str):
    """Index of a nakshatra by (case-insensitive) name, or None."""
    if not name:
        return None
    key = name.strip().lower().replace("-", " ")
    for i, (nm, _, _) in enumerate(NAKSHATRAS):
        if nm.lower() == key:
            return i
    return None


def find_rashi(name: str):
    if not name:
        return None
    key = name.strip().lower()
    for i, (sa, en) in enumerate(RASHI):
        if key in (sa.lower(), en.lower()):
            return i
    return None
