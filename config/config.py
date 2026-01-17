import os
import requests


# Database path
_current_file = os.path.abspath(__file__)
_config_dir = os.path.dirname(_current_file)
BASE_DIR = os.path.dirname(_config_dir)
DB_PATH = os.path.join(BASE_DIR, "data", "data.db")

# Update interval in minutes
UPDATE_MINUTES = 30

# Web scraping config
BASE_URL = "https://www.csie.ntnu.edu.tw"
WP_API_BASE = "https://www.csie.ntnu.edu.tw/index.php/wp-json/wp/v2"

CATEGORY_URLS = [
    "https://www.csie.ntnu.edu.tw/index.php/category/news/competition/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/announcement/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/seminar/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/enrollment/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/honor-roll/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/scholarship/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/intern/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/recruitment/",
    "https://www.csie.ntnu.edu.tw/index.php/category/news/1/", 
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
    "Connection": "keep-alive",
})