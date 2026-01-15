import sqlite3
    
def init_db():
    # 0) Initialize database
    conn = sqlite3.connect("data.db")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1) registered_forum
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_forum (
            channel_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    
    # 2) posted_news
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posted_news (
            post_id INTEGER PRIMARY KEY,
            title TEXT,
            url TEXT,
            content TEXT,
            content_hash TEXT,
            timestamp DATETIME
        )
    """)
    conn.commit()
    
    # 3) tags
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            tag_id INTEGER PRIMARY KEY,
            tag_name TEXT
        )
    """)
    conn.commit()

    # 4) post_tags
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_tags (
            post_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY (post_id) REFERENCES posted_news(post_id),
            FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
        )
    """)
    conn.commit()

    # 5) files
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            file_url TEXT,
            FOREIGN KEY (post_id) REFERENCES posted_news(post_id)
        )
    """)
    conn.commit()

    # 6) images
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            image_url TEXT,
            FOREIGN KEY (post_id) REFERENCES posted_news(post_id)
        )
    """)
    conn.commit()

    # 7) forum_posted
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forum_posted (
            forum_channel_id INTEGER,
            post_id INTEGER,
            dc_thread_id TEXT,
            PRIMARY KEY (forum_channel_id, post_id),
            FOREIGN KEY (post_id) REFERENCES posted_news(post_id)
        )
    """)
    conn.commit()

    # 8) repost
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repost (
            forum_channel_id INTEGER,
            post_id INTEGER,
            PRIMARY KEY (forum_channel_id, post_id),
            FOREIGN KEY (post_id) REFERENCES posted_news(post_id)
        )
    """)
    conn.commit()
    
    conn.close()