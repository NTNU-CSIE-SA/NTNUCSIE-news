import logging
import sqlite3
import os

from config.config import DB_PATH


log = logging.getLogger(__name__)
    
def init_db():
    # Create data directory if not exists
    log.info("Initializing database...")
    data_dir = os.path.dirname(DB_PATH)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    # 0) Initialize database
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1) registered_forum
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_forum (
            channel_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    log.debug("Created table\033[1m registered_forum\033[0m.")
    
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
    log.debug("Created table \033[1mposted_news\033[0m.")

    # 3) tags
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    log.debug("Created table \033[1mtags\033[0m.")

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
    log.debug("Created table \033[1mpost_tags\033[0m.")

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
    log.debug("Created table \033[1mfiles\033[0m.")

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
    log.debug("Created table \033[1mimages\033[0m.")

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
    log.debug("Created table \033[1mforum_posted\033[0m.")

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
    log.debug("Created table \033[1mrepost\033[0m.")

    log.info("Database initialized.")
    
    conn.close()