import discord
import json

from discord.ext import commands
from discord import app_commands

CONFIG_FILE = "data/forum_config.json"

class Forum(commands.Cog):
    def __init__(self, bot: commands.Bot, forum_channel_ids: list[int] = None):
        self.bot = bot
        self.forum_channel_list = forum_channel_ids or []

    # async def _get_forum(self) -> discord.ForumChannel:
    #     ch = self.bot.get_channel(self.forum_channel_id) or await self.bot.fetch_channel(self.forum_channel_id)
    #     if not isinstance(ch, discord.ForumChannel):
    #         raise RuntimeError(f"Channel {self.forum_channel_id} 不是 ForumChannel。")
    #     return ch

    async def get_forum_list(self) -> list[discord.ForumChannel]:
        forum_list = []
        for forum_id in self.forum_channel_list:
            ch = self.bot.get_channel(forum_id) or await self.bot.fetch_channel(forum_id)
            if not isinstance(ch, discord.ForumChannel):
                print(f"[Error] Channel {forum_id} 不是 ForumChannel。")
                continue
            forum_list.append(ch)
        return forum_list

    async def post_forum(
        self,
        title: str,
        content: str,
        tags: list[int] = None,
        posted_list: list[int] = None
    ) -> list[int]:
        forum_list = await self.get_forum_list()

        if not forum_list:
            print("[Error] 沒有可用的 ForumChannel。")
            return
        
        for forum in forum_list:
            if forum.id in (posted_list or []):
                print(f"[Info] 貼文已在 {forum.name} 發佈過，跳過。")
                continue

            # tags
            applied_tags = []
            if tags:
                for tag_id in tags:
                    tag = discord.utils.get(forum.available_tags, id=tag_id)
                    if tag:
                        applied_tags.append(tag)

            # 建立論壇「貼文」＝在該 ForumChannel 建立 thread，並送出首則訊息
            thread, first_message = await forum.create_thread(
                name=title,
                content=content,
                applied_tags=applied_tags,
                reason="自動發文"
            )

            posted_list.append(forum.id)

            print(f"已在 {forum.name} 建立新貼文: {thread.name} (ID: {thread.id})")

        return posted_list
    
    def is_owner():
        async def predicate(inter: discord.Interaction):
            return await inter.client.is_owner(inter.user)
        return app_commands.check(predicate)

    @app_commands.command(name = "add_forum", description = "新增發佈新聞用的論壇頻道")
    @commands.is_owner()
    @app_commands.describe(forum_channel = "論壇頻道")
    async def add_forum(self, interaction: discord.Interaction, forum_channel: discord.ForumChannel):
        '''
        新增發佈新聞用的論壇頻道，請確定該頻道為 ForumChannel。
        目前支援多個論壇頻道，發佈時會自動跳過已發佈過的頻道。
        '''
        if forum_channel.id in self.forum_channel_list:
            await interaction.response.send_message(f"頻道 {forum_channel.name} 已在發佈清單中。", ephemeral=True)
            return

        self.forum_channel_list.append(forum_channel.id)

        # save to config file
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"registered_forum": self.forum_channel_list}, f, ensure_ascii=False, indent=4)
    
        await interaction.response.send_message(f"已新增頻道 {forum_channel.name} 至發佈清單。", ephemeral=True)

async def setup(bot: commands.Bot):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    forum_id = config.get("registered_forum", [])

    await bot.add_cog(Forum(bot, forum_id))