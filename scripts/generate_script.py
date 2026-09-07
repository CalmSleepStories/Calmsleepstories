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

SYSTEM_PROMPT = f"""You are writing a long-form bedtime sleep story script, meant to be read aloud
slowly in a soft, calm voice for adults who want to relax and fall asleep.

Rules:
- Second person or gentle third person, present tense, very slow pacing.
- No jump scares, conflict, tension, or cliffhangers. Nothing exciting should happen.
- Long, unhurried descriptive passages: sounds, textures, light, temperature, small repetitive actions.
- Short, simple sentences. Frequent natural pauses (write them as separate short paragraphs).
- Do not use chapter headings, slide numbers, bullet points, or any formatting.
- Do not include stage directions like "[pause]" or sound effect notes.
- Output ONLY the narration text the narrator will read aloud, nothing else.
- Target length: approximately {TARGET_WORDS} words (this is a {VIDEO_MINUTES}-minute story).
"""


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


def generate_script(topic_title: str) -> str:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.6-flash")

    prompt = f"{SYSTEM_PROMPT}\n\nTonight's story topic: \"{topic_title}\""
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Safety net: strip any stray markdown/formatting Gemini might add.
    text = re.sub(r"[#*_`]", "", text)
    return text


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

    print(f"Generating sleep-story script for: {topic['title']}")
    script_text = generate_script(topic["title"])
    visual_queries = derive_visual_queries(topic["title"])

    word_count = len(script_text.split())
    print(f"Script generated: {word_count} words (target ~{TARGET_WORDS})")

    with open(os.path.join(OUT_DIR, "script.txt"), "w", encoding="utf-8") as f:
        f.write(script_text)

    metadata = {
        "topic_id": topic["id"],
        "title": topic["title"],
        "word_count": word_count,
        "visual_queries": visual_queries,
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
