import asyncio
import sqlite3
import logging
import os

import services.news_processer as np

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any
from discord.ext import commands, tasks
from config.config import UPDATE_MINUTES, DB_PATH

log = logging.getLogger(__name__)

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()

    async def cog_load(self):
        self.scheduled_post.start()

    def cog_unload(self):
        self.scheduled_post.cancel()

    def _get_db(self):
        conn = sqlite3.connect(DB_PATH, timeout=10) 
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;") # Foreign key support
        conn.row_factory = sqlite3.Row
        return conn

    @tasks.loop(minutes=UPDATE_MINUTES)
    async def scheduled_post(self):
        async with self._lock:
            # 1) Update news
            log.info("Updating news database...")
            await asyncio.to_thread(np.update_news)
            log.info("News database updated.")

            # 2) Get repost tasks
            with self._get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        r.forum_channel_id, 
                        r.post_id, 
                        p.title, 
                        p.url, 
                        p.content, 
                        p.timestamp, 
                        f.dc_thread_id
                    FROM repost r
                    JOIN posted_news p ON r.post_id = p.post_id
                    LEFT JOIN forum_posted f ON r.forum_channel_id = f.forum_channel_id AND r.post_id = f.post_id
                    WHERE p.timestamp <= datetime('now')
                    LIMIT 50
                """)
                tasks_rows = cursor.fetchall()
                if not tasks_rows: 
                    log.info("No pending repost tasks found.")
                    return

                forum_cog = self.bot.get_cog("Forum")
                log.info(f"Found {len(tasks_rows)} repost tasks to process.")
                if not forum_cog: 
                    return

                # 3) Get additional post info
                posts_info = self._get_posts_additional_info(cursor, {row['post_id'] for row in tasks_rows})

                # 4) Process repost tasks
                ok = 0
                for row in tasks_rows:
                    f_id = row['forum_channel_id']
                    forum = self.bot.get_channel(f_id)

                    if forum is None:
                        log.warning(f"偵測到失效頻道 ID {f_id}，自動從資料庫移除。")
                        cursor.execute("DELETE FROM registered_forum WHERE channel_id = ?", (f_id,))
                        cursor.execute("DELETE FROM repost WHERE forum_channel_id = ?", (f_id,))
                        cursor.execute("DELETE FROM forum_posted WHERE forum_channel_id = ?", (f_id,))
                        conn.commit()
                        continue

                    p_id = row['post_id']
                    info = posts_info.get(p_id, {})

                    post_data = {
                        "url": row['url'],
                        "title": row['title'],
                        "content": row['content'],
                        "timestamp": datetime.fromisoformat(row['timestamp']).replace(tzinfo=TAIPEI_TZ) if row['timestamp'] else None,
                        "tags": info.get("tags", []),
                        "images_url": info.get("image_urls", []),
                        "files_url": info.get("file_urls", [])
                    }

                    try:
                        if row['dc_thread_id'] is None:
                            # 建立新貼文
                            new_dc_id = await forum_cog.create_post(f_id, post_data)
                            if new_dc_id:
                                cursor.execute("INSERT OR REPLACE INTO forum_posted (forum_channel_id, post_id, dc_thread_id) VALUES (?, ?, ?)",
                                               (f_id, p_id, str(new_dc_id)))
                        else:
                            # TODO: Handle updates (update_post)
                            pass

                        # 成功後刪除任務並提交
                        cursor.execute("DELETE FROM repost WHERE forum_channel_id = ? AND post_id = ?", (f_id, p_id))
                        conn.commit()
                        ok += 1


                    except Exception as e:
                        log.error(f"Failed to post to forum channel {f_id} for post {p_id}: {e}")
                    
                    # time limit
                    await asyncio.sleep(10)
                
                log.info(f"Repost task processing completed: {ok}/{len(tasks_rows)} succeeded.")

    def _get_posts_additional_info(self, cursor, post_ids: set) -> Dict[int, Any]:
        """封裝輔助查詢，讓主邏輯更乾淨"""
        info = {}
        for p_id in post_ids:
            tags = [r[0] for r in cursor.execute("SELECT t.tag_name FROM tags t JOIN post_tags pt ON t.tag_id = pt.tag_id WHERE pt.post_id = ?", (p_id,)).fetchall()]
            imgs = [r[0] for r in cursor.execute("SELECT image_url FROM images WHERE post_id = ?", (p_id,)).fetchall()]
            files = [r[0] for r in cursor.execute("SELECT file_url FROM files WHERE post_id = ?", (p_id,)).fetchall()]
            info[p_id] = {"tags": tags, "image_urls": imgs, "file_urls": files}
        return info

    @scheduled_post.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduler(bot))