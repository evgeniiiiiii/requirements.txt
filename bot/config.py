import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

raw_url = os.getenv("DATABASE_URL", "")
DATABASE_URL = raw_url.replace("postgresql://", "postgresql+asyncpg://")
