import json
import os
import re
from datetime import timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from playwright.sync_api import sync_playwright


JSON_PATH = "data/posts.json"
BASE_URL = "https://ntnucsie.info"
ANNOUNCEMENT_URL = "https://ntnucsie.info/announcement/"


# ----------------------------
# File utils
# ----------------------------
def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_db(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(path: str, data: List[Dict[str, Any]]) -> None:
    ensure_parent_dir(path)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ----------------------------
# Text / time utils
# ----------------------------
def normalize_text(s: str) -> str:
    s = re.sub(r"\r\n", "\n", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def to_iso8601(ts: str) -> str:
    dt = date_parser.parse(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.isoformat().replace("+00:00", "Z")


def unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ----------------------------
# requests html fetch
# ----------------------------
def fetch_html(url: str) -> BeautifulSoup:
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def pick_main_container(soup: BeautifulSoup):
    return soup.find("main") or soup.find("article") or soup.body or soup


def extract_timestamp_from_page(soup: BeautifulSoup) -> Optional[str]:
    # 文章頁常見 'Sep 20, 2025' / '公告日期：2025年9月20日'
    text = " ".join(soup.get_text("\n", strip=True).split())
    m = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b", text)
    if m:
        return to_iso8601(m.group(0))
    m2 = re.search(r"公告日期[:：]\s*([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)", text)
    if m2:
        return to_iso8601(m2.group(1))
    return None


# ----------------------------
# Playwright: scrape announcement list WITH tags
# ----------------------------
def scrape_post_list_with_tags() -> List[Dict[str, Any]]:
    """
    直接從 /announcement/ 頁面抓：
      - title
      - tags (chips)
      - url
      - date (卡片上顯示的日期)
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(ANNOUNCEMENT_URL, wait_until="networkidle")

        # 等卡片出現（若 selector 變動，你再貼我 HTML，我幫你調）
        # 這邊用「卡片內有 > 連結」的方式抓
        page.wait_for_timeout(500)  # 稍微保險一下

        cards = page.locator("a[href^='/announcement/']").all()

        items: List[Dict[str, Any]] = []
        seen = set()

        for a in cards:
            href = a.get_attribute("href")
            if not href:
                continue
            url = urljoin(BASE_URL, href)

            # 避免把 "Back to announcement" 之類的也抓進來
            if not "/announcement/" in url or url.rstrip("/").endswith("/announcement"):
                continue

            if url in seen:
                continue
            seen.add(url)

            # 從卡片附近抓日期 / tags / title：往上找包含它的 container
            # Playwright 沒有「parent selector」很好用，所以先用 a 的文字 + 同層 chips 推斷
            title = a.inner_text().strip()
            title = re.sub(r"\s+", " ", title)

            # 抓同一張卡片上的 tags：找附近所有 button/span 類似 chip
            # 用 evaluate 直接爬 DOM 最穩
            meta = a.evaluate(
                """(el) => {
                    // 找卡片容器：往上走幾層
                    let cur = el;
                    for (let i=0;i<6;i++){
                      if(!cur) break;
                      // 卡片通常會有 role 或 class，抓不到就繼續往上
                      if(cur.tagName.toLowerCase() === 'div') break;
                      cur = cur.parentElement;
                    }
                    const root = cur || el.parentElement || el;
                    const text = root.innerText || '';
                    // tags: 常見是小 chip，這裡抓 root 內所有 button 或 span 的短文字
                    const tags = [];
                    root.querySelectorAll('button, span, div').forEach(n=>{
                      const t = (n.innerText || '').trim();
                      if(t && t.length <= 8) tags.push(t);
                    });
                    return { text, tags };
                }"""
            )

            # meta["tags"] 裡會混到很多短字（例如月份/數字），所以我們用你站的 tag 集合過濾
            allowed_tags = {"會長股", "系學會", "總務股", "資訊股"}
            tags = []
            for t in meta.get("tags", []):
                if t in allowed_tags and t not in tags:
                    tags.append(t)

            # 日期：從卡片文字找 'SEP 20, 2025'
            card_text = meta.get("text", "")
            m = re.search(r"\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2},\s+\d{4}\b", card_text)
            date_iso = to_iso8601(m.group(0)) if m else None

            items.append({
                "id": url,          # 直接用 url 當唯一 id
                "url": url,
                "title_hint": title, # 只是 hint，真正標題以內容頁 h1 為主
                "tags": tags,
                "timestamp_hint": date_iso,
            })

        browser.close()

    return items


# ----------------------------
# Scrape post detail
# ----------------------------
def scrape_post_detail(meta: Dict[str, Any]) -> Dict[str, Any]:
    url = meta["url"]
    soup = fetch_html(url)
    main = pick_main_container(soup)

    h1 = main.find("h1") or soup.find("h1")
    title = h1.get_text(strip=True) if h1 else (meta.get("title_hint") or "(no title)")

    timestamp = extract_timestamp_from_page(soup) or meta.get("timestamp_hint")

    content_text = main.get_text("\n", strip=True)
    content_text = re.sub(r"\bBack to top\b.*", "", content_text, flags=re.I | re.S)
    content = normalize_text(content_text)

    images: List[str] = []
    for img in main.find_all("img", src=True):
        images.append(urljoin(BASE_URL, img["src"].strip()))
    images = unique_keep_order(images)

    return {
        "id": meta["id"],
        "url": url,
        "title": title,
        "tags": meta.get("tags", []),   # ✅ 你要的 tag 就在這
        "content": content,
        "images": images,
        "timestamp": timestamp,
        "posted": [],
    }


def upsert(db: List[Dict[str, Any]], item: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_id = {x.get("id"): x for x in db}
    old = by_id.get(item["id"])
    if old:
        keep_posted = old.get("posted", [])
        old.update(item)
        old["posted"] = keep_posted
    else:
        db.append(item)
    return db


def main():
    db = load_db(JSON_PATH)

    post_list = scrape_post_list_with_tags()
    if not post_list:
        print("WARN: /announcement/ 沒抓到任何卡片，可能 selector 變了。")
        return

    for meta in post_list:
        try:
            item = scrape_post_detail(meta)
            db = upsert(db, item)
            print("OK:", item["title"], "| tags:", item["tags"])
        except Exception as e:
            print("FAIL:", meta.get("url"), e)

    db.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    save_db(JSON_PATH, db)
    print(f"Saved {len(db)} posts -> {JSON_PATH}")


if __name__ == "__main__":
    main()