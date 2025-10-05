import os

import discord
from discord.ext import commands

class Forum(commands.Cog):
    def __init__(self, bot: commands.Bot, forum_channel_id: int):
        self.bot = bot
        self.forum_channel_id = forum_channel_id

    async def _get_forum(self) -> discord.ForumChannel:
        ch = self.bot.get_channel(self.forum_channel_id) or await self.bot.fetch_channel(self.forum_channel_id)
        if not isinstance(ch, discord.ForumChannel):
            raise RuntimeError(f"Channel {self.forum_channel_id} 不是 ForumChannel。")
        return ch

    async def post_forum(
        self,
        title: str,
        content: str,
        tags: list[int] = None,
    ):
        forum = await self._get_forum()

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

async def setup(bot: commands.Bot):
    forum_id = int(os.getenv("FORUM_CHANNEL_ID"))
    await bot.add_cog(Forum(bot, forum_id))