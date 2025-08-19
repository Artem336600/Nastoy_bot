from supabase import Client, create_client

from .config import SUPABASE_URL, SUPABASE_KEY


def get_supabase() -> Client:
    assert SUPABASE_URL and SUPABASE_KEY
    return create_client(SUPABASE_URL, SUPABASE_KEY)


