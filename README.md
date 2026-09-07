# Sleep Story Automation

Roz automatic ek 15-25 minute ka calm sleep-story video banata aur YouTube pe upload karta hai.
Gemini script likhta hai, edge-tts soft awaaz mein narrate karta hai, Pexels se calm background
clips aati hain, ffmpeg video assemble karta hai, aur GitHub Actions roz khud trigger karta hai.
100% free (GitHub Actions free tier + free API tiers).

## Pipeline
```
generate_script.py   -> Gemini se sleep-story script (~word count = VIDEO_MINUTES x 130)
generate_audio.py    -> edge-tts se slow/soft narration (mp3)
fetch_background.py  -> Pexels se calm clips (kabhi repeat nahi hote)
compose_video.py     -> ffmpeg se video + background music mix + final mp4
upload_youtube.py    -> YouTube pe unique title/description ke saath upload
```
`main.py` in sabko order mein chalata hai. `.github/workflows/daily-upload.yml` isko roz
schedule pe (aur manually bhi) trigger karta hai.

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
`content_plan.json` mein 10 starter topics already hain. Jab sab "done" ho jayen to naye topics
add karna mat bhoolna (`"status": "pending"` ke saath), warna pipeline fail ho jayega.

### 6. Schedule time set karo
`.github/workflows/daily-upload.yml` mein cron `"0 21 * * *"` hai (21:00 UTC roz). Apne audience
ke time-zone ke hisaab se badal do.

### 7. Test run
GitHub par repo ke Actions tab mein jaake workflow select karo -> "Run workflow" (manual trigger).
Poora pipeline chalke dekho, koi error aaye to Actions log mein dikh jayega.

## YouTube policy notes
- Roz sirf 1 video daalo, spam mat lagao
- Har video ka title/description unique hai (script auto-generate karta hai)
- `CHANNEL_MADE_FOR_KIDS=false` set hai workflow mein (adult sleep stories ke liye sahi)
- Same script/story kabhi dobara nahi banti — `content_plan.json` history track karta hai
- Pexels clips bhi dedup hote hain (`used_pexels_ids` list)

## Costs
Sab kuch free tier ke andar: GitHub Actions (2000 free min/month), Gemini free tier, Pexels free
tier, YouTube Data API free quota (upload me thoda quota lagta hai, daily 1 upload easily fit ho
jata hai).
