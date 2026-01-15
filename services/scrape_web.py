import json
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.csie.ntnu.edu.tw"
WP_API_BASE = "https://www.csie.ntnu.edu.tw/index.php/wp-json/wp/v2"

CATEGORY_URLS = [
    "https://www.csie.ntnu.edu.tw/index.php/category/news/competition/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/announcement/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/seminar/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/enrollment/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/honor-roll/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/scholarship/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/intern/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/recruitment/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/1/", 
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
    "Connection": "keep-alive",
})

def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


# def load_db(path: str) -> List[Dict[str, Any]]:
#     if not os.path.exists(path):
#         return []

#     if os.path.getsize(path) == 0:
#         print(f"WARN: {path} 是空檔案，將重新建立。")
#         return []

#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             return json.load(f)
#         except json.JSONDecodeError as exc:
#             print(f"WARN: 讀取 {path} 失敗（{exc}），將重新建立。")
#             return []


# def save_db(path: str, data: List[Dict[str, Any]]) -> None:
#     ensure_parent_dir(path)
#     tmp = path + ".tmp"
#     with open(tmp, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)
#     os.replace(tmp, path)

def unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def extract_img_urls_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    imgs = []
    for img in soup.select("img[src]"):
        src = img.get("src")
        if src:
            imgs.append(urljoin(BASE_URL, src.strip()))
    return unique_keep_order(imgs)

def get_category_id_from_header(category_page_url: str) -> Optional[int]:
    r = SESSION.head(category_page_url, timeout=20, allow_redirects=True)
    link = r.headers.get("Link", "") or r.headers.get("link", "")
    m = re.search(r"/wp/v2/categories/(\d+)", link)
    return int(m.group(1)) if m else None

def get_category_name(cat_id: int, cache: Dict[int, str]) -> str:
    if cat_id in cache:
        return cache[cat_id]
    r = SESSION.get(f"{WP_API_BASE}/categories/{cat_id}", timeout=25)
    r.raise_for_status()
    name = r.json().get("name") or str(cat_id)
    cache[cat_id] = name
    return name

def fetch_posts_by_category(cat_id: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    page = 1
    per_page = 100

    while True:
        r = SESSION.get(
            f"{WP_API_BASE}/posts",
            params={"categories": cat_id, "per_page": per_page, "page": page, "_embed": 1},
            timeout=30,
        )

        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break

        r.raise_for_status()
        items = r.json()
        if not items:
            break

        out.extend(items)

        total_pages = int(r.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1

    return out

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
    # db = load_db(JSON_PATH)

    cat_name_cache: Dict[int, str] = {}

    cat_ids: List[int] = []
    for url in CATEGORY_URLS:
        cat_id = get_category_id_from_header(url)
        if cat_id is None:
            print(f"[Skip] not a category page (cannot parse category id): {url}")
            continue
        name = get_category_name(cat_id, cat_name_cache)
        print(f"[OK] {name} (id={cat_id}) <- {url}")
        cat_ids.append(cat_id)

    cat_ids = list(dict.fromkeys(cat_ids))

    if not cat_ids:
        print("[WARN] 沒有任何有效分類（全部解析不到 category id）。")
        return

    all_items_map: Dict[str, Dict[str, Any]] = {}

    for cat_id in cat_ids:
        cat_name = get_category_name(cat_id, cat_name_cache)
        posts = fetch_posts_by_category(cat_id)
        print(f"Fetch {cat_name} (id={cat_id}) -> {len(posts)} posts")

        for p in posts:
            post_id = str(p.get("id"))
            url = p.get("link")

            title_html = (p.get("title") or {}).get("rendered") or ""
            title = BeautifulSoup(title_html, "html.parser").get_text(strip=True)

            content_html = (p.get("content") or {}).get("rendered") or ""
            content = html_to_text(content_html)

            date_gmt = p.get("date_gmt")
            timestamp = None
            if date_gmt:
                timestamp = date_gmt if date_gmt.endswith("Z") else (date_gmt + "Z")

            tags = []
            for cid in p.get("categories", []):
                tags.append(get_category_name(int(cid), cat_name_cache))
            tags = unique_keep_order(tags)

            files = []
            embedded = p.get("_embedded", {})
            fm = embedded.get("wp:featuredmedia")
            if isinstance(fm, list) and fm:
                src = fm[0].get("source_url")
                if src:
                    files.append(urljoin(BASE_URL, src.strip()))
            files.extend(extract_img_urls_from_html(content_html))
            files = unique_keep_order(files)

            images = []
            for f in files:
                if re.search(r"\.(jpg|jpeg|png|gif|bmp|webp)(\?|$)", f, re.IGNORECASE):
                    images.append(f)
                    files.remove(f)

            all_items_map[post_id] = {
                "id": post_id,     
                "url": url,
                "title": title,
                "tags": tags,
                "content": content,
                "images": images,
                "files": files,
                "timestamp": timestamp,
                "posted": [],      
            }

    if not all_items_map:
        print("[Warning] 有分類，但抓不到任何貼文。")
        return

    return list(all_items_map.values())


if __name__ == "__main__":
    main()