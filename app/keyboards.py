from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Any, List, Optional


def build_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру для админов"""
    keyboard = [
        [KeyboardButton(text="Создать мероприятие")],
        [KeyboardButton(text="Предстоящие мероприятия")],
        [KeyboardButton(text="Прошедшие мероприятия")],
        [KeyboardButton(text="Посмотреть всех участников бота")],
        [KeyboardButton(text="Настольные игры")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_user_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру для обычных пользователей"""
    keyboard = [
        [KeyboardButton(text="Зарегистрироваться на мероприятие")],
        [KeyboardButton(text="Мои мероприятия")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_event_inline_keyboard(draft: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Создает inline клавиатуру для редактирования мероприятия"""
    keyboard = []
    
    # Функция для проверки заполненности поля
    def is_filled(value):
        return value is not None and str(value).strip() != ""
    
    # Создаем кнопки с галочками для заполненных полей
    title_mark = "✅" if is_filled(draft.get("title")) else ""
    desc_mark = "✅" if is_filled(draft.get("description")) else ""
    photo_mark = "✅" if is_filled(draft.get("photo")) else ""
    games_mark = "✅" if is_filled(draft.get("board_games")) else ""
    date_mark = "✅" if is_filled(draft.get("datetime")) else ""
    resp_mark = "✅" if is_filled(draft.get("responsible")) else ""
    qty_mark = "✅" if is_filled(draft.get("quantity")) else ""
    
    keyboard.extend([
        [InlineKeyboardButton(text=f"Название {title_mark}", callback_data="evt:title")],
        [InlineKeyboardButton(text=f"Описание {desc_mark}", callback_data="evt:description")],
        [InlineKeyboardButton(text=f"Картинка {photo_mark}", callback_data="evt:photo")],
        [InlineKeyboardButton(text=f"Настолки {games_mark}", callback_data="evt:board_games")],
        [InlineKeyboardButton(text=f"Дата и время {date_mark}", callback_data="evt:datetime")],
        [InlineKeyboardButton(text=f"Ответственные {resp_mark}", callback_data="evt:responsible")],
        [InlineKeyboardButton(text=f"Количество участников {qty_mark}", callback_data="evt:quantity")],
        [InlineKeyboardButton(text="Подтвердить", callback_data="evt:confirm")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_final_confirm_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для финального подтверждения"""
    keyboard = [
        [InlineKeyboardButton(text="Сохранить", callback_data="evt:final_confirm")],
        [InlineKeyboardButton(text="Назад", callback_data="evt:final_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_events_list_keyboard(events: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком мероприятий"""
    keyboard = []
    
    for i, event in enumerate(events):
        title = event.get("title", "Без названия")
        # Используем индекс вместо ID
        button_text = title[:30] + "..." if len(title) > 30 else title
        
        # Проверяем, завершено ли мероприятие
        is_completed = event.get("is_completed", False)
        if is_completed:
            button_text += " ✅"
        
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"event:show:{i}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_event_edit_keyboard(event: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Создает inline клавиатуру для редактирования существующего мероприятия"""
    keyboard = []
    
    # Функция для проверки заполненности поля
    def is_filled(value):
        return value is not None and str(value).strip() != ""
    
    # Создаем кнопки с галочками для заполненных полей
    title_mark = "✅" if is_filled(event.get("title")) else ""
    desc_mark = "✅" if is_filled(event.get("description")) else ""
    photo_mark = "✅" if is_filled(event.get("photo")) else ""
    games_mark = "✅" if is_filled(event.get("board_games")) else ""
    date_mark = "✅" if is_filled(event.get("date")) else ""  # Используем "date" для существующих мероприятий
    resp_mark = "✅" if is_filled(event.get("responsible")) else ""
    qty_mark = "✅" if is_filled(event.get("quantity")) else ""
    
    keyboard.extend([
        [InlineKeyboardButton(text=f"Название {title_mark}", callback_data="evt_edit:title")],
        [InlineKeyboardButton(text=f"Описание {desc_mark}", callback_data="evt_edit:description")],
        [InlineKeyboardButton(text=f"Картинка {photo_mark}", callback_data="evt_edit:photo")],
        [InlineKeyboardButton(text=f"Настолки {games_mark}", callback_data="evt_edit:board_games")],
        [InlineKeyboardButton(text=f"Дата и время {date_mark}", callback_data="evt_edit:datetime")],
        [InlineKeyboardButton(text=f"Ответственные {resp_mark}", callback_data="evt_edit:responsible")],
        [InlineKeyboardButton(text=f"Количество участников {qty_mark}", callback_data="evt_edit:quantity")],
        [InlineKeyboardButton(text="Готово", callback_data="evt_edit:confirm")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_edit_final_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Сохранить изменения", callback_data="evt_edit:final_confirm")],
        [InlineKeyboardButton(text="Назад", callback_data="evt_edit:final_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_event_management_keyboard(event_index: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру управления мероприятием для админов"""
    keyboard = [
        [InlineKeyboardButton(text="Изменить мероприятие", callback_data=f"event:edit:{event_index}")],
        [InlineKeyboardButton(text="Посмотреть участников", callback_data=f"event:participants:{event_index}")],
        [InlineKeyboardButton(text="Чёрный список", callback_data=f"event:blacklist:{event_index}")],
        [InlineKeyboardButton(text="Отправить рассылку", callback_data=f"event:broadcast:{event_index}")],
        [InlineKeyboardButton(text="Отменить мероприятие", callback_data=f"event:cancel:{event_index}")],
        [InlineKeyboardButton(text="Завершить мероприятие", callback_data=f"event:complete:{event_index}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="event:back_to_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_participants_list_keyboard(participants: List[Dict[str, Any]], event_index: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком участников мероприятия"""
    keyboard = []
    
    for i, participant in enumerate(participants):
        username = participant.get("username", "Неизвестный")
        status = participant.get("status", "registered")
        
        # Формируем текст кнопки
        if status == "registered":
            button_text = f"✅ {username}"
        elif status == "waitlist":
            button_text = f"⏳ {username} (в очереди)"
        else:
            button_text = f"❓ {username}"
        
        # Ограничиваем длину текста
        if len(button_text) > 30:
            button_text = button_text[:27] + "..."
        
        keyboard.append([InlineKeyboardButton(
            text=button_text, 
            callback_data=f"participant:show:{event_index}:{i}"
        )])
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton(
        text="⬅️ Назад к мероприятию", 
        callback_data=f"event:show:{event_index}"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_participant_info_keyboard(event_index: int, participant_index: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для информации об участнике"""
    keyboard = [
        [InlineKeyboardButton(text="💬 Написать участнику", callback_data=f"participant:message:{event_index}:{participant_index}")],
        [InlineKeyboardButton(text="🚫 Добавить в ЧС", callback_data=f"participant:blacklist:{event_index}:{participant_index}")],
        [InlineKeyboardButton(text="❌ Кикнуть", callback_data=f"participant:remove:{event_index}:{participant_index}")],
        [InlineKeyboardButton(text="⬅️ Назад к участникам", callback_data=f"event:participants:{event_index}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_contact_responsible_keyboard(event_index: int, responsibles: List[str]) -> InlineKeyboardMarkup:
    keyboard: List[List[InlineKeyboardButton]] = []
    for tg in responsibles:
        username_clean = tg.lstrip("@")
        keyboard.append([InlineKeyboardButton(text=f"🔗 Открыть профиль {tg}", url=f"https://t.me/{username_clean}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"event:show:{event_index}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_cancel_message_keyboard(event_index: int, participant_index: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для отмены отправки сообщения"""
    keyboard = [
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"participant:cancel_message:{event_index}:{participant_index}")],
        [InlineKeyboardButton(text="⬅️ Назад к участнику", callback_data=f"participant:show:{event_index}:{participant_index}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_blacklist_confirm_keyboard(event_index: int, participant_index: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения добавления в черный список"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"participant:confirm_blacklist:{event_index}:{participant_index}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"participant:cancel_blacklist:{event_index}:{participant_index}")],
        [InlineKeyboardButton(text="⬅️ Назад к участнику", callback_data=f"participant:show:{event_index}:{participant_index}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_blacklist_view_keyboard(blacklist: List[Dict[str, Any]], event_index: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для просмотра черного списка мероприятия"""
    keyboard = []
    
    for i, blacklisted_user in enumerate(blacklist):
        username = blacklisted_user.get("username", "Неизвестный")
        added_by = blacklisted_user.get("added_by", "Неизвестно")
        reason = blacklisted_user.get("reason", "Причина не указана")
        
        # Формируем текст кнопки
        button_text = f"🚫 {username}"
        if len(button_text) > 30:
            button_text = button_text[:27] + "..."
        
        keyboard.append([InlineKeyboardButton(
            text=button_text, 
            callback_data=f"blacklist:show:{event_index}:{i}"
        )])
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton(
        text="⬅️ Назад к мероприятию", 
        callback_data=f"event:show:{event_index}"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_blacklist_user_info_keyboard(event_index: int, blacklist_index: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для информации о пользователе в черном списке"""
    keyboard = [
        [InlineKeyboardButton(text="💬 Написать", callback_data=f"blacklist:message:{event_index}:{blacklist_index}")],
        [InlineKeyboardButton(text="✅ Убрать из ЧС", callback_data=f"blacklist:remove:{event_index}:{blacklist_index}")],
        [InlineKeyboardButton(text="⬅️ Назад к ЧС", callback_data=f"event:blacklist:{event_index}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_past_event_actions_keyboard(event_index: int) -> InlineKeyboardMarkup:
    """Клавиатура для прошедшего мероприятия (для админов)"""
    keyboard = [
        [InlineKeyboardButton(text="👥 Участники", callback_data=f"event:participants:{event_index}")],
        [InlineKeyboardButton(text="📊 Собрать статистику", callback_data=f"event:collect_stats:{event_index}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="event:back_to_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_feedback_rating_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с оценками 1-10 для участника"""
    row1 = [
        InlineKeyboardButton(text=str(i), callback_data=f"feedback:rate:{event_id}:{i}") for i in range(1, 6)
    ]
    row2 = [
        InlineKeyboardButton(text=str(i), callback_data=f"feedback:rate:{event_id}:{i}") for i in range(6, 11)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


def build_feedback_comment_keyboard(event_id: int, rating: int) -> InlineKeyboardMarkup:
    """Клавиатура при вводе комментария: кнопка пропуска"""
    keyboard = [
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"feedback:skip_comment:{event_id}:{rating}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_admin_users_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню раздела 'Посмотреть всех участников бота'"""
    keyboard = [
        [InlineKeyboardButton(text="👥 Участники", callback_data="admin_users:participants")],
        [InlineKeyboardButton(text="🚫 Чёрный список", callback_data="admin_users:blacklist")],
        [InlineKeyboardButton(text="🛡 Админы", callback_data="admin_users:admins")],
        [InlineKeyboardButton(text="🎲 Настольные игры", callback_data="admin_users:games")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_users_list_keyboard(users: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for i, u in enumerate(users):
        username = u.get("tg_username") or u.get("username") or "?"
        keyboard.append([InlineKeyboardButton(text=username, callback_data=f"global_user:show:{i}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users:back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_global_user_info_keyboard(user_index: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="💬 Написать", callback_data=f"global_user:message:{user_index}")],
        [InlineKeyboardButton(text="🚫 Добавить в ЧС", callback_data=f"global_user:blacklist_add:{user_index}")],
        [InlineKeyboardButton(text="📜 История мероприятий", callback_data=f"global_user:history:{user_index}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users:participants")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_global_blacklist_list_keyboard(users: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for i, u in enumerate(users):
        username = u.get("user_tg_username") or u.get("tg_username") or "?"
        keyboard.append([InlineKeyboardButton(text=f"🚫 {username}", callback_data=f"gbl:blacklist:show:{i}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users:back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_global_blacklist_user_keyboard(user_index: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="💬 Написать", callback_data=f"gbl:blacklist:message:{user_index}")],
        [InlineKeyboardButton(text="✅ Исключить из ЧС", callback_data=f"gbl:blacklist:remove:{user_index}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users:blacklist")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_admins_list_keyboard(admins: List[Dict[str, Any]], callback_prefix: str = "gbl:admins:show") -> InlineKeyboardMarkup:
    keyboard = []
    for i, a in enumerate(admins):
        tg = a.get("tg") or a.get("tg_username") or "?"
        keyboard.append([InlineKeyboardButton(text=tg, callback_data=f"{callback_prefix}:{i}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users:back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_admin_info_keyboard(admin_index: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="💬 Написать", callback_data=f"gbl:admin:message:{admin_index}")],
        [InlineKeyboardButton(text="📋 Список прошедших мероприятий", callback_data=f"gbl:admin:past_events:{admin_index}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users:admins")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_cancel_global_message_keyboard(back_callback: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(text="❌ Отменить", callback_data=back_callback)]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_admins_selection_keyboard(admins: List[Dict[str, Any]], selected_usernames: List[str], done_callback: str, toggle_prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    keyboard: List[List[InlineKeyboardButton]] = []
    for i, a in enumerate(admins):
        tg = a.get("tg") or a.get("tg_username") or "?"
        mark = "✅ " if tg in selected_usernames else ""
        keyboard.append([InlineKeyboardButton(text=f"{mark}{tg}", callback_data=f"{toggle_prefix}:{i}")])
    keyboard.append([InlineKeyboardButton(text="✅ Готово", callback_data=done_callback)])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_games_list_keyboard(games: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard: List[List[InlineKeyboardButton]] = []
    for i, g in enumerate(games):
        title = g.get("title") or "Без названия"
        keyboard.append([InlineKeyboardButton(text=title, callback_data=f"games:show:{i}")])
    keyboard.append([InlineKeyboardButton(text="➕ Создать игру", callback_data="games:create")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users:back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_game_view_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="⬅️ К списку игр", callback_data="admin_users:games")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_board_games_selection_keyboard(games: List[Dict[str, Any]], selected_titles: List[str], done_callback: str, toggle_prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    keyboard: List[List[InlineKeyboardButton]] = []
    for i, g in enumerate(games):
        title = g.get("title") or "Без названия"
        mark = "✅ " if title in selected_titles else ""
        keyboard.append([InlineKeyboardButton(text=f"{mark}{title}", callback_data=f"{toggle_prefix}:{i}")])
    keyboard.append([InlineKeyboardButton(text="✅ Готово", callback_data=done_callback)])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_game_inline_keyboard(draft: Dict[str, Any]) -> InlineKeyboardMarkup:
    keyboard = []
    def is_filled(v):
        return v is not None and str(v).strip() != ""
    title_mark = "✅" if is_filled(draft.get("title")) else ""
    photo_mark = "✅" if is_filled(draft.get("photo")) else ""
    rules_mark = "✅" if is_filled(draft.get("rules")) else ""
    keyboard.extend([
        [InlineKeyboardButton(text=f"Картинка {photo_mark}", callback_data="game:photo")],
        [InlineKeyboardButton(text=f"Название {title_mark}", callback_data="game:title")],
        [InlineKeyboardButton(text=f"Правила {rules_mark}", callback_data="game:rules")],
        [InlineKeyboardButton(text="Подтвердить", callback_data="game:confirm")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_game_final_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Сохранить", callback_data="game:final_confirm")],
        [InlineKeyboardButton(text="Назад", callback_data="game:final_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
