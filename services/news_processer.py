import sqlite3
import hashlib
import services.scrape_web as sw

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

# def insert_data(item):
#     conn = sqlite3.connect("data.db")
#     conn.execute("PRAGMA foreign_keys = ON;")
#     cursor = conn.cursor()

#     # 1) posted_news
#     status = check_post_status(conn, item)
#     if status == "CREATE":
#         content_hash = generate_hash(item.get("content", ""))
#         cursor.execute("""
#             INSERT INTO posted_news (post_id, title, url, content, content_hash, timestamp)
#             VALUES (?, ?, ?, ?, ?, ?)
#         """, (
#             item.get("id"),
#             item.get("title"),
#             item.get("url"),
#             item.get("content"),
#             content_hash,
#             item.get("timestamp"),
#         ))
#         conn.commit()
#     elif status == "UPDATE":
#         content_hash = generate_hash(item.get("content", ""))
#         cursor.execute("""
#             UPDATE posted_news
#             SET title = ?, url = ?, content = ?, content_hash = ?, timestamp = ?
#             WHERE post_id = ?
#         """, (
#             item.get("title"),
#             item.get("url"),
#             item.get("content"),
#             content_hash,
#             item.get("timestamp"),
#             item.get("id")
#         ))
#         conn.commit()
#     else:
#         conn.close()
#         return

#     # 2) tags and post_tags
#     tags = item.get("tags", [])
#     for tag in tags:
#         tag_id = tag.get("id")
#         tag_name = tag.get("name")

#         # Insert into tags table
#         cursor.execute("""
#             INSERT OR IGNORE INTO tags (tag_id, tag_name)
#             VALUES (?, ?)
#         """, (tag_id, tag_name))
#         conn.commit()

#         # Insert into post_tags table
#         cursor.execute("""
#             INSERT OR IGNORE INTO post_tags (post_id, tag_id)
#             VALUES (?, ?)
#         """, (item.get("id"), tag_id))
#         conn.commit()

#     # 3) Clear existing files and images for updates
#     if status == "UPDATE":
#         cursor.execute("""
#             DELETE FROM files WHERE post_id = ?
#         """, (item.get("id"),))
#         conn.commit()

#         cursor.execute("""
#             DELETE FROM images WHERE post_id = ?
#         """, (item.get("id"),))
#         conn.commit()

#     # 4) files
#     files = item.get("files", [])
#     for file_url in files:
#         cursor.execute("""
#             INSERT OR IGNORE INTO files (post_id, file_url)
#             VALUES (?, ?)
#         """, (item.get("id"), file_url))
#         conn.commit()

#     # 5) images
#     images = item.get("images_list", [])
#     for image_url in images:
#         cursor.execute("""
#             INSERT OR IGNORE INTO images (post_id, image_url)
#             VALUES (?, ?)
#         """, (item.get("id"), image_url))
#         conn.commit()

#     # 5) repost
#     cursor.execute("""
#         INSERT OR IGNORE INTO repost (forum_channel_id, post_id)
#         SELECT channel_id, ? FROM registered_forum
#     """, (item.get("id"),))
#     conn.commit()
#     conn.close()


# def update_news():
#     # 1) Scrape all news
#     all_items = sw.main()
#     if not all_items:
#         print("[Warning] 有分類，但抓不到任何貼文。")
#         return
    
#     # TODO: Use LLMs to rewrite content or summarize content

#     # 3) Update to database
#     for item in all_items:
#         insert_data(item)

#     print(f"[Info] 已更新 {len(all_items)} 筆貼文到資料庫。")
def insert_data(conn, item):
    """
    優化點：接收 conn 物件，不在此處建立連線，也不在此處 commit。
    """
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

        # 更新時先清空舊的關聯資料
        cursor.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
        cursor.execute("DELETE FROM files WHERE post_id = ?", (post_id,))
        cursor.execute("DELETE FROM images WHERE post_id = ?", (post_id,))

    # 2) tags
    for tag in item.get("tags", []):
        t_id, t_name = tag.get("id"), tag.get("name")
        cursor.execute("INSERT OR IGNORE INTO tags (tag_id, tag_name) VALUES (?, ?)", (t_id, t_name))
        cursor.execute("INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (?, ?)", (post_id, t_id))

    # 3) files & images
    for file_url in item.get("files", []):
        cursor.execute("INSERT OR IGNORE INTO files (post_id, file_url) VALUES (?, ?)", (post_id, file_url))
    
    for image_url in item.get("images_list", []):
        cursor.execute("INSERT OR IGNORE INTO images (post_id, image_url) VALUES (?, ?)", (post_id, image_url))

    # 4) repost (產生任務)
    cursor.execute("""
        INSERT OR IGNORE INTO repost (forum_channel_id, post_id)
        SELECT channel_id, ? FROM registered_forum
    """, (post_id,))

def update_news():
    all_items = sw.main()
    if not all_items: 
        return

    # 建立單一連線並開啟 WAL
    conn = sqlite3.connect("data.db")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    print("[Info] 開始同步貼文到資料庫...")

    try:
        # 使用 Transaction
        with conn:
            for item in all_items:
                insert_data(conn, item)
        print(f"[Info] 已同步 {len(all_items)} 筆貼文。")
    except Exception as e:
        print(f"[Error] 資料庫寫入失敗: {e}")
    finally:
        conn.close()