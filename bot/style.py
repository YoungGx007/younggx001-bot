TEXT_STYLE_TEMPLATES = {
    "english": [
        "I'm a bit busy rn.", "Just chilling.", "Yeah, I get it.",
        "Sounds good to me.", "Not sure tbh.", "I'll check on that.",
    ],
    "swahili": [
        "Niko busy kidogo.", "Niko tu hapa.", "Ndiyo, nimeelewa.",
        "Inasikika vizuri.", "Sijui vizuri.", "Nitaangalia hiyo.",
    ],
    "sheng": [
        "Niko tied kidogo.", "Niko tu hapa msee.", "Ite, nimeelewa.",
        "Inasound poa.", "Sijui boss.", "Nitacheck hiyo.",
    ],
}

_SHENG_WORDS = {"msee", "boss", "ite", "areh", "niaje", "fresh", "uside", "tunakuja"}
_SWAHILI_WORDS = {"sasa", "habari", "ndiyo", "tafadhali", "kwaheri", "asante",
                  "karibu", "uko", "unaendeleaje", "hujambo", "poa", "niko", "sawa"}


def detect_language(text: str) -> str:
    words = set(text.lower().split())
    sheng_hits = len(words & _SHENG_WORDS)
    swahili_hits = len(words & _SWAHILI_WORDS)
    if sheng_hits > swahili_hits:
        return "sheng"
    if swahili_hits > 0:
        return "swahili"
    return "english"


def style_like_me(text: str, language: str = "english") -> str:
    if language != "english":
        return text
    replacements = [
        ("you are", "u r"), ("you", "u"), ("are", "r"),
        ("right now", "rn"), ("because", "cuz"), ("going to", "gonna"),
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def bilingual_reply(english: str, swahili: str) -> str:
    return f"{english}\n{swahili}"
