# Sleep Story Shorts Automation

Roz automatic ek **~60 second** ka calm sleep-story **YouTube Short** banata aur upload karta hai.

Gemini short script likhta hai, edge-tts soft awaaz mein narrate karta hai, Pexels se vertical calm clips aati hain, ffmpeg 9:16 video assemble karta hai, aur GitHub Actions schedule pe trigger karta hai.

**Full SEO** included: keyword-rich title, optimized description, hashtags (#Shorts + niche), backend tags.

100% free (GitHub Actions free tier + free API tiers).

## Pipeline

```
generate_script.py   -> Gemini se ~60s sleep-story script + full SEO metadata
generate_audio.py    -> edge-tts se slow/soft narration (mp3)
fetch_background.py  -> Pexels se vertical calm clips (kabhi repeat nahi hote)
compose_video.py     -> ffmpeg se 1080x1920 (9:16) Short + music mix
upload_youtube.py    -> YouTube pe SEO title/description/tags ke saath upload
```

`main.py` in sabko order mein chalata hai. `.github/workflows/daily-upload.yml` isko roz schedule pe (aur manually bhi) trigger karta hai.

## Setup (ek baar karna hai)

### 1. Free API keys lo
- **Gemini**: https://aistudio.google.com — free API key
- **Pexels**: https://www.pexels.com/api — free signup, instant key

### 2. YouTube OAuth (refresh token banao)
1. https://console.cloud.google.com pe naya project banao
2. "YouTube Data API v3" enable karo
3. OAuth client credentials banao — type **Desktop app**
4. `client_secrets.json` download karke repo root mein daal do (commit MAT karna, `.gitignore` mein already hai)
5. Locally chalao:
   ```
   pip install -r requirements.txt
   python scripts/auth_setup.py
   ```
   Browser khulega, apne YouTube channel wale Google account se login karo. Terminal mein
   `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, aur `YOUTUBE_REFRESH_TOKEN` print honge.

### 3. GitHub repo Secrets add karo
Repo -> Settings -> Secrets and variables -> Actions -> "New repository secret":
- `GEMINI_API_KEY`
- `PEXELS_API_KEY`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

### 4. (Optional) Background music
`assets/music/` folder mein ek ya do royalty-free calm/ambient `.mp3` daal do (YouTube Audio
Library, Pixabay Music, ya Freesound se free mil jaate hain). Nahi doge to sirf narration jayega —
video chalta rahega, bas music nahi hoga.

### 5. Topics list badhao
`content_plan.json` mein starter topics already hain. Jab sab "done" ho jayen to naye topics
add karna mat bhoolna (`"status": "pending"` ke saath), warna pipeline fail ho jayega.

### 6. Schedule time set karo
`.github/workflows/daily-upload.yml` mein cron `"0 21 * * *"` hai (21:00 UTC roz). Apne audience
ke time-zone ke hisaab se badal do.

### 7. Test run
GitHub par repo ke Actions tab mein jaake workflow select karo -> "Run workflow" (manual trigger).
Poora pipeline chalke dekho, koi error aaye to Actions log mein dikh jayega.

## YouTube Shorts + SEO notes
- Har Short ~60 seconds, vertical 1080x1920 (9:16) — automatically Shorts feed mein jaata hai
- Title: keyword front-loaded, under 70 characters
- Description: primary keyword pehli sentence mein + soft CTA
- Hashtags: `#Shorts` + 3-4 niche tags (description ke end mein)
- Backend tags: 8-12 relevant keywords
- `CHANNEL_MADE_FOR_KIDS=false` set hai (adult sleep stories ke liye sahi)
- Same script/story kabhi dobara nahi banti — `content_plan.json` history track karta hai
- Pexels clips bhi dedup hote hain (`used_pexels_ids` list)
- AI-generated disclosure (`containsSyntheticMedia: true`) already hai

## Costs
Sab kuch free tier ke andar: GitHub Actions (2000 free min/month), Gemini free tier, Pexels free
tier, YouTube Data API free quota (daily 1 Short easily fit ho jata hai).
