import re
import gc
import time
import requests
from bs4 import BeautifulSoup

# ─── URLs ─────────────────────────────────────────────────────────────────────
LOGIN_URL = "https://gmatclub.com/forum/ucp.php?mode=login"

SECTION_URLS = {
    "PS": "https://gmatclub.com/forum/problem-solving-ps-140/",
    "CR": "https://gmatclub.com/forum/critical-reasoning-cr-139/",
    "RC": "https://gmatclub.com/forum/reading-comprehension-rc-141/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or "").strip()


def extract_options(soup) -> dict:
    options = {"A": "", "B": "", "C": "", "D": "", "E": ""}
    text = soup.get_text("\n")
    for letter in ["A", "B", "C", "D", "E"]:
        pattern = rf'\(?{letter}\)?\s*[.:]?\s*(.+?)(?=\n\s*\(?[B-E]\)?|\Z)'
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            options[letter] = clean(m.group(1)[:300])
    return options


def extract_difficulty(soup) -> str:
    for div in soup.find_all(class_=re.compile(r'tag|difficulty|kudos', re.I)):
        t = clean(div.get_text())
        if any(k in t.lower() for k in ['easy', 'medium', 'hard', '500', '600', '700', '800', 'level']):
            return t
    # Also check for difficulty in text
    text = soup.get_text()
    m = re.search(r'Difficulty:\s*([^\n|]+)', text, re.IGNORECASE)
    if m:
        return clean(m.group(1))
    return "N/A"


def extract_answer(soup) -> str:
    text = soup.get_text()
    m = re.search(r'(?:OA|Official\s*Answer)[:\s]*([A-E])', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return "N/A"


def extract_solution(post_bodies) -> str:
    if len(post_bodies) < 2:
        return "N/A"
    for body in post_bodies[1:4]:
        text = clean(body.get_text(" "))
        if len(text) > 80:
            return text[:1000]
    return "N/A"


# ─── Session Login ────────────────────────────────────────────────────────────

def create_session(cookies_dict: dict) -> requests.Session:
    """Create a requests session with user-provided cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    for name, value in cookies_dict.items():
        session.cookies.set(name, value, domain=".gmatclub.com")
    return session


def verify_login(session: requests.Session) -> bool:
    """Check if the session is actually logged in."""
    try:
        resp = session.get("https://gmatclub.com/forum/", timeout=15)
        content = resp.text.lower()
        # Logged in if logout link present
        return "logout" in content or "log out" in content or "ucp.php?mode=logout" in content
    except:
        return False


# ─── Question Scraping ────────────────────────────────────────────────────────

def get_question_links(session: requests.Session, section_url: str, max_pages: int) -> list:
    links = []
    url = section_url

    for _ in range(max_pages):
        try:
            resp = session.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                if re.search(r'/forum/[a-z0-9][a-z0-9-]+-\d+\.html', href):
                    full = href if href.startswith("http") else "https://gmatclub.com" + href
                    if full not in links and "viewtopic" not in full:
                        links.append(full)

            # Next page
            next_btn = soup.find("a", string=re.compile(r'Next|›|»', re.I))
            if next_btn and next_btn.get("href"):
                nxt = next_btn["href"]
                url = nxt if nxt.startswith("http") else "https://gmatclub.com" + nxt
            else:
                break

            time.sleep(1)  # polite delay

        except Exception as e:
            print(f"Error getting links from {url}: {e}")
            break

    return links[:50]


def scrape_question(session: requests.Session, url: str, q_type: str) -> dict | None:
    try:
        resp = session.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        post_bodies = soup.find_all(class_=re.compile(r'post[_-]?body|post[_-]?content|message', re.I))
        if not post_bodies:
            post_bodies = soup.find_all("div", class_=re.compile(r'postbody|content', re.I))
        if not post_bodies:
            return None

        first_post = post_bodies[0]
        question_text = clean(first_post.get_text(" "))[:2000]
        if len(question_text) < 20:
            return None

        options    = extract_options(first_post)
        difficulty = extract_difficulty(soup)
        answer     = extract_answer(soup)
        solution   = extract_solution(post_bodies)

        title_tag = soup.find("h1") or soup.find("h2")
        title = clean(title_tag.get_text()) if title_tag else question_text[:80]

        time.sleep(0.8)  # polite delay

        return {
            "Title":      title[:150],
            "Question":   question_text,
            "Option A":   options["A"],
            "Option B":   options["B"],
            "Option C":   options["C"],
            "Option D":   options["D"],
            "Option E":   options["E"],
            "Answer":     answer,
            "Solution":   solution,
            "Difficulty": difficulty,
            "Type":       q_type,
            "URL":        url,
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def run_scraper(
    cookies_dict: dict,
    sections: list,
    max_pages: int,
    progress_callback=None,
) -> dict:
    results = {s: [] for s in sections}

    if progress_callback:
        progress_callback("🔐 Verifying session...")

    session = create_session(cookies_dict)

    if not verify_login(session):
        raise ValueError("Session invalid. Please re-export your cookies and try again.")

    if progress_callback:
        progress_callback("✅ Session verified — logged in!")

    for section in sections:
        url = SECTION_URLS[section]

        if progress_callback:
            progress_callback(f"🔍 Collecting {section} question links...")

        links = get_question_links(session, url, max_pages)

        if progress_callback:
            progress_callback(f"📋 Found {len(links)} {section} links. Scraping...")

        for i, link in enumerate(links):
            row = scrape_question(session, link, section)
            if row:
                results[section].append(row)
            if progress_callback and (i + 1) % 5 == 0:
                progress_callback(f"  {section}: {i+1}/{len(links)} scraped...")

        if progress_callback:
            progress_callback(f"✅ {section} done — {len(results[section])} questions.")

    session.close()
    gc.collect()
    return results
