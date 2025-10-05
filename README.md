# NTNUCSIE news
![Discord](https://img.shields.io/badge/Discord-7289DA.svg?logo=discord&logoColor=white&style=for-the-badge) ![Python](https://img.shields.io/badge/Python-14354C.svg?logo=python&logoColor=white&style=for-the-badge)  
  
This is a Discord bot to repost the news from [NTNU CSIE official website](https://www.csie.ntnu.edu.tw/index.php/news/).  

## 🖥️ Requirements 
To run the program successfully, please check the following:  
- Python 3.13+/ uv. 

## Run
### Environment setting
Please set a `.env` file for the repo, you can run following instruction and fill information in terminal to set `.env`

```sh
echo 'DISCORD_TOKEN=<your_discord_bot_token>
TEST_GUILD_ID=<test_guild_id>
FORUM_CHANNEL_ID=<test_forum_channel_id>' > .env
```

### Development
Use **uv** to install dependencies the backend app need:

```sh
uv sync
uv run main.py
```
