import os
import json

from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from cogs.forum import Forum

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
DATA_FILE = "data/post.json"

class Scheduler(Forum):
    def __init__(self, bot: commands.Bot, forum_channel_id: int = None):
        self.bot = bot
        self.forum_channel_id = forum_channel_id
        self.scheduled_post.start()

    def cog_unload(self):
        self.scheduled_post.cancel()

    @tasks.loop(seconds=10)
    async def scheduled_post(self):
        now = datetime.now(TAIPEI_TZ)
        
        # 讀取貼文資料
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                posts = json.load(f)
        except FileNotFoundError:
            print("[Error] 找不到 data/post.json 檔案。")
            return
        except json.JSONDecodeError:
            print("[Error] data/post.json 檔案格式錯誤。")
            return

        posts_to_post = []
        for post in posts:
            post_time_str = post.get("timestamp")
            if not post_time_str:
                continue
            try:
                post_time = datetime.fromisoformat(post_time_str.replace("Z", "+00:00")).astimezone(TAIPEI_TZ)
            except ValueError:
                print(f"[Error] 貼文時間格式錯誤: {post_time_str}")
                continue
            if post.get("posted"):
                continue
            if now >= post_time:
                posts_to_post.append(post)

        for post in posts_to_post:
            if post.get("posted"):
                continue
            title = post.get("title", "無標題")
            content = post.get("content", "")
            tags = post.get("tags", [])
            await self.post_forum(title, content, tags)
            post["posted"] = True

        # Update the JSON file to mark posts as posted
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(posts, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[Error] 無法儲存貼文資料: {e}")


async def setup(bot: commands.Bot):
    forum_id = int(os.getenv("FORUM_CHANNEL_ID"))
    await bot.add_cog(Scheduler(bot, forum_id))