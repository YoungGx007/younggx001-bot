import os
import random
from flask import request
from twilio.twiml.messaging_response import MessagingResponse
from .style import detect_language, style_like_me, bilingual_reply, TEXT_STYLE_TEMPLATES

BOT_MODE = os.getenv("BOT_MODE", "online").lower()
conversation_history = {}
USE_BILINGUAL = os.getenv("USE_BILINGUAL", "true").lower() == "true"


def detect_topic(text: str) -> str:
    keywords = {
        "plans": ["plan", "tomorrow", "weekend", "movie", "game", "hang"],
        "feelings": ["how are", "how u", "u doing", "feeling", "mood"],
        "food": ["eat", "food", "hungry", "dinner", "lunch"],
        "wifi": ["wifi", "internet", "signal", "connection"],
    }
    for topic, terms in keywords.items():
        for term in terms:
            if term in text:
                return topic
    return "chat"


def continue_conversation(incoming_text: str, sender: str) -> str:
    incoming = incoming_text.strip()
    if not incoming:
        return style_like_me("Hey! I'm here, what's up?", "english")

    incoming_lower = incoming.lower()
    language = detect_language(incoming_lower)
    topic = detect_topic(incoming_lower)
    conversation_history.setdefault(sender, {})["topic"] = topic
    conversation_history.setdefault(sender, {})["language"] = language

    if any(greet in incoming_lower for greet in ["hello", "hi", "hey", "yo", "hujambo", "sasa"]):
        if language == "swahili":
            return style_like_me(random.choice(["Hujambo! Unaendeleaje?", "Mambo! Uko poa?", "Sasa, uko aje?", "Habari yako? (How are you?)", "Karibu! Uko poa?", "Hey! Hujambo, what's up?" ]), language)
        if language == "sheng":
            return style_like_me(random.choice(["Sasa msee, uko aje?", "Mambo, uko poa?", "Yo, nini cha news?", "Hey msee, uko fresh?", "Sawa boss, nini story?", "Yo! Sasa, what's good?" ]), language)
        return style_like_me(random.choice(["Hey! what's up?", "Yo! what are u doing?", "Hey there, u good?" ]), language)

    if any(word in incoming_lower for word in ["how are", "how's", "how r", "u doing", "doing", "unaendeleaje", "uko aje"]):
        if language == "swahili":
            return style_like_me(random.choice(["Niko poa, wewe je?", "Salama, weweje?", "Niko fine, unaendeleaje?", "I'm good, niko poa! Wewe?", "All good, salama sana!" ]), language)
        if language == "sheng":
            return style_like_me(random.choice(["Niko poa msee, wewe je?", "Sawa boss, uko aje?", "Niko fresh, na wewe?", "I'm fresh, niko poa! Uko?", "All good, sawa kabisa!" ]), language)
        return style_like_me(random.choice(["I'm good, u?", "Doing pretty good, u?", "All good here, u?" ]), language)

    if "lol" in incoming_lower or "haha" in incoming_lower:
        if language == "swahili":
            return style_like_me(random.choice(["Haha, kweli!", "Kuwa na poa hiyo.", "Nafurahi unacheka.", "That's funny! Haha, kweli!", "Lol, kuwa na poa sana!" ]) + " Una kitu kingine?", language)
        if language == "sheng":
            return style_like_me(random.choice(["Areh, hiyo ni poa.", "Lol, hii ni msee.", "Hio ni funny sana.", "That's wild! Areh, poa!", "Haha, sawa kabisa!" ]) + " Nini tena?", language)
        return style_like_me(random.choice(["Haha, same.", "Lol, that's funny.", "For real, that's wild."]) + " What else?", language)

    if "?" in incoming or any(word in incoming_lower for word in ["what", "why", "when", "where", "who", "how", "which", "kwanini", "nini", "wapi", "lini"]):
        if language == "swahili":
            follow = random.choice(["Unadhani?", "Tuweze?", "Je, ni sawa?", "Tupange kwa lini?", "What do u think?"])
            return style_like_me(random.choice(["Ndiyo, ni sawa.", "Inaonekana vizuri.", "Nadhani tutakuliza.", "Yeah, it's good!", "All good!"]) + " " + follow, language)
        if language == "sheng":
            follow = random.choice(["Uside?", "Tupige plan?", "Sawa sawa?", "Tuendelee?", "What do u think?"])
            return style_like_me(random.choice(["Ite, iko poa.", "Kwa kweli, inaendana.", "Tufanye hivyo.", "Yeah, sounds good!", "All good!"]) + " " + follow, language)
        follow = random.choice(["What do u think?", "Should we do it?", "Sound good?", "Wanna keep going?"])
        return style_like_me(random.choice(["Yeah, totally.", "For sure.", "I think so."]) + " " + follow, language)

    if topic == "plans":
        if language == "swahili":
            return style_like_me(random.choice(["Poa, tuchague siku.", "Inaweza kuwa nzuri.", "Niko tayari kwa hiyo.", "Sounds good! Poa sana.", "Yeah, let's do it!"]) + " Tunaweza kupanga nini?", language)
        if language == "sheng":
            return style_like_me(random.choice(["Sawa, tupi plan.", "That inaweza kuwa poa.", "Niko down kwa hiyo.", "Sounds fun! Sawa.", "Yeah, I'm down!"]) + " Umefikiria nini?", language)
        return style_like_me(random.choice(["Sounds good, let's do that.", "That could be fun.", "I'm down for that."]) + " What do u wanna plan?", language)

    if topic == "wifi":
        if language == "swahili":
            return style_like_me(random.choice(["Wifi ina matatizo sasa.", "Kwa upande wangu iko sawa.", "Nikiwa wifi nitaangalia.", "Wifi is acting up! Ina matatizo.", "All good here!"]) + " Umeona bado?", language)
        if language == "sheng":
            return style_like_me(random.choice(["Wifi ipo low key.", "Kwa side yangu iko poa.", "Nikiwa kwa wifi nina check.", "Wifi is bad! Low key.", "Fine on my end!"]) + " Ebu sema?", language)
        return style_like_me(random.choice(["Yeah, wifi is acting up.", "It's fine on my end.", "If I'm on wifi I can check it."]) + " U see it yet?", language)

    if topic == "food":
        if language == "swahili":
            return style_like_me(random.choice(["Nataka kitu kitamu.", "Chakula inasikika poa.", "Tafadhali tuje kwa chakula nzuri.", "I'm hungry! Nataka kitu.", "Sounds tasty!"]) + " Unataka nini?", language)
        if language == "sheng":
            return style_like_me(random.choice(["Nataka kitu fresh.", "Chakula iko sawa.", "Tuchomee kitu.", "I'm craving! Nataka fresh.", "Let's eat!"]) + " Umeshafikiri?", language)
        return style_like_me(random.choice(["I'm craving something good.", "Food sounds great.", "Let's get something tasty."]) + " What do u want?", language)

    if language == "swahili":
        return style_like_me(random.choice(["Endelea.", "Niambie zaidi.", "Nini kinachofuata?", "Keep going!", "Tell me more!"]), language)
    if language == "sheng":
        return style_like_me(random.choice(["Endelea msee.", "Nipe story.", "Nini next?", "Keep it coming!", "What's next?"]), language)
    return style_like_me(random.choice(["Yup, keep going.", "Tell me more.", "What's next?" ]), language)


def auto_reply(incoming_text: str) -> str:
    language = detect_language(incoming_text.lower())
    base = random.choice(TEXT_STYLE_TEMPLATES[language])
    if language == "english" and "sorry" not in base.lower() and random.random() < 0.4:
        base = base.replace("I'm", "Sorry, I'm")
    return style_like_me(base + " " + random.choice([
        "What else is up?", "Tell me more.", "Keep it coming." ]), language)


def generate_reply(sender: str, incoming_text: str) -> str:
    if BOT_MODE == "offline":
        return auto_reply(incoming_text)
    
    language = detect_language(incoming_text.lower())
    response = continue_conversation(incoming_text, sender)
    
    # Add bilingual replies for Kiswahili when enabled
    if USE_BILINGUAL and language == "swahili":
        # Generate both English and Swahili versions
        en_msg = random.choice(["Got it!", "I see!", "Understood!", "All good!", "Thanks!"])
        sw_msg = response
        return bilingual_reply(en_msg, sw_msg.split("\n")[0] if "\n" in sw_msg else sw_msg)
    
    return response


def setup_routes(app):
    @app.route("/whatsapp", methods=["POST"])
    def reply():
        msg = request.values.get("Body", "")
        sender = request.values.get("From", "unknown")

        resp = MessagingResponse()
        resp.message(generate_reply(sender, msg))
        return str(resp)
