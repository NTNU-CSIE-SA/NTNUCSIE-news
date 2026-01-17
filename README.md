# NTNUCSIE news
![Discord](https://img.shields.io/badge/Discord-7289DA.svg?logo=discord&logoColor=white&style=for-the-badge)
![Python](https://img.shields.io/badge/Python-14354C.svg?logo=python&logoColor=white&style=for-the-badge)
![sqlite](https://img.shields.io/badge/sqlite-07405e.svg?logo=sqlite&logoColor=white&style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white&style=for-the-badge)  

## ✨ Overview
- Discord bot to repost the news from [NTNU CSIE official website](https://www.csie.ntnu.edu.tw/index.php/news/).  
- You can **register** your forum channels in Discord, then our Discord bot will send you the posts on the website automatically.

## 🧑‍💻 Team work
```
boyan1001: Project manager / Discord bot Design / Database / Dockerfile

RokuSennyou: Design website information scraping bot
```

## 🖥️ Requirements 
To run the program successfully, please check the following:  
- Python 3.13+/ uv. 
- Docker % docker-compose (you can also deploy by Docker)

## 🐳  Run by Docker
Please set a `.env` file for the repo, you can run following instruction and fill information in terminal to set `.env`

```sh
echo 'DISCORD_TOKEN=<your_discord_bot_token>
TEST_GUILD_ID=<test_guild_id>' > .env
```

Build and start the containers:
```sh
docker-compose up -d --build
```

## 💻 Local Development (without Docker)
Please set a `.env` file for the repo, you can run following instruction and fill information in terminal to set `.env`

```sh
echo 'DISCORD_TOKEN=<your_discord_bot_token>
TEST_GUILD_ID=<test_guild_id>' > .env
```

Use **uv** to install dependencies the backend app need:

```sh
uv sync
uv run bot.py
```

## ⚒️ Usage
Then you can use instruction `/add_forum <forum channel>` to add the forum which you want to launch posts to forum lists. The program will launch posts on it.

If you want to untrack the forum, you can use `/remove_forum <forum channel>` to remove the forum.
