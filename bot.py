import os
import logging
import discord
import asyncio
import argparse

import utils.db_util as db

from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands
from utils.log_util import setup_logging

log = logging.getLogger(__name__)

def setup_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NTNU CSIE News Discord Bot")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    return parser

async def main_loop():
    load_dotenv()

    dc_token = os.getenv("DISCORD_TOKEN")
    # test_guild_id = int(os.getenv("TEST_GUILD_ID"))
    # test_guild_obj = discord.Object(id=test_guild_id)

    # bot settings
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="$", intents=intents)

    @bot.event
    async def on_ready():
        log.info(f'Bot logged in as {bot.user} (ID: {bot.user.id})')
        try:
            # 1) 同步到 Discord 全域指令，可能需要一段時間才會生效
            synced = await bot.tree.sync()

            # # 2) 將全域指令鏡射到測試伺服器，立即可用
            # bot.tree.copy_global_to(guild=test_guild_obj)
            # synced = await bot.tree.sync(guild=test_guild_obj)

            log.info(f'Synced {len(synced)} commands.')
        except Exception as e:
            log.error(f"Failed to sync commands: {e}")


    def slash_is_owner():
        async def predicate(inter: discord.Interaction) -> bool:
            return await inter.client.is_owner(inter.user)
        return app_commands.check(predicate)

    @bot.tree.command(name="load", description="[管理員] 載入特定功能模組")
    @slash_is_owner()
    async def load(interaction: discord.Interaction, cog: str):
        await bot.load_extension(f"cogs.{cog}")
        # await bot.tree.sync(guild=test_guild_obj)
        await interaction.response.send_message(f"[Info] 成功載入 \033[1m{cog}\033[0m")

    @bot.tree.command(name="unload", description="[管理員] 卸載特定功能模組")
    @slash_is_owner()
    async def unload(interaction: discord.Interaction, cog: str):
        await bot.unload_extension(f"cogs.{cog}")
        # await bot.tree.sync(guild=test_guild_obj)
        await interaction.response.send_message(f"[Info] 成功卸載 \033[1m{cog}\033[0m")

    @bot.tree.command(name="reload", description="[管理員] 重新載入特定功能模組")
    @slash_is_owner()
    async def reload(interaction: discord.Interaction, cog: str):
        await bot.reload_extension(f"cogs.{cog}")
        # await bot.tree.sync(guild=test_guild_obj)
        await interaction.response.send_message(f"[Info] 成功重新載入 \033[1m{cog}\033[0m")

    # Load cogs
    for filename in os.listdir("./cogs"):
        if filename == ".DS_Store" or filename == "__pycache__" or filename.startswith("_"):
            continue
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                log.info(f"Loaded cog: \033[1m{filename}\033[0m")
            except Exception as e:
                log.error(f"Failed to load cog \033[1m{filename}\033[0m: {e}")

    # Start bot
    while True:
        try:
            await bot.start(dc_token)
        except (discord.ConnectionClosed, discord.GatewayNotFound, discord.InvalidSession, discord.HTTPException) as e:
            log.error(f"Bot disconnected with error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            await bot.close()
            break

def main():
    # parser
    parser = setup_arg_parser()
    args = parser.parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    
    # logging system
    os.makedirs("logs", exist_ok=True)
    setup_logging(log_level)

    # Initialize database
    db.init_db()

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log.info("Bot shutting down.")


if __name__ == "__main__":
    main()