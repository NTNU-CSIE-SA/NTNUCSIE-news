import discord
import sqlite3
import aiohttp
import io
import re
import asyncio
import logging


from discord.ext import commands
from discord import app_commands

log = logging.getLogger(__name__)
class Forum(commands.Cog):
    def __init__(self, bot: commands.Bot, forum_channel_ids: list[int] = None):
        self.bot = bot
        self.db_lock = asyncio.Lock()
    
    async def _smart_download(self, session, url, max_mb):
        """智慧下載：檢查大小，太大的回傳 URL 字串，小的回傳 discord.File"""
        try:
            async with session.head(url, timeout=5, allow_redirects=True) as resp:
                size_bytes = int(resp.headers.get('Content-Length', 0))
                if size_bytes > max_mb * 1024 * 1024:
                    return url
            
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = io.BytesIO(await resp.read())

                    filename = url.split("/")[-1].split("?")[0] or "attachment"
                    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                    return discord.File(data, filename=filename)
        except Exception:
            pass
        return url
    
    async def create_post(
        self,
        forum_id: int,
        post: dict,
        max_upload_size_mb: int = 24,
    ):
        # 1) Get forum channel
        forum = self.bot.get_channel(forum_id)
        if not isinstance(forum, discord.ForumChannel):
            logging.error(f"頻道 ID {forum_id} 不是論壇頻道 (ForumChannel)。")
            return None
        
        # 2) Fetch data
        url = post.get("url", "")
        title = post.get("title", "無標題")
        content = post.get("content", "")
        timestamp_obj = post.get("timestamp") # 假設傳入的是 datetime 物件
        tags = post.get("tags", [])
        image_urls = post.get("images_url", [])
        file_urls = post.get("files_url", [])

        # 3) Download files and images
        upload_files = []
        large_file_links = []
        async with aiohttp.ClientSession() as session:
            for u in (image_urls[:10] + file_urls):
                file_obj = await self._smart_download(session, u, max_upload_size_mb)
                if isinstance(file_obj, discord.File):
                    if len(upload_files) < 10:
                        upload_files.append(file_obj)
                    else:
                        large_file_links.append(u)
                elif isinstance(file_obj, str):
                    large_file_links.append(file_obj)
        
        # 4) New Content
        # Discord Timestamp: <t:秒數:F>
        discord_ts = ""
        if hasattr(timestamp_obj, 'timestamp'):
            discord_ts = f"<t:{int(timestamp_obj.timestamp())}:F>"
        else:
            discord_ts = str(timestamp_obj)

        new_content = (
            f"{content[:1800]}\n\n"
            f"{'='*30}\n"
            f"📌 原文連結：{url}\n📅 發文時間：{discord_ts}"
        )

        if large_file_links:
            new_content += "\n📂 附加檔案連結：\n" + "\n".join([f"- {link}" for link in large_file_links])

        # 5) tags
        applied_tags = []
        for tag_id in tags:
            tag = discord.utils.get(forum.available_tags, name=tag_id) 
            if tag: 
                applied_tags.append(tag)
            else:
                if len(forum.available_tags) + len(applied_tags) < 20:
                    try:
                        new_tag = await forum.create_tag(name=tag_id, moderated=False)
                        applied_tags.append(new_tag)
                    except Exception as e:
                        log.error(f"無法建立新標籤 '{tag_id}'：{e}")

        # 6) Post thread
        try:
            result = await forum.create_thread(
                name=title[:100], 
                content=new_content[:2000],
                applied_tags=applied_tags,
                files=upload_files,
                reason="自動發文"
            )

            log.info(f"在 {forum.name} 發佈新貼文: {result.thread.name} (ID: {result.thread.id})")
            return result.thread.id 
        except Exception as e:
            log.error(f"在 {forum.name} 發佈貼文失敗: {e}")
            return None
    
    def is_owner():
        async def predicate(inter: discord.Interaction):
            return await inter.client.is_owner(inter.user)
        return app_commands.check(predicate)

    @app_commands.command(name="add_forum", description="新增發佈新聞用的論壇頻道")
    @app_commands.checks.has_permissions(administrator=True) # 建議改用管理員權限檢查
    async def add_forum(self, interaction: discord.Interaction, forum_channel: discord.ForumChannel):
        # 1. 第一時間告訴 Discord：我收到了，請等我處理 (解決 3 秒超時問題)
        # ephemeral=True 表示只有執行者看得到「思考中」的訊息
        await interaction.response.defer(ephemeral=True)

        # 2. 檢查頻道型別
        if not isinstance(forum_channel, discord.ForumChannel):
            return await interaction.followup.send(f"頻道 {forum_channel.name} 不是論壇頻道。")

        # 3. 執行資料庫操作 (現在你有 15 分鐘可以慢慢跑)
        try:
            # 獲取 Scheduler 的鎖，確保資料庫寫入不衝突
            scheduler_cog = self.bot.get_cog("Scheduler")
            async with scheduler_cog._lock:
                with sqlite3.connect("data.db") as conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    cursor = conn.cursor()

                    # 檢查重複
                    cursor.execute("SELECT 1 FROM registered_forum WHERE channel_id = ?", (forum_channel.id,))
                    if cursor.fetchone():
                        return await interaction.followup.send(f"頻道 {forum_channel.name} 已在清單中。")

                    # 插入頻道
                    cursor.execute("INSERT INTO registered_forum (channel_id) VALUES (?)", (forum_channel.id,))
                    
                    # 同步現有貼文 (這就是原本會超時的重活)
                    cursor.execute("""
                        INSERT OR IGNORE INTO repost (forum_channel_id, post_id)
                        SELECT ?, post_id FROM posted_news
                    """, (forum_channel.id,))
                    
                    conn.commit()

            # 4. 更新記憶體清單
            if hasattr(self, "forum_channel_list"):
                self.forum_channel_list.append(forum_channel.id)

            # 5. 處理完成後，使用 followup 發送正式成功訊息
            log.info(f"新增論壇頻道 {forum_channel.name} (ID: {forum_channel.id}) 並同步現有貼文任務。")
            await interaction.followup.send(f"已成功新增頻道 **{forum_channel.name}** 並同步現有貼文任務。")

        except Exception as e:
            log.error(f"add_forum 失敗: {e}")
            # 出錯也要告訴使用者
            await interaction.followup.send(f"新增過程中發生錯誤: {e}")

    @app_commands.command(name="remove_forum", description="移除發佈新聞用的論壇頻道")
    @app_commands.checks.has_permissions(administrator=True) # 建議改用管理員權限檢查
    async def remove_forum(self, interaction: discord.Interaction, forum_channel: discord.ForumChannel):
        await interaction.response.defer(ephemeral=True)

        try:
            scheduler_cog = self.bot.get_cog("Scheduler")
            async with scheduler_cog._lock:
                with sqlite3.connect("data.db") as conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    cursor = conn.cursor()

                    cursor.execute("DELETE FROM registered_forum WHERE channel_id = ?", (forum_channel.id,))
                    cursor.execute("DELETE FROM repost WHERE forum_channel_id = ?", (forum_channel.id,))
                    conn.commit()

            if hasattr(self, "forum_channel_list"):
                self.forum_channel_list.remove(forum_channel.id)

            log.info(f"移除論壇頻道 {forum_channel.name} (ID: {forum_channel.id})。")
            await interaction.followup.send(f"已成功移除頻道 **{forum_channel.name}**。")

        except Exception as e:
            log.error(f"remove_forum 失敗: {e}")
            await interaction.followup.send(f"移除過程中發生錯誤: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Forum(bot))