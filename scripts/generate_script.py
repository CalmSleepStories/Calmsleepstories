"""
Picks the next 'pending' topic from content_plan.json, asks Gemini to write a
short ~60-second calm sleep-story script for YouTube Shorts, and saves it +
SEO-optimized metadata for the rest of the pipeline.
Also marks the topic 'done' and appends to history so the same story is never
generated twice.
"""

import os
import json
import re
from datetime import datetime, timezone

import google.generativeai as genai

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_PATH = os.path.join(ROOT, "content_plan.json")
OUT_DIR = os.path.join(ROOT, "output")

# Fixed 60-second Shorts target.
# ~130 spoken words per minute at a calm sleep-story pace → ~130 words for 60s.
TARGET_WORDS = 130
VIDEO_SECONDS = 60

# Rotating narrative angles so every Short isn't structurally identical.
STYLE_VARIANTS = [
    "Second person ('you'), starting with arriving somewhere and settling in slowly.",
    "Gentle third person following one quiet character, starting mid-routine, already at ease.",
    "Second person, starting with a small sensory detail (a sound or smell) before revealing the place.",
    "Gentle third person, structured as a slow walk from one quiet spot to another.",
    "Second person, framed as a soft memory being recalled, unhurried, half-dreaming.",
]

SYSTEM_PROMPT_TEMPLATE = """You are writing a short bedtime sleep story script for a YouTube Short (exactly ~60 seconds when spoken slowly).

Narrative approach for this story specifically: {style}

Rules:
- Very slow pacing, present tense.
- No jump scares, conflict, tension, or cliffhangers. Nothing exciting should happen.
- Focus on calm sensory details: soft sounds, gentle light, temperature, textures, quiet repetitive actions.
- Short, simple sentences. Frequent natural pauses (write them as separate short paragraphs).
- Do not use chapter headings, slide numbers, bullet points, or any formatting.
- Do not include stage directions like "[pause]" or sound effect notes.
- Output ONLY the narration text the narrator will read aloud, nothing else.
- Target length: approximately {target_words} words (this is a 60-second Short).
- Keep it complete and satisfying within the short length — a tiny self-contained calm moment.
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
        style=style, target_words=TARGET_WORDS
    )
    prompt = f"{system_prompt}\n\nTonight's story topic: \"{topic_title}\""
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Safety net: strip any stray markdown/formatting Gemini might add.
    text = re.sub(r"[#*_`]", "", text)
    return text


def generate_seo_metadata(topic_title: str) -> dict:
    """Generate full SEO package: keyword-optimized title, description, tags, hashtags."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.6-flash")

    prompt = f"""You are a YouTube Shorts SEO expert for calm sleep / relaxation content.

Topic: "{topic_title}"

Generate a complete SEO package for a 60-second calm sleep story Short. Output ONLY valid JSON with these exact keys:

{{
  "primary_keyword": "main search phrase people would type (2-5 words)",
  "title": "YouTube title under 65 characters, front-load the primary keyword, calm and click-worthy, NO hashtags",
  "description": "3-5 short sentences. First sentence must include the primary keyword. Then 1-2 calming sentences about the story. End with a soft CTA like 'Follow for more calm sleep stories'. No hashtags here.",
  "hashtags": ["#Shorts", "#SleepStory", "#Calm", "#Relaxation", "#DeepSleep"],
  "tags": ["list of 8-12 backend tags as strings, mix of primary keyword, long-tail, and related terms like sleep story, bedtime story for adults, calm narration, etc."]
}}

Rules:
- Title: max 65 characters, keyword first, natural, no clickbait.
- Description: keyword in first sentence, warm tone, under 400 characters total.
- Hashtags: exactly 5, always start with #Shorts, then niche ones. No #fyp or #viral.
- Tags: 8-12 items, relevant, no duplicates.
- Output pure JSON only, no markdown, no explanation.
"""

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        seo = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if Gemini returns messy JSON
        seo = {
            "primary_keyword": "calm sleep story",
            "title": f"{topic_title} | Calm Sleep Story",
            "description": f"A calm sleep story about {topic_title.lower()}. Soft narration to help you relax and fall asleep. Follow for more peaceful Shorts.",
            "hashtags": ["#Shorts", "#SleepStory", "#Calm", "#Relaxation", "#DeepSleep"],
            "tags": [
                "sleep story", "calm sleep story", "bedtime story", "relaxation",
                "deep sleep", "sleep aid", "calm narration", "peaceful story",
                "fall asleep fast", "sleep shorts", "ambient sleep", "soft voice"
            ],
        }

    # Hard safety limits
    if len(seo.get("title", "")) > 70:
        seo["title"] = seo["title"][:67] + "..."
    seo["hashtags"] = (seo.get("hashtags") or ["#Shorts", "#SleepStory", "#Calm"])[:5]
    if "#Shorts" not in seo["hashtags"] and "#shorts" not in [h.lower() for h in seo["hashtags"]]:
        seo["hashtags"] = ["#Shorts"] + seo["hashtags"][:4]

    return seo


def derive_visual_queries(topic_title: str) -> list:
    """Ask Gemini for calm vertical-friendly Pexels search queries."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.6-flash")
    prompt = (
        "Give me 5 short Pexels stock-video search queries (2-4 words each) for calm, "
        "slow, vertical-friendly sleep-story background footage matching this topic. "
        "Nature, soft light, slow motion, peaceful interiors. No people talking, no text, no fast motion. "
        f"Topic: \"{topic_title}\". "
        "Output ONLY the 5 queries, one per line, no numbering, no extra text."
    )
    response = model.generate_content(prompt)
    lines = [l.strip("-• \t") for l in response.text.strip().splitlines() if l.strip()]
    return lines[:5] if lines else ["calm nature vertical", "soft light room", "rain window slow"]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    plan = load_plan()
    topic = pick_topic(plan)
    history_count = len(plan.get("history", []))
    style = pick_style_variant(history_count)

    print(f"Generating 60s Shorts script for: {topic['title']}")
    print(f"Narrative style for this run: {style}")
    script_text = generate_script(topic["title"], style)
    visual_queries = derive_visual_queries(topic["title"])
    seo = generate_seo_metadata(topic["title"])

    word_count = len(script_text.split())
    print(f"Script generated: {word_count} words (target ~{TARGET_WORDS})")
    print(f"SEO Title: {seo.get('title')}")
    print(f"Primary keyword: {seo.get('primary_keyword')}")

    with open(os.path.join(OUT_DIR, "script.txt"), "w", encoding="utf-8") as f:
        f.write(script_text)

    metadata = {
        "topic_id": topic["id"],
        "title": topic["title"],
        "word_count": word_count,
        "visual_queries": visual_queries,
        "style": style,
        "seo": seo,
        "video_seconds": VIDEO_SECONDS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(OUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Mark topic done and log history so it's never reused.
    topic["status"] = "done"
    plan.setdefault("history", []).append(
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
