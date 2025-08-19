from supabase import Client, create_client
from typing import Optional

from .config import SUPABASE_URL, SUPABASE_KEY

_client: Optional[Client] = None


def get_supabase() -> Client:
    global _client
    assert SUPABASE_URL and SUPABASE_KEY
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


