import os
from typing import Optional

BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")


def validate_config() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Не заданы SUPABASE_URL / SUPABASE_KEY в переменных окружения")


