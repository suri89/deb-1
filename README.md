# 📚 GMAT Club Scraper — Streamlit Cloud Version

No Playwright. No local setup. Runs 100% on Streamlit Cloud.

---

## 🚀 Deploy to Streamlit Cloud (5 minutes)

### Step 1 — Push to GitHub
1. Create a free GitHub account at github.com
2. Create a new repository (e.g. `gmat-scraper`)
3. Upload all files from this folder into the repo

### Step 2 — Deploy on Streamlit Cloud
1. Go to share.streamlit.io
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repo → branch: `main` → file: `app.py`
5. Click **Deploy** → live in ~2 minutes

Your app URL will be: `https://yourname-gmat-scraper.streamlit.app`

---

## 🍪 How to Get Cookies (One-Time)

1. Install **Cookie-Editor** Chrome extension (free)
   → https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm

2. Go to **gmatclub.com** and log in

3. Click the Cookie-Editor icon → click **Export** → **Export JSON**

4. Copy the entire JSON text

5. Paste into the app's cookie box → click Start Scraping

---

## 📁 Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `scraper.py` | requests-based scraper (no Playwright) |
| `excel_builder.py` | Formatted Excel export |
| `requirements.txt` | Dependencies |

---

## 📊 Excel Output

| Sheet | Contents |
|-------|----------|
| Quantitative | PS questions |
| Verbal | CR + RC questions |

Columns: Title, Question, Options A–E, Answer, Solution, Difficulty, Type, URL

---

## ⚠️ Notes

- Cookies expire after ~30 days — re-export when needed
- Free Streamlit Cloud apps sleep after 7 days of inactivity (just reopen to wake)
- Scraping ~50 questions takes 5–8 minutes
