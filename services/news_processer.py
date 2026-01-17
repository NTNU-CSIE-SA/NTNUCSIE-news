import logging
import sqlite3
import hashlib
import services.scrape_web as sw

from config.config import DB_PATH

log = logging.getLogger(__name__)

def generate_hash(content: str) -> str:
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def check_post_status(conn, item):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content_hash FROM posted_news WHERE post_id = ?
    """, (item.get("id"),))
    row = cursor.fetchone()

    if row is None:
        return "CREATE"

    existing_hash = row[0]
    new_hash = generate_hash(item.get("content", ""))

    if existing_hash != new_hash:
        return "UPDATE"
    return "NO_CHANGE"

def insert_data(conn, item):
    cursor = conn.cursor()
    post_id = item.get("id")
    status = check_post_status(conn, item)

    if status == "NO_CHANGE":
        return

    content_hash = generate_hash(item.get("content", ""))

    # 1) posted_news (CREATE or UPDATE)
    if status == "CREATE":
        cursor.execute("""
            INSERT INTO posted_news (post_id, title, url, content, content_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (post_id, item.get("title"), item.get("url"), item.get("content"), content_hash, item.get("timestamp")))
    else:
        cursor.execute("""
            UPDATE posted_news
            SET title = ?, url = ?, content = ?, content_hash = ?, timestamp = ?
            WHERE post_id = ?
        """, (item.get("title"), item.get("url"), item.get("content"), content_hash, item.get("timestamp"), post_id))

        # Remove existing tags, files, images for UPDATE
        cursor.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
        cursor.execute("DELETE FROM files WHERE post_id = ?", (post_id,))
        cursor.execute("DELETE FROM images WHERE post_id = ?", (post_id,))

    # 2) tags
    tags = item.get("tags", [])
    for tag_name in tags:
        cursor.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag_name,))
        cursor.execute("SELECT tag_id FROM tags WHERE tag_name = ?", (tag_name,))
        result = cursor.fetchone()
        
        if result:
            tag_id = result[0]
            cursor.execute("""
                INSERT OR IGNORE INTO post_tags (post_id, tag_id)
                VALUES (?, ?)
            """, (post_id, tag_id))

    # 3) files & images
    for file_url in item.get("files", []):
        cursor.execute("INSERT OR IGNORE INTO files (post_id, file_url) VALUES (?, ?)", (post_id, file_url))
    
    for image_url in item.get("images", []):
        cursor.execute("INSERT OR IGNORE INTO images (post_id, image_url) VALUES (?, ?)", (post_id, image_url))

    # 4) repost
    cursor.execute("""
        INSERT OR IGNORE INTO repost (forum_channel_id, post_id)
        SELECT channel_id, ? FROM registered_forum
    """, (post_id,))

def update_news():
    # 1) Scrape all news
    all_items = sw.main()
    if not all_items: 
        return
    
    # 2) Update to database
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    log.info(f"Updating {len(all_items)} news items to database...")

    try:
        with conn:
            ok = 0
            for item in all_items:
                ## TODO: Use LLMs to rewrite content or summarize content

                ## 3) Insert or update data
                if isinstance(item, dict):
                    insert_data(conn, item)
                    ok += 1
                else:
                    log.warning(f"Invalid item format: {item}")
            log.info(f"Successfully updated {ok}/{len(all_items)} items.")
    except Exception as e:
        log.error(f"Error updating news: {e}")
    finally:
        conn.close()