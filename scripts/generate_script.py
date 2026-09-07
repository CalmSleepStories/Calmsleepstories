"""
Picks the next 'pending' topic from content_plan.json, asks Gemini to write a
slow, calm, long-form sleep-story script, and saves it + metadata for the
rest of the pipeline. Also marks the topic 'done' and appends to history so
the same story is never generated twice.
"""

import os
import json
import re
from datetime import datetime, timezone

import google.generativeai as genai

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_PATH = os.path.join(ROOT, "content_plan.json")
OUT_DIR = os.path.join(ROOT, "output")
VIDEO_MINUTES = int(os.environ.get("VIDEO_MINUTES", "20"))

# Roughly 130 spoken words per minute at a slow, sleep-story pace.
WORDS_PER_MINUTE = 130
TARGET_WORDS = VIDEO_MINUTES * WORDS_PER_MINUTE

# Rotating narrative angles so every video isn't structurally identical
# (same POV, same opening, same pacing pattern every single time). This is
# picked deterministically from how many stories have been made so far,
# so it cycles through all of them and each run is reproducible.
STYLE_VARIANTS = [
    "Second person ('you'), starting with arriving somewhere and settling in slowly.",
    "Gentle third person following one quiet character, starting mid-routine, already at ease.",
    "Second person, starting with a small sensory detail (a sound or smell) before revealing the place.",
    "Gentle third person, structured as a slow walk from one quiet spot to another over time.",
    "Second person, framed as memory being recalled slowly, unhurried, half-dreaming.",
]

SYSTEM_PROMPT_TEMPLATE = """You are writing a long-form bedtime sleep story script, meant to be read aloud
slowly in a soft, calm voice for adults who want to relax and fall asleep.

Narrative approach for this story specifically: {style}

Rules:
- Very slow pacing, present tense.
- No jump scares, conflict, tension, or cliffhangers. Nothing exciting should happen.
- Long, unhurried descriptive passages: sounds, textures, light, temperature, small repetitive actions.
- Short, simple sentences. Frequent natural pauses (write them as separate short paragraphs).
- Do not use chapter headings, slide numbers, bullet points, or any formatting.
- Do not include stage directions like "[pause]" or sound effect notes.
- Output ONLY the narration text the narrator will read aloud, nothing else.
- Target length: approximately {target_words} words (this is a {video_minutes}-minute story).
"""


def pick_style_variant(history_count: int) -> str:
    return STYLE_VARIANTS[history_count % len(STYLE_VARIANTS)]


def load_plan():
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_plan(plan):
    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)


def pick_topic(plan):
    for topic in plan["topics"]:
        if topic["status"] == "pending":
            return topic
    raise SystemExit(
        "No pending topics left in content_plan.json. Add more topics before the next run."
    )


def generate_script(topic_title: str, style: str) -> str:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.6-flash")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        style=style, target_words=TARGET_WORDS, video_minutes=VIDEO_MINUTES
    )
    prompt = f"{system_prompt}\n\nTonight's story topic: \"{topic_title}\""
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Safety net: strip any stray markdown/formatting Gemini might add.
    text = re.sub(r"[#*_`]", "", text)
    return text


def generate_author_note(topic_title: str) -> str:
    """A short, specific 2-3 sentence note for the video description so the
    description isn't the exact same boilerplate every single upload."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.6-flash")
    prompt = (
        "Write 2 short sentences (max 40 words total) that could sit at the top of a "
        "YouTube description for a bedtime sleep-story video, speaking directly and "
        "warmly to the viewer about tonight's specific story below. Be specific to the "
        "topic, not generic boilerplate. No hashtags, no emojis, no quotation marks.\n\n"
        f"Tonight's story: \"{topic_title}\""
    )
    response = model.generate_content(prompt)
    return response.text.strip()


def derive_visual_queries(topic_title: str) -> list:
    """Ask Gemini for a handful of calm Pexels search queries matching the story."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.6-flash")
    prompt = (
        "Give me 6 short Pexels stock-video search queries (2-4 words each) for calm, "
        "slow, sleep-story background footage matching this topic. Nature, soft light, "
        "slow motion. No people talking, no text overlays, no fast motion. "
        f"Topic: \"{topic_title}\". "
        "Output ONLY the 6 queries, one per line, no numbering, no extra text."
    )
    response = model.generate_content(prompt)
    lines = [l.strip("-• \t") for l in response.text.strip().splitlines() if l.strip()]
    return lines[:6] if lines else ["calm nature slow motion"]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    plan = load_plan()
    topic = pick_topic(plan)
    history_count = len(plan.get("history", []))
    style = pick_style_variant(history_count)

    print(f"Generating sleep-story script for: {topic['title']}")
    print(f"Narrative style for this run: {style}")
    script_text = generate_script(topic["title"], style)
    visual_queries = derive_visual_queries(topic["title"])
    author_note = generate_author_note(topic["title"])

    word_count = len(script_text.split())
    print(f"Script generated: {word_count} words (target ~{TARGET_WORDS})")

    with open(os.path.join(OUT_DIR, "script.txt"), "w", encoding="utf-8") as f:
        f.write(script_text)

    metadata = {
        "topic_id": topic["id"],
        "title": topic["title"],
        "word_count": word_count,
        "visual_queries": visual_queries,
        "style": style,
        "author_note": author_note,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(OUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Mark topic done and log history so it's never reused.
    topic["status"] = "done"
    plan["history"].append(
        {
            "topic_id": topic["id"],
            "title": topic["title"],
            "generated_at": metadata["generated_at"],
        }
    )
    save_plan(plan)

    print("Done. Wrote output/script.txt and output/metadata.json")


if __name__ == "__main__":
    main()
