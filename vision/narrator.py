"""The voice: turns a detection result into one short sentence to say out loud."""
import json
import re
import time
import urllib.request
from collections import Counter

from . import config

PLURALS = {"person": "people", "mouse": "mice", "knife": "knives", "sheep": "sheep",
           "skis": "skis", "scissors": "scissors", "wine glass": "wine glasses"}
NUMBERS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def plural(word, n):
    if n == 1:
        return word
    if word in PLURALS:
        return PLURALS[word]
    if word.endswith(("s", "sh", "ch", "x")):
        return word + "es"
    return word + "s"


def a_or_an(word):
    return ("an " if word[0] in "aeiou" else "a ") + word


def join_words(items):
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def describe(result):
    """{"objects": [...], "faces": [...]} -> "I see two people and a cup. One person is smiling." """
    counts = Counter(o["label"] for o in result["objects"])
    if not counts and not result["faces"]:
        return "I don't see anything I recognize."

    parts = []
    for label, n in counts.most_common(4):          # the 4 most common things is plenty to say
        parts.append(a_or_an(label) if n == 1 else f"{NUMBERS[min(n, 9)]} {plural(label, n)}")
    sentence = f"I see {join_words(parts)}." if parts else "I see a face."

    moods = Counter(f["expression"] for f in result["faces"]
                    if f["expression"] and f["expression"] != "neutral")
    for mood, n in moods.most_common(2):
        who = "Someone is" if n == 1 else f"{NUMBERS[min(n, 9)].capitalize()} people are"
        mood_text = {"mouth open": "open-mouthed", "eyes closed": "closing their eyes"}.get(mood, mood)
        sentence += f" {who} {mood_text}."
    return sentence


class Narrator:
    """Decides *when* to speak, so the phone doesn't repeat itself every second."""

    def __init__(self, use_llm=False):
        self.use_llm = use_llm
        self.last_key = None
        self.last_time = 0.0
        self.last_text = ""

    def update(self, result):
        """Returns (text, should_speak)."""
        key = (tuple(sorted(Counter(o["label"] for o in result["objects"]).items())),
               tuple(sorted(f["expression"] or "" for f in result["faces"])))
        now = time.time()
        changed = key != self.last_key
        if not changed and now - self.last_time < config.REPEAT_AFTER_S:
            return self.last_text, False

        text = describe(result)
        if self.use_llm and (result["objects"] or result["faces"]):
            text = rephrase_with_llm(text, result) or text
        self.last_key, self.last_time, self.last_text = key, now, text
        return text, True


def rephrase_with_llm(plain_sentence, result):
    """Optional: ask a language model (e.g. on your Oracle node) to narrate with personality.
    Returns None on any problem, so the plain sentence is used instead."""
    prompt = (
        "You are the voice of an old Nokia phone camera that is learning to see. "
        "In ONE short sentence (max 20 words, plain ASCII, no emoji), say what you see. "
        f"Facts: {plain_sentence} Raw detections: "
        + json.dumps({"objects": [o["label"] for o in result["objects"]],
                      "faces": [f["expression"] for f in result["faces"]]})
    )
    body = json.dumps({"model": config.LLM_MODEL,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(config.LLM_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer local"})
    try:
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT_S) as r:
            text = json.loads(r.read())["choices"][0]["message"]["content"]
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()  # drop "thinking" text
        return text.encode("ascii", "ignore").decode().replace("\n", " ")[:160] or None
    except Exception as e:
        print(f"[narrator] LLM unavailable ({e}); using the plain sentence.")
        return None
