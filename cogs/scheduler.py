import json
import asyncio

from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from cogs.forum import Forum

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
DATA_FILE = "data/post.json"
CONFIG_FILE = "data/forum_config.json"

class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot, forum_channel_ids: list[int] = None):
        self.bot = bot
        self.forum_channel_list = forum_channel_ids or []
        self._lock = asyncio.Lock()

    async def cog_load(self):
        if not self.scheduled_post.is_running():
            self.scheduled_post.start()

    def cog_unload(self):
        self.scheduled_post.cancel()

    @tasks.loop(minutes=1)
    async def scheduled_post(self):
        async with self._lock:
            now = datetime.now(TAIPEI_TZ)
            
            # read posts from JSON file
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    posts = json.load(f)
            except FileNotFoundError:
                print("[Error] 找不到 data/post.json 檔案。")
                return
            except json.JSONDecodeError:
                print("[Error] data/post.json 檔案格式錯誤。")
                return
            
            # load posts to list
            posts_to_post = []
            for post in posts:
                post_time_str = post.get("timestamp")
                if not post_time_str:
                    continue
                try:
                    dt = datetime.fromisoformat(post_time_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=TAIPEI_TZ)
                    post_time = dt.astimezone(TAIPEI_TZ)
                except ValueError:
                    print(f"[Error] 貼文時間格式錯誤: {post_time_str}")
                    continue
                if now >= post_time:
                    posts_to_post.append(post)

            forum_cog: Forum = self.bot.get_cog("Forum")
            if not forum_cog:
                print("[Error] 找不到 Forum cog，無法發佈貼文。")
                return

            # launch post tp forum
            for post in posts_to_post:
                title = post.get("title", "無標題")
                content = post.get("content", "")
                tags = post.get("tags", [])
                posted_list = post.get("posted", [])

                try:
                    posted_list = await forum_cog.post_forum(title, content, tags, posted_list)
                    print(f"[Info] 已發佈貼文: {title}")
                except Exception as e:
                    print(f"[Error] 發佈貼文失敗: {title}, 錯誤: {e}")
                    continue

                post["posted"] = posted_list

            # Update the JSON file to mark posts as posted
            try:
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(posts, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"[Error] 無法儲存貼文資料: {e}")
    
    @scheduled_post.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    forum_id = config.get("registered_forum", [])
    
    await bot.add_cog(Scheduler(bot, forum_id))