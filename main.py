import os
import logging
import discord
import asyncio

from discord.ext import commands
from dotenv import load_dotenv

# logging settings
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

async def main_loop():
    load_dotenv()

    dc_token = os.getenv("DISCORD_TOKEN")
    test_guild_id = int(os.getenv("TEST_GUILD_ID"))
    test_guild_obj = discord.Object(id=test_guild_id)

    # bot settings
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="$", intents=intents)

    @bot.event
    async def on_ready():
        print(f'We have logged in as {bot.user}')
        try:
            synced = await bot.tree.sync()
            await bot.tree.sync(guild=test_guild_obj)
            print(f'Synced {len(synced)} command(s)')
        except Exception as e:
            print(e)

    @bot.tree.command(name="load", description="Load a cog")
    @commands.is_owner()
    async def load(interaction: discord.Interaction, cog: str):
        await bot.load_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"Loaded {cog} cog.")

    @bot.tree.command(name="unload", description="Unload a cog")
    @commands.is_owner()
    async def unload(interaction: discord.Interaction, cog: str):
        await bot.unload_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"Unloaded {cog} cog.")

    @bot.tree.command(name="reload", description="Reload a cog")
    @commands.is_owner()
    async def reload(interaction: discord.Interaction, cog: str):
        await bot.reload_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"Reloaded {cog} cog.")

    # Load cogs
    for filename in os.listdir("./cogs"):
        if filename == ".DS_Store" or filename == "__pycache__" or filename.startswith("_"):
            continue
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded \033[1m{filename}\033[0m cog.")
            except Exception as e:
                print(f"Failed to load cog {filename}: {e}")

    # Start bot
    while True:
        try:
            await bot.start(dc_token)
        except (discord.ConnectionClosed, discord.GatewayNotFound, discord.InvalidSession, discord.HTTPException) as e:
            print(f"Connection error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            await bot.close()
            break

def main():
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Bot shutting down.")


if __name__ == "__main__":
    asyncio.run(main())