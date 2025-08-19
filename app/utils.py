from typing import Optional, Dict, Any

from .supabase_client import get_supabase
from datetime import datetime, timedelta


def user_is_admin(username: Optional[str]) -> bool:
    if not username:
        return False
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("admin")
            .select("tg")
            .eq("tg", tg_username)
            .limit(1)
            .execute()
        )
        return bool(resp.data) and len(resp.data) > 0
    except Exception:
        return False


def format_event_text(draft: Dict[str, Any]) -> str:
    return (
        "📋 Черновик мероприятия:\n"
        f"Название: {draft.get('title') or '(не задано)'}\n"
        f"Описание: {draft.get('description') or '(не задано)'}\n"
        f"Настолки: {draft.get('board_games') or '(не выбрано)'}\n"
        f"Дата и время: {draft.get('datetime') or '(не задано)'}\n"
        f"Ответственные: {draft.get('responsible') or '(не назначены)'}\n"
        f"Количество участников: {draft.get('quantity') or '(не задано)'}"
    )


def format_event_text_without_photo(draft: Dict[str, Any]) -> str:
    return (
        "📋 Черновик мероприятия:\n"
        f"Название: {draft.get('title') or '(не задано)'}\n"
        f"Описание: {draft.get('description') or '(не задано)'}\n"
        f"Картинка: {draft.get('photo') or '(не задано)'}\n"
        f"Настолки: {draft.get('board_games') or '(не выбрано)'}\n"
        f"Дата и время: {draft.get('datetime') or '(не задано)'}\n"
        f"Ответственные: {draft.get('responsible') or '(не назначены)'}\n"
        f"Количество участников: {draft.get('quantity') or '(не задано)'}"
    )


def draft_required_keys() -> list[str]:
    return [
        "title",
        "description",
        "photo",
        "board_games",
        "datetime",
        "responsible",
        "quantity",
    ]


def ensure_draft_keys(draft: Dict[str, Any]) -> Dict[str, Any]:
    for key in draft_required_keys():
        draft.setdefault(key, None)
    return draft


def draft_missing_fields(draft: Dict[str, Any]) -> list[str]:
    def is_filled(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        return True

    missing: list[str] = []
    for key in draft_required_keys():
        if not is_filled(draft.get(key)):
            missing.append(key)
    return missing


def ensure_user_exists(username: Optional[str], chat_id: Optional[int] = None) -> bool:
    """Убеждается, что пользователь существует в базе данных"""
    if not username:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # Проверяем, существует ли пользователь
        resp = (
            supabase
            .table("users")
            .select("id")
            .eq("tg_username", tg_username)
            .limit(1)
            .execute()
        )
        
        if resp.data and len(resp.data) > 0:
            # Пользователь существует, обновляем chat_id если он передан
            if chat_id is not None:
                supabase.table("users").update({"chat_id": chat_id}).eq("tg_username", tg_username).execute()
            return True
        else:
            # Пользователь не существует, создаем его
            user_data = {"tg_username": tg_username}
            if chat_id is not None:
                user_data["chat_id"] = chat_id
            
            supabase.table("users").insert(user_data).execute()
            return True
    except Exception as e:
        print(f"ERROR ensuring user exists: {e}")
        return False


def is_user_registered_for_event(username: Optional[str], event_id: int) -> bool:
    """Проверяет, зарегистрирован ли пользователь на мероприятие"""
    if not username or not event_id:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_registrations")
            .select("id")
            .eq("user_tg_username", tg_username)
            .eq("event_id", event_id)
            .eq("status", "registered")
            .limit(1)
            .execute()
        )
        return bool(resp.data) and len(resp.data) > 0
    except Exception as e:
        print(f"ERROR checking registration: {e}")
        return False


def register_user_for_event(username: Optional[str], event_id: int) -> bool:
    """Регистрирует пользователя на мероприятие"""
    if not username or not event_id:
        return False
    
    # Убеждаемся, что пользователь существует
    if not ensure_user_exists(username):
        return False
    
    # Проверяем, не находится ли пользователь в черном списке
    if is_user_in_event_blacklist(event_id, username):
        return False
    
    # Проверяем, не зарегистрирован ли уже
    if is_user_registered_for_event(username, event_id):
        return False
    
    # Проверяем, не заполнено ли мероприятие
    if is_event_full(event_id):
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # Проверяем, есть ли уже запись (возможно, отменённая)
        existing_resp = (
            supabase
            .table("event_registrations")
            .select("id, status")
            .eq("user_tg_username", tg_username)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        
        if existing_resp.data and len(existing_resp.data) > 0:
            # Запись уже существует, обновляем статус
            existing_record = existing_resp.data[0]
            supabase.table("event_registrations").update({
                "status": "registered",
                "registration_date": "NOW()"
            }).eq("id", existing_record["id"]).execute()
        else:
            # Создаём новую запись
            supabase.table("event_registrations").insert({
                "user_tg_username": tg_username,
                "event_id": event_id,
                "status": "registered"
            }).execute()
        
        return True
    except Exception as e:
        print(f"ERROR registering user: {e}")
        return False


def unregister_user_from_event(username: Optional[str], event_id: int) -> bool:
    """Отменяет регистрацию пользователя на мероприятие"""
    if not username or not event_id:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # Проверяем, есть ли активная регистрация
        existing_resp = (
            supabase
            .table("event_registrations")
            .select("id, status")
            .eq("user_tg_username", tg_username)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        
        if not existing_resp.data or len(existing_resp.data) == 0:
            # Записи нет вообще
            return False
        
        existing_record = existing_resp.data[0]
        if existing_record["status"] == "cancelled":
            # Уже отменено
            return False
        
        # Отменяем регистрацию
        supabase.table("event_registrations").update({
            "status": "cancelled"
        }).eq("id", existing_record["id"]).execute()
        
        return True
    except Exception as e:
        print(f"ERROR unregistering user: {e}")
        return False


def get_user_registrations(username: Optional[str]) -> list[Dict[str, Any]]:
    """Получает список мероприятий, на которые зарегистрирован пользователь"""
    if not username:
        return []
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_registrations")
            .select("*, events(*)")
            .eq("user_tg_username", tg_username)
            .eq("status", "registered")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"ERROR getting user registrations: {e}")
        return []


def get_user_chat_id(username: Optional[str]) -> Optional[int]:
    """Получает chat_id пользователя из базы данных"""
    if not username:
        return None
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("users")
            .select("chat_id")
            .eq("tg_username", tg_username)
            .limit(1)
            .execute()
        )
        if resp.data and len(resp.data) > 0:
            return resp.data[0].get("chat_id")
        return None
    except Exception as e:
        print(f"ERROR getting user chat_id: {e}")
        return None


def get_event_registrations(event_id: int) -> list[Dict[str, Any]]:
    """Получает список зарегистрированных пользователей на мероприятие"""
    if not event_id:
        return []
    
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_registrations")
            .select("*, users(*)")
            .eq("event_id", event_id)
            .eq("status", "registered")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"ERROR getting event registrations: {e}")
        return []


def get_event_available_slots(event_id: int) -> tuple[int, int]:
    """Получает количество доступных мест на мероприятии
    Возвращает: (занято мест, максимальное количество мест)"""
    if not event_id:
        return (0, 0)
    
    supabase = get_supabase()
    try:
        # Получаем информацию о мероприятии
        event_resp = (
            supabase
            .table("events")
            .select("quantity")
            .eq("id", event_id)
            .limit(1)
            .execute()
        )
        
        if not event_resp.data:
            return (0, 0)
        
        max_slots = event_resp.data[0].get("quantity", 0)
        if not max_slots:
            return (0, 0)  # Если количество не ограничено
        
        # Получаем количество зарегистрированных участников
        registrations_resp = (
            supabase
            .table("event_registrations")
            .select("id", count="exact")
            .eq("event_id", event_id)
            .eq("status", "registered")
            .execute()
        )
        
        occupied_slots = registrations_resp.count or 0
        return (occupied_slots, max_slots)
        
    except Exception as e:
        print(f"ERROR getting event available slots: {e}")
        return (0, 0)


def is_event_full(event_id: int) -> bool:
    """Проверяет, заполнено ли мероприятие"""
    occupied, max_slots = get_event_available_slots(event_id)
    return max_slots > 0 and occupied >= max_slots


def get_event_available_slots_count(event_id: int) -> int:
    """Получает количество оставшихся свободных мест"""
    occupied, max_slots = get_event_available_slots(event_id)
    if max_slots == 0:
        return -1  # Неограниченное количество
    return max(0, max_slots - occupied)


def is_user_on_waitlist(username: Optional[str], event_id: int) -> bool:
    """Проверяет, находится ли пользователь в очереди ожидания"""
    if not username or not event_id:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_registrations")
            .select("id")
            .eq("user_tg_username", tg_username)
            .eq("event_id", event_id)
            .eq("status", "waitlist")
            .limit(1)
            .execute()
        )
        return bool(resp.data) and len(resp.data) > 0
    except Exception as e:
        print(f"ERROR checking waitlist: {e}")
        return False


def add_user_to_waitlist(username: Optional[str], event_id: int) -> bool:
    """Добавляет пользователя в очередь ожидания"""
    if not username or not event_id:
        return False
    
    # Убеждаемся, что пользователь существует
    if not ensure_user_exists(username):
        return False
    
    # Проверяем, не находится ли пользователь в черном списке
    if is_user_in_event_blacklist(event_id, username):
        return False
    
    # Проверяем, не зарегистрирован ли уже или не в очереди
    if is_user_registered_for_event(username, event_id) or is_user_on_waitlist(username, event_id):
        return False
    
    # Проверяем, что мероприятие действительно заполнено
    if not is_event_full(event_id):
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # Проверяем, есть ли уже запись (возможно, отменённая)
        existing_resp = (
            supabase
            .table("event_registrations")
            .select("id, status")
            .eq("user_tg_username", tg_username)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        
        if existing_resp.data and len(existing_resp.data) > 0:
            # Запись уже существует, обновляем статус
            existing_record = existing_resp.data[0]
            supabase.table("event_registrations").update({
                "status": "waitlist",
                "registration_date": "NOW()"
            }).eq("id", existing_record["id"]).execute()
        else:
            # Создаём новую запись
            supabase.table("event_registrations").insert({
                "user_tg_username": tg_username,
                "event_id": event_id,
                "status": "waitlist"
            }).execute()
        
        return True
    except Exception as e:
        print(f"ERROR adding to waitlist: {e}")
        return False


def remove_user_from_waitlist(username: Optional[str], event_id: int) -> bool:
    """Удаляет пользователя из очереди ожидания"""
    if not username or not event_id:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # Проверяем, есть ли запись в очереди
        existing_resp = (
            supabase
            .table("event_registrations")
            .select("id, status")
            .eq("user_tg_username", tg_username)
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        
        if not existing_resp.data or len(existing_resp.data) == 0:
            return False
        
        existing_record = existing_resp.data[0]
        if existing_record["status"] != "waitlist":
            return False
        
        # Удаляем из очереди
        supabase.table("event_registrations").update({
            "status": "cancelled"
        }).eq("id", existing_record["id"]).execute()
        
        return True
    except Exception as e:
        print(f"ERROR removing from waitlist: {e}")
        return False


def get_waitlist_position(username: Optional[str], event_id: int) -> int:
    """Получает позицию пользователя в очереди ожидания"""
    if not username or not event_id:
        return -1
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # Получаем всех пользователей в очереди для этого мероприятия
        waitlist_resp = (
            supabase
            .table("event_registrations")
            .select("user_tg_username, registration_date")
            .eq("event_id", event_id)
            .eq("status", "waitlist")
            .order("registration_date", desc=False)
            .execute()
        )
        
        if not waitlist_resp.data:
            return -1
        
        # Ищем позицию пользователя
        for i, record in enumerate(waitlist_resp.data):
            if record["user_tg_username"] == tg_username:
                return i + 1  # Позиция начинается с 1
        
        return -1
    except Exception as e:
        print(f"ERROR getting waitlist position: {e}")
        return -1


def get_event_participants(event_id: int) -> list:
    """Получает список всех участников мероприятия (зарегистрированных и в очереди)"""
    if not event_id:
        return []
    
    supabase = get_supabase()
    try:
        # Получаем всех зарегистрированных участников
        registered_resp = (
            supabase
            .table("event_registrations")
            .select("user_tg_username, registration_date, status")
            .eq("event_id", event_id)
            .in_("status", ["registered", "waitlist"])
            .order("registration_date", desc=False)
            .execute()
        )
        
        participants = []
        if registered_resp.data:
            for record in registered_resp.data:
                participants.append({
                    "username": record["user_tg_username"],
                    "status": record["status"],
                    "registration_date": record["registration_date"]
                })
        
        return participants
    except Exception as e:
        print(f"ERROR getting event participants: {e}")
        return []


def get_user_info(username: str) -> dict:
    """Получает информацию о пользователе"""
    if not username:
        return {}
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("users")
            .select("id, tg_username, chat_id, created_at")
            .eq("tg_username", tg_username)
            .limit(1)
            .execute()
        )
        
        if resp.data and len(resp.data) > 0:
            return resp.data[0]
        return {}
    except Exception as e:
        print(f"ERROR getting user info: {e}")
        return {}


def get_user_registrations_count(username: str) -> int:
    """Получает количество мероприятий, на которые зарегистрирован пользователь"""
    if not username:
        return 0


def get_user_events_history(username: str) -> list[Dict[str, Any]]:
    """История мероприятий пользователя (по таблице event_registrations)"""
    if not username:
        return []
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_registrations")
            .select("status, registration_date, events(*)")
            .eq("user_tg_username", tg_username)
            .order("registration_date", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"ERROR get_user_events_history: {e}")
        return []
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_registrations")
            .select("id", count="exact")
            .eq("user_tg_username", tg_username)
            .eq("status", "registered")
            .execute()
        )
        
        return resp.count or 0
    except Exception as e:
        print(f"ERROR getting user registrations count: {e}")
        return 0


def is_user_in_event_blacklist(event_id: int, username: str) -> bool:
    """Проверяет, находится ли пользователь в черном списке мероприятия"""
    if not event_id or not username:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_blacklist")
            .select("id")
            .eq("event_id", event_id)
            .eq("user_tg_username", tg_username)
            .limit(1)
            .execute()
        )
        
        return bool(resp.data) and len(resp.data) > 0
    except Exception as e:
        print(f"ERROR checking blacklist: {e}")
        return False


def add_user_to_event_blacklist(event_id: int, username: str, added_by: str, reason: str = None) -> bool:
    """Добавляет пользователя в черный список мероприятия"""
    if not event_id or not username or not added_by:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    added_by_username = added_by if added_by.startswith("@") else f"@{added_by}"
    
    supabase = get_supabase()
    try:
        # Проверяем, не находится ли уже пользователь в черном списке
        if is_user_in_event_blacklist(event_id, tg_username):
            return True  # Уже в черном списке
        
        # Гарантируем, что добавляющий админ существует в таблице users (для FK)
        try:
            ensure_user_exists(added_by_username)
        except Exception:
            pass
        
        # Добавляем в черный список
        resp = (
            supabase
            .table("event_blacklist")
            .insert({
                "event_id": event_id,
                "user_tg_username": tg_username,
                "added_by_tg_username": added_by_username,
                "reason": reason
            })
            .execute()
        )
        
        return bool(resp.data) and len(resp.data) > 0
    except Exception as e:
        print(f"ERROR adding to blacklist: {e}")
        return False


def remove_user_from_event_blacklist(event_id: int, username: str) -> bool:
    """Удаляет пользователя из черного списка мероприятия"""
    if not event_id or not username:
        return False
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_blacklist")
            .delete()
            .eq("event_id", event_id)
            .eq("user_tg_username", tg_username)
            .execute()
        )
        
        return bool(resp.data) and len(resp.data) > 0
    except Exception as e:
        print(f"ERROR removing from blacklist: {e}")
        return False


def get_event_blacklist(event_id: int) -> list:
    """Получает список пользователей в черном списке мероприятия"""
    if not event_id:
        return []
    
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("event_blacklist")
            .select("user_tg_username, added_by_tg_username, added_at, reason")
            .eq("event_id", event_id)
            .order("added_at", desc=True)
            .execute()
        )
        
        blacklist = []
        if resp.data:
            for record in resp.data:
                blacklist.append({
                    "username": record["user_tg_username"],
                    "added_by": record["added_by_tg_username"],
                    "added_at": record["added_at"],
                    "reason": record["reason"]
                })
        
        return blacklist
    except Exception as e:
        print(f"ERROR getting event blacklist: {e}")
        return []


def get_user_chat_id(username: str) -> Optional[int]:
    """Получает chat_id пользователя для отправки уведомлений"""
    if not username:
        return None
    
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("users")
            .select("chat_id")
            .eq("tg_username", tg_username)
            .limit(1)
            .execute()
        )
        
        if resp.data and len(resp.data) > 0:
            return resp.data[0].get("chat_id")
        return None
    except Exception as e:
        print(f"ERROR getting user chat_id: {e}")
        return None


def get_all_users() -> list[Dict[str, Any]]:
    """Все пользователи бота"""
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("users")
            .select("tg_username, chat_id, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"ERROR get_all_users: {e}")
        return []


def get_all_admins() -> list[Dict[str, Any]]:
    supabase = get_supabase()
    try:
        resp = supabase.table("admin").select("tg").execute()
        return resp.data or []
    except Exception as e:
        print(f"ERROR get_all_admins: {e}")
        return []


def add_user_to_global_blacklist(username: str) -> bool:
    """Добаляет пользователя в глобальный ЧС (запрет для всех мероприятий)"""
    if not username:
        return False
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # ensure user exists for FK
        ensure_user_exists(tg_username)
        supabase.table("global_blacklist").insert({
            "user_tg_username": tg_username
        }).execute()
        return True
    except Exception as e:
        print(f"ERROR add_user_to_global_blacklist: {e}")
        return False


def remove_user_from_global_blacklist(username: str) -> bool:
    if not username:
        return False
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        supabase.table("global_blacklist").delete().eq("user_tg_username", tg_username).execute()
        return True
    except Exception as e:
        print(f"ERROR remove_user_from_global_blacklist: {e}")
        return False


def get_global_blacklist() -> list[Dict[str, Any]]:
    supabase = get_supabase()
    try:
        resp = supabase.table("global_blacklist").select("user_tg_username, added_at").order("added_at", desc=True).execute()
        return resp.data or []
    except Exception as e:
        print(f"ERROR get_global_blacklist: {e}")
        return []


def get_admin_past_events(admin_tg: str) -> list[Dict[str, Any]]:
    """Возвращает прошедшие мероприятия, где указанный админ фигурирует в поле responsible"""
    if not admin_tg:
        return []


def format_game_text(draft: Dict[str, Any]) -> str:
    return (
        "🎲 Черновик игры:\n"
        f"Название: {draft.get('title') or '(не задано)'}\n"
        f"Правила: {draft.get('rules') or '(не заданы)'}"
    )


def format_game_text_without_photo(draft: Dict[str, Any]) -> str:
    return (
        "🎲 Черновик игры:\n"
        f"Название: {draft.get('title') or '(не задано)'}\n"
        f"Картинка: {draft.get('photo') or '(не задано)'}\n"
        f"Правила: {draft.get('rules') or '(не заданы)'}"
    )


def parse_event_datetime(value: str) -> Optional[str]:
    """Парсит строку даты и времени и возвращает в формате ISO 'YYYY-MM-DD HH:MM'.
    Поддерживаемые форматы ввода:
    - 'DD.MM.YYYY HH:MM' (например, 25.08.2025 18:30)
    - 'DD/MM/YYYY HH:MM'
    - 'YYYY-MM-DD HH:MM'
    - 'DD.MM.YYYY' (без времени -> отклоняется)
    Возвращает None, если распарсить не удалось или нет времени.
    """
    if not value:
        return None
    text = value.strip()
    # Набор форматов с временем
    formats_with_time = [
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M",
    ]
    for fmt in formats_with_time:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    # Попытка распознать без времени — считаем ошибкой (требуем время)
    return None


def parse_event_datetime_to_datetime(value: str) -> Optional[datetime]:
    """Парсит строку даты и времени в datetime. См. parse_event_datetime для форматов."""
    if not value:
        return None
    text = value.strip()
    formats_with_time = [
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M",
    ]
    for fmt in formats_with_time:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass
    return None


def is_future_datetime_str(iso_text: str) -> bool:
    """Проверяет, что строка в формате 'YYYY-MM-DD HH:MM' указывает на будущее время."""
    try:
        dt = datetime.strptime(iso_text, "%Y-%m-%d %H:%M")
        return dt > datetime.now()
    except Exception:
        return False


def get_events_needing_reminders() -> list[Dict[str, Any]]:
    """Возвращает мероприятия, для которых пора отправить напоминание за день/час и ещё не отправляли."""
    supabase = get_supabase()
    now = datetime.now()
    results: list[Dict[str, Any]] = []
    try:
        resp = supabase.table("events").select("*").eq("is_completed", False).eq("is_cancelled", False).execute()
        events = resp.data or []
        for e in events:
            date_text = e.get("date")
            dt = parse_event_datetime_to_datetime(date_text) if date_text else None
            if not dt:
                continue
            # 1 день
            if not e.get("reminder_1day_sent") and 0 <= (dt - now).total_seconds() <= 24*3600 + 60:
                results.append({"event": e, "type": "1day"})
            # 1 час
            if not e.get("reminder_1hour_sent") and 0 <= (dt - now).total_seconds() <= 3600 + 60:
                results.append({"event": e, "type": "1hour"})
    except Exception as ex:
        print(f"ERROR get_events_needing_reminders: {ex}")
    return results


def mark_event_reminder_sent(event_id: int, reminder_type: str) -> None:
    supabase = get_supabase()
    try:
        if reminder_type == "1day":
            supabase.table("events").update({"reminder_1day_sent": True}).eq("id", event_id).execute()
        elif reminder_type == "1hour":
            supabase.table("events").update({"reminder_1hour_sent": True}).eq("id", event_id).execute()
    except Exception as ex:
        print(f"ERROR mark_event_reminder_sent: {ex}")


def get_board_games() -> list[Dict[str, Any]]:
    supabase = get_supabase()
    try:
        resp = supabase.table("board_games").select("*").order("created_at", desc=True).execute()
        return resp.data or []
    except Exception as e:
        print(f"ERROR get_board_games: {e}")
        return []


def create_board_game(payload: Dict[str, Any]) -> bool:
    supabase = get_supabase()
    try:
        supabase.table("board_games").insert(payload).execute()
        return True
    except Exception as e:
        print(f"ERROR create_board_game: {e}")
        return False
    supabase = get_supabase()
    try:
        resp = (
            supabase
            .table("events")
            .select("*")
            .eq("is_completed", True)
            .ilike("responsible", f"%{admin_tg}%")
            .order("date", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"ERROR get_admin_past_events: {e}")
        return []


def save_event_feedback_rating(username: Optional[str], event_id: int, rating: int) -> bool:
    """Сохраняет/обновляет оценку пользователя для мероприятия (без комментария)"""
    if not username or not event_id or not (1 <= rating <= 10):
        return False
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        # Проверяем, есть ли уже отзыв
        existing = (
            supabase
            .table("event_feedback")
            .select("id")
            .eq("event_id", event_id)
            .eq("user_tg_username", tg_username)
            .limit(1)
            .execute()
        )
        if existing.data and len(existing.data) > 0:
            feedback_id = existing.data[0]["id"]
            supabase.table("event_feedback").update({
                "rating": rating
            }).eq("id", feedback_id).execute()
        else:
            supabase.table("event_feedback").insert({
                "event_id": event_id,
                "user_tg_username": tg_username,
                "rating": rating
            }).execute()
        return True
    except Exception as e:
        print(f"ERROR saving feedback rating: {e}")
        return False


def save_event_feedback_comment(username: Optional[str], event_id: int, comment: str) -> bool:
    """Сохраняет/обновляет комментарий пользователя для мероприятия"""
    if not username or not event_id:
        return False
    tg_username = username if username.startswith("@") else f"@{username}"
    supabase = get_supabase()
    try:
        existing = (
            supabase
            .table("event_feedback")
            .select("id")
            .eq("event_id", event_id)
            .eq("user_tg_username", tg_username)
            .limit(1)
            .execute()
        )
        if existing.data and len(existing.data) > 0:
            feedback_id = existing.data[0]["id"]
            supabase.table("event_feedback").update({
                "comment": comment
            }).eq("id", feedback_id).execute()
        else:
            supabase.table("event_feedback").insert({
                "event_id": event_id,
                "user_tg_username": tg_username,
                "comment": comment
            }).execute()
        return True
    except Exception as e:
        print(f"ERROR saving feedback comment: {e}")
        return False