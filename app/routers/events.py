from typing import Dict, Any, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

from ..keyboards import build_event_inline_keyboard, build_final_confirm_keyboard, build_events_list_keyboard, build_event_edit_keyboard, build_event_management_keyboard, build_participants_list_keyboard, build_participant_info_keyboard, build_cancel_message_keyboard, build_blacklist_confirm_keyboard, build_blacklist_view_keyboard, build_blacklist_user_info_keyboard, build_edit_final_confirm_keyboard, build_past_event_actions_keyboard, build_feedback_rating_keyboard, build_feedback_comment_keyboard, build_admin_users_main_keyboard, build_users_list_keyboard, build_global_user_info_keyboard, build_global_blacklist_list_keyboard, build_global_blacklist_user_keyboard, build_admins_list_keyboard, build_admin_info_keyboard, build_cancel_global_message_keyboard, build_admins_selection_keyboard, build_contact_responsible_keyboard, build_games_list_keyboard, build_game_view_keyboard, build_game_inline_keyboard, build_game_final_confirm_keyboard
from ..states import EventForm, EventEditForm, MessageParticipantForm, BlacklistForm, MessageBlacklistUserForm, BroadcastForm, FeedbackForm, GlobalMessageForm, ResponsibleSelectionForm, MessageResponsibleForm, BoardGameCreateForm
from ..utils import user_is_admin, format_event_text, format_event_text_without_photo, ensure_draft_keys, draft_missing_fields, is_user_registered_for_event, register_user_for_event, unregister_user_from_event, get_user_registrations, get_event_registrations, is_event_full, get_event_available_slots_count, is_user_on_waitlist, add_user_to_waitlist, remove_user_from_waitlist, get_waitlist_position, get_user_chat_id, ensure_user_exists, get_event_participants, get_user_info, get_user_registrations_count, is_user_in_event_blacklist, add_user_to_event_blacklist, remove_user_from_event_blacklist, get_event_blacklist, save_event_feedback_rating, save_event_feedback_comment, get_all_users, add_user_to_global_blacklist, get_global_blacklist, remove_user_from_global_blacklist, get_all_admins, get_admin_past_events, get_user_events_history, get_board_games, create_board_game, format_game_text, format_game_text_without_photo, parse_event_datetime, is_future_datetime_str
from ..supabase_client import get_supabase


router = Router()


async def _safe_edit_message(message_obj: Message, new_text: str, keyboard: InlineKeyboardMarkup) -> None:
	try:
		if message_obj.photo:
			await message_obj.edit_caption(caption=new_text, reply_markup=keyboard)
		else:
			await message_obj.edit_text(text=new_text, reply_markup=keyboard)
	except TelegramBadRequest as e:
		# Если контент не изменился — пробуем обновить только клавиатуру или игнорируем
		if "message is not modified" in str(e):
			try:
				await message_obj.edit_reply_markup(reply_markup=keyboard)
			except Exception:
				pass
		else:
			raise


@router.message(lambda m: m.text == "Создать мероприятие")
async def on_create_event(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return
    if not user_is_admin(user.username):
        await message.answer("Доступно только админам")
        return

    draft: Dict[str, Any] = {
        "title": None,
        "description": None,
        "photo": None,
        "board_games": None,
        "datetime": None,
        "responsible": None,
        "quantity": None,
    }
    sent = await message.answer(format_event_text(draft), reply_markup=build_event_inline_keyboard(draft))
    await state.update_data(event_draft=draft, card_chat_id=sent.chat.id, card_message_id=sent.message_id)


@router.message(lambda m: m.text == "Предстоящие мероприятия")
async def on_upcoming_events(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        await message.answer("Доступно только админам")
        return
    
    supabase = get_supabase()
    try:
        # Получаем только незавершённые мероприятия
        response = supabase.table("events").select("*").eq("is_completed", False).eq("is_cancelled", False).execute()
        events = response.data
        
        print(f"UPCOMING_EVENTS: found {len(events)} upcoming events")
        for event in events:
            print(f"  Event: id={event.get('id')}, title='{event.get('title')}'")
            print(f"    Full event data: {event}")
        
        if not events:
            await message.answer("Пока нет предстоящих мероприятий")
            return
        
        # Сортируем по дате (если есть)
        events.sort(key=lambda x: x.get("date", ""), reverse=False)
        
        # Сохраняем список мероприятий в состоянии
        await state.update_data(events_list=events)
        
        # Создаем клавиатуру со списком мероприятий
        keyboard = build_events_list_keyboard(events)
        print(f"KEYBOARD_CREATED: {len(keyboard.inline_keyboard)} buttons")
        
        await message.answer(
            f"Предстоящие мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        print(f"UPCOMING_EVENTS_ERROR: {e}")
        await message.answer("Ошибка при загрузке мероприятий")


@router.message(lambda m: m.text == "Прошедшие мероприятия")
async def on_past_events(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        await message.answer("Доступно только админам")
        return
    
    supabase = get_supabase()
    try:
        # Получаем только завершённые мероприятия
        response = supabase.table("events").select("*").eq("is_completed", True).execute()
        events = response.data
        
        print(f"PAST_EVENTS: found {len(events)} past events")
        for event in events:
            print(f"  Event: id={event.get('id')}, title='{event.get('title')}'")
            print(f"    Full event data: {event}")
        
        if not events:
            await message.answer("Пока нет прошедших мероприятий")
            return
        
        # Сортируем по дате (если есть) - самые новые сначала
        events.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # Сохраняем список мероприятий в состоянии
        await state.update_data(events_list=events)
        
        # Создаем клавиатуру со списком мероприятий
        keyboard = build_events_list_keyboard(events)
        print(f"KEYBOARD_CREATED: {len(keyboard.inline_keyboard)} buttons")
        
        await message.answer(
            f"Прошедшие мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        print(f"PAST_EVENTS_ERROR: {e}")
        await message.answer("Ошибка при загрузке мероприятий")


@router.message(lambda m: m.text == "Посмотреть всех участников бота")
async def on_admin_users_menu(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        await message.answer("Доступно только админам")
        return
    kb = build_admin_users_main_keyboard()
    await message.answer("Выберите раздел:", reply_markup=kb)


@router.callback_query(F.data == "admin_users:back")
async def on_admin_users_back(callback: CallbackQuery, state: FSMContext) -> None:
    kb = build_admin_users_main_keyboard()
    await _safe_edit_message(callback.message, "Выберите раздел:", kb)
    await callback.answer()


@router.callback_query(F.data.startswith("user:contact_resp_list:"))
async def on_contact_responsible_list(callback: CallbackQuery, state: FSMContext) -> None:
    # Извлекаем индекс мероприятия
    event_index = int(callback.data.split(":")[-1])
    data = await state.get_data()
    events = data.get("events_list", [])
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    event = events[event_index]
    responsibles_raw = event.get("responsible") or ""
    responsibles = [s.strip() for s in responsibles_raw.split(",") if s.strip()]
    if not responsibles:
        await callback.answer("Ответственные не указаны", show_alert=True)
        return
    kb = build_contact_responsible_keyboard(event_index, responsibles)
    await _safe_edit_message(callback.message, "Откройте профиль ответственного и напишите ему в ЛС:", kb)
    await callback.answer()


# Убрали отправку через бота — всегда предлагаем прямой контакт

@router.callback_query(F.data == "admin_users:participants")
async def on_admin_users_participants(callback: CallbackQuery, state: FSMContext) -> None:
    # Исключаем админов из списка участников
    users = get_all_users()
    admins = get_all_admins()
    admin_tgs = set()
    for a in admins:
        tg = a.get("tg") or a.get("tg_username")
        if tg:
            admin_tgs.add(tg)
    users = [u for u in users if (u.get("tg_username") not in admin_tgs)]
    await state.update_data(global_users=users)
    kb = build_users_list_keyboard(users)
    await _safe_edit_message(callback.message, "👥 Все пользователи:", kb)
    await callback.answer()


@router.callback_query(F.data.startswith("global_user:show:"))
async def on_global_user_show(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    users = data.get("global_users", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(users):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    user = users[idx]
    username = user.get("tg_username")
    text = f"👤 {username}\nchat_id: {user.get('chat_id') or '-'}\nВ боте с: {user.get('created_at') or '-'}"
    kb = build_global_user_info_keyboard(idx)
    await _safe_edit_message(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data.startswith("global_user:history:"))
async def on_global_user_history(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    users = data.get("global_users", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(users):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    username = users[idx].get("tg_username")
    history = get_user_events_history(username)
    if not history:
        await callback.answer("История пуста", show_alert=True)
        return
    # Подготовим простой список
    lines = ["📜 История мероприятий:"]
    for rec in history[:30]:
        event = rec.get("events") or {}
        title = event.get("title", "Без названия")
        date = event.get("date", "-")
        status = rec.get("status", "?")
        lines.append(f"• {title} | {date} | {status}")
    text = "\n".join(lines)
    await _safe_edit_message(callback.message, text, build_global_user_info_keyboard(idx))
    await callback.answer()


@router.callback_query(F.data.startswith("global_user:blacklist_add:"))
async def on_global_user_blacklist_add(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    users = data.get("global_users", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(users):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    username = users[idx].get("tg_username")
    if add_user_to_global_blacklist(username):
        await callback.answer("Пользователь добавлен в глобальный ЧС", show_alert=True)
    else:
        await callback.answer("Не удалось добавить в ЧС", show_alert=True)


@router.callback_query(F.data == "admin_users:blacklist")
async def on_admin_users_blacklist(callback: CallbackQuery, state: FSMContext) -> None:
    users = get_global_blacklist()
    await state.update_data(global_blacklist=users)
    kb = build_global_blacklist_list_keyboard(users)
    await _safe_edit_message(callback.message, "🚫 Глобальный чёрный список:", kb)
    await callback.answer()


@router.callback_query(F.data.startswith("gbl:blacklist:show:"))
async def on_global_blacklist_show(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    users = data.get("global_blacklist", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(users):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    username = users[idx].get("user_tg_username")
    text = f"🚫 {username}\nДобавлен: {users[idx].get('added_at','-')}"
    kb = build_global_blacklist_user_keyboard(idx)
    await _safe_edit_message(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data.startswith("gbl:blacklist:remove:"))
async def on_global_blacklist_remove(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    users = data.get("global_blacklist", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(users):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    username = users[idx].get("user_tg_username")
    if remove_user_from_global_blacklist(username):
        await callback.answer("Пользователь исключён из ЧС", show_alert=True)
        # Обновить список
        updated = get_global_blacklist()
        await state.update_data(global_blacklist=updated)
        kb = build_global_blacklist_list_keyboard(updated)
        await _safe_edit_message(callback.message, "🚫 Глобальный чёрный список:", kb)
    else:
        await callback.answer("Не удалось исключить", show_alert=True)


@router.callback_query(F.data == "admin_users:admins")
async def on_admin_users_admins(callback: CallbackQuery, state: FSMContext) -> None:
    admins = get_all_admins()
    await state.update_data(global_admins=admins)
    kb = build_admins_list_keyboard(admins)
    await _safe_edit_message(callback.message, "🛡 Администраторы:", kb)
    await callback.answer()


@router.callback_query(F.data == "admin_users:games")
async def on_admin_users_games(callback: CallbackQuery, state: FSMContext) -> None:
    games = get_board_games()
    await state.update_data(board_games_list=games)
    kb = build_games_list_keyboard(games)
    await _safe_edit_message(callback.message, "🎲 Настольные игры:", kb)
    await callback.answer()


@router.callback_query(F.data.startswith("games:show:"))
async def on_show_game(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    games = data.get("board_games_list", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(games):
        await callback.answer("Игра не найдена", show_alert=True)
        return
    game = games[idx]
    title = game.get("title") or "Без названия"
    rules = game.get("rules") or "Правила не указаны"
    caption = f"🎲 {title}\n\n📜 Правила:\n{rules}"
    kb = build_game_view_keyboard()
    if game.get("photo"):
        try:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=game["photo"], caption=caption),
                reply_markup=kb
            )
        except Exception:
            await _safe_edit_message(callback.message, caption, kb)
    else:
        await _safe_edit_message(callback.message, caption, kb)
    await callback.answer()


@router.callback_query(F.data == "games:create")
async def on_create_game(callback: CallbackQuery, state: FSMContext) -> None:
    draft = {"photo": None, "title": None, "rules": None}
    await state.update_data(game_draft=draft, game_card_chat_id=callback.message.chat.id, game_card_message_id=callback.message.message_id)
    # Показ карточки с кнопками
    await _safe_edit_message(callback.message, format_game_text_without_photo(draft), build_game_inline_keyboard(draft))
    await callback.answer()


@router.callback_query(F.data == "game:photo")
async def game_cb_set_photo(callback: CallbackQuery, state: FSMContext) -> None:
    await _ask_and_set_state(callback, state, "Отправьте картинку игры (или пропустите, отправив '-' ):", BoardGameCreateForm.waiting_for_photo)


@router.message(BoardGameCreateForm.waiting_for_photo)
async def game_set_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("game_draft", {})
    photo_value = None
    if (message.text or "").strip() != "-":
        if message.photo:
            try:
                photo_value = message.photo[-1].file_id
            except Exception:
                photo_value = None
        if not photo_value:
            photo_value = (message.text or "").strip() or None
    draft["photo"] = photo_value
    await state.update_data(game_draft=draft)
    await _delete_prompt_and_input(message, state)
    # Обновляем карточку
    # Обновляем карточку
    await message.answer(format_game_text(draft), reply_markup=build_game_inline_keyboard(draft))
    await state.set_state(None)


@router.callback_query(F.data == "game:title")
async def game_cb_set_title(callback: CallbackQuery, state: FSMContext) -> None:
    await _ask_and_set_state(callback, state, "Введите название игры:", BoardGameCreateForm.waiting_for_title)


@router.message(BoardGameCreateForm.waiting_for_title)
async def game_set_title(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("game_draft", {})
    draft["title"] = (message.text or "").strip() or None
    await state.update_data(game_draft=draft)
    await _delete_prompt_and_input(message, state)
    await message.answer(format_game_text(draft), reply_markup=build_game_inline_keyboard(draft))
    await state.set_state(None)


@router.callback_query(F.data == "game:rules")
async def game_cb_set_rules(callback: CallbackQuery, state: FSMContext) -> None:
    await _ask_and_set_state(callback, state, "Вставьте правила (текст):", BoardGameCreateForm.waiting_for_rules)


@router.message(BoardGameCreateForm.waiting_for_rules)
async def game_set_rules(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("game_draft", {})
    draft["rules"] = (message.text or "").strip() or None
    await state.update_data(game_draft=draft)
    await _delete_prompt_and_input(message, state)
    # Показать финальные кнопки
    await message.answer(format_game_text(draft), reply_markup=build_game_final_confirm_keyboard())


@router.callback_query(F.data == "game:final_cancel")
async def game_final_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Продолжайте редактирование", show_alert=False)
    data = await state.get_data()
    draft = data.get("game_draft", {})
    await _safe_edit_message(callback.message, format_event_text({
        "title": draft.get("title"),
        "description": draft.get("rules"),
        "photo": draft.get("photo"),
        "board_games": None,
        "datetime": None,
        "responsible": None,
        "quantity": None,
    }), build_game_inline_keyboard(draft))


@router.callback_query(F.data == "game:final_confirm")
async def game_final_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("game_draft", {})
    if not draft.get("title"):
        await callback.answer("Название обязательно", show_alert=True)
        return
    ok = create_board_game({
        "title": draft.get("title"),
        "photo": draft.get("photo"),
        "rules": draft.get("rules"),
    })
    if ok:
        await callback.answer("Игра создана", show_alert=True)
        games = get_board_games()
        await state.update_data(board_games_list=games, game_draft=None)
        kb = build_games_list_keyboard(games)
        await _safe_edit_message(callback.message, "🎲 Настольные игры:", kb)
    else:
        await callback.answer("Ошибка при создании", show_alert=True)
@router.callback_query(F.data.startswith("gbl:admins:show:"))
async def on_admin_info(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    admins = data.get("global_admins", [])
    idx = int(callback.data.split(":")[3])
    if idx >= len(admins):
        await callback.answer("Админ не найден", show_alert=True)
        return
    admin = admins[idx]
    tg = admin.get("tg") or admin.get("tg_username")
    text = f"🛡 {tg}"
    kb = build_admin_info_keyboard(idx)
    await _safe_edit_message(callback.message, text, kb)
    await callback.answer()


@router.callback_query(F.data.startswith("gbl:admin:past_events:"))
async def on_admin_past_events(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    admins = data.get("global_admins", [])
    idx = int(callback.data.split(":")[3])
    if idx >= len(admins):
        await callback.answer("Админ не найден", show_alert=True)
        return
    tg = admins[idx].get("tg") or admins[idx].get("tg_username")
    events = get_admin_past_events(tg)
    if not events:
        await callback.answer("Нет прошедших мероприятий", show_alert=True)
        return
    # использовать общий список
    await state.update_data(events_list=events)
    kb = build_events_list_keyboard(events)
    await _safe_edit_message(callback.message, f"Прошедшие мероприятия администратора {tg}:", kb)
    await callback.answer()


@router.callback_query(F.data.startswith("global_user:message:"))
async def on_global_user_message(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    users = data.get("global_users", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(users):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    user = users[idx]
    username = user.get("tg_username")
    chat_id = user.get("chat_id")
    await state.update_data(global_msg_target_username=username, global_msg_target_chat_id=chat_id)
    kb = build_cancel_global_message_keyboard("admin_users:participants")
    await _safe_edit_message(callback.message, f"💬 Написать пользователю {username}\n\nВведите текст сообщения:", kb)
    await state.set_state(GlobalMessageForm.waiting_for_message)
    await callback.answer()


@router.callback_query(F.data.startswith("gbl:blacklist:message:"))
async def on_global_blacklist_message(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    users = data.get("global_blacklist", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(users):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    username = users[idx].get("user_tg_username")
    await state.update_data(global_msg_target_username=username, global_msg_target_chat_id=None)
    kb = build_cancel_global_message_keyboard("admin_users:blacklist")
    await _safe_edit_message(callback.message, f"💬 Написать пользователю {username}\n\nВведите текст сообщения:", kb)
    await state.set_state(GlobalMessageForm.waiting_for_message)
    await callback.answer()


@router.callback_query(F.data.startswith("gbl:admin:message:"))
async def on_admins_list_message(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    admins = data.get("global_admins", [])
    idx = int(callback.data.split(":")[3])
    if idx >= len(admins):
        await callback.answer("Админ не найден", show_alert=True)
        return
    tg = admins[idx].get("tg") or admins[idx].get("tg_username")
    await state.update_data(global_msg_target_username=tg, global_msg_target_chat_id=None)
    kb = build_cancel_global_message_keyboard("admin_users:admins")
    await _safe_edit_message(callback.message, f"💬 Написать администратору {tg}\n\nВведите текст сообщения:", kb)
    await state.set_state(GlobalMessageForm.waiting_for_message)
    await callback.answer()


@router.message(GlobalMessageForm.waiting_for_message)
async def on_global_message_send(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    username = data.get("global_msg_target_username")
    chat_id = data.get("global_msg_target_chat_id")
    text = message.text
    delivered = False
    if chat_id:
        try:
            await message.bot.send_message(chat_id=chat_id, text=text)
            delivered = True
        except Exception as e:
            print(f"ERROR sending global msg by chat_id: {e}")
    if not delivered and username:
        try:
            actual_chat_id = get_user_chat_id(username)
            if actual_chat_id:
                await message.bot.send_message(chat_id=actual_chat_id, text=text)
                delivered = True
        except Exception as e:
            print(f"ERROR sending global msg by username: {e}")
    await message.answer("Сообщение отправлено" if delivered else "Не удалось доставить сообщение")
    await state.clear()
@router.callback_query(F.data.startswith("event:complete:"))
async def on_complete_event(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Проверяем, не завершено ли уже мероприятие
    if event.get("is_completed", False):
        await callback.answer("Мероприятие уже завершено", show_alert=True)
        return
    
    # Обновляем мероприятие в базе данных
    supabase = get_supabase()
    try:
        # Используем title для идентификации мероприятия, так как id может отсутствовать
        supabase.table("events").update({"is_completed": True}).eq("title", event["title"]).execute()
        
        await callback.answer("Мероприятие завершено! ✅", show_alert=True)
        
        # Удаляем завершённое мероприятие из текущего списка
        events.pop(event_index)
        
        # Обновляем состояние
        await state.update_data(events_list=events)
        
        # Возвращаемся к списку мероприятий
        keyboard = build_events_list_keyboard(events)
        
        # Проверяем, есть ли фото в текущем сообщении
        if callback.message.photo:
            # Если сообщение содержит фото, редактируем как фото с новым caption
            await callback.message.edit_caption(
                caption=f"Предстоящие мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:",
                reply_markup=keyboard
            )
        else:
            # Если сообщение текстовое, редактируем как текст
            await callback.message.edit_text(
                f"Предстоящие мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:",
                reply_markup=keyboard
            )
        
        # Уведомляем всех зарегистрированных участников о завершении мероприятия
        try:
            # Получаем всех зарегистрированных участников
            participants_resp = (
                supabase
                .table("event_registrations")
                .select("user_tg_username")
                .eq("event_id", event.get("id"))
                .eq("status", "registered")
                .execute()
            )
            
            if participants_resp.data:
                event_info = f"📋 {event.get('title', 'Мероприятие')}\n📅 {event.get('date', 'Дата не указана')}"
                completion_text = f"🏁 **Мероприятие завершено!**\n\n{event_info}\n\nСпасибо за участие! Надеемся, вам понравилось! 🎉"
                
                for participant in participants_resp.data:
                    try:
                        notify_username = participant["user_tg_username"].lstrip("@")
                        await callback.bot.send_message(
                            chat_id=f"@{notify_username}",
                            text=completion_text
                        )
                    except Exception as notify_error:
                        print(f"ERROR sending completion notification to {participant['user_tg_username']}: {notify_error}")
                        # Продолжаем с другими участниками
        except Exception as e:
            print(f"ERROR sending completion notifications: {e}")
            # Уведомления не критичны, продолжаем работу
        
    except Exception as e:
        print(f"COMPLETE_EVENT_ERROR: {e}")
        await callback.answer("Ошибка при завершении мероприятия", show_alert=True)


@router.callback_query(F.data.startswith("event:show:"))
async def on_show_event_details(callback: CallbackQuery, state: FSMContext) -> None:
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Форматируем детали мероприятия
    details = f"📋 {event.get('title', 'Без названия')}\n\n"
    
    # Добавляем статус завершения/отмены
    if event.get("is_completed", False):
        details += "✅ **МЕРОПРИЯТИЕ ЗАВЕРШЕНО**\n\n"
    if event.get("is_cancelled", False):
        details += "❌ **МЕРОПРИЯТИЕ ОТМЕНЕНО**\n\n"
    
    if event.get("description"):
        details += f"📝 Описание: {event['description']}\n\n"
    
    if event.get("board_games"):
        details += f"🎲 Настольные игры: {event['board_games']}\n\n"
    
    if event.get("date"):
        details += f"📅 Дата и время: {event['date']}\n\n"
    
    if event.get("responsible"):
        details += f"👥 Ответственные: {event['responsible']}\n\n"
    
    if event.get("quantity"):
        details += f"👤 Количество участников: {event['quantity']}\n\n"
    
    # Добавляем информацию о доступных местах
    available_slots = get_event_available_slots_count(event.get("id"))
    if available_slots == -1:
        details += "🎫 Мест: неограниченно\n\n"
    elif available_slots == 0:
        details += "🎫 Мест: нет свободных мест\n\n"
    else:
        details += f"🎫 Свободных мест: {available_slots}\n\n"
    
    # Проверяем, является ли пользователь админом
    is_admin = user_is_admin(callback.from_user.username if callback.from_user else None)
    
    # Создаем клавиатуру для деталей мероприятия
    keyboard = []
    
    if is_admin:
        # Клавиатура для админов
        if not event.get("is_completed", False) and not event.get("is_cancelled", False):
            # Используем готовую клавиатуру управления
            keyboard = build_event_management_keyboard(event_index).inline_keyboard
        else:
            # Для завершённых/отменённых мероприятий показать кнопки: участники и сбор статистики
            keyboard = build_past_event_actions_keyboard(event_index).inline_keyboard
    else:
        # Клавиатура для обычных пользователей
        if not event.get("is_completed", False) and not event.get("is_cancelled", False):
            # Проверяем, зарегистрирован ли пользователь на это мероприятие
            is_registered = is_user_registered_for_event(
                callback.from_user.username if callback.from_user else None,
                event.get("id")
            )
            
            # Проверяем, находится ли пользователь в очереди ожидания
            is_on_waitlist = is_user_on_waitlist(
                callback.from_user.username if callback.from_user else None,
                event.get("id")
            )
            
            if is_registered:
                keyboard.append([InlineKeyboardButton(text="❌ Отменить регистрацию", callback_data=f"event:unregister:{event_index}")])
            elif is_on_waitlist:
                # Показываем позицию в очереди
                position = get_waitlist_position(
                    callback.from_user.username if callback.from_user else None,
                    event.get("id")
                )
                keyboard.append([InlineKeyboardButton(text=f"⏳ В очереди (№{position})", callback_data=f"event:leave_waitlist:{event_index}")])
            else:
                # Проверяем, не заполнено ли мероприятие
                if is_event_full(event.get("id")):
                    keyboard.append([InlineKeyboardButton(text="📋 Занять место", callback_data=f"event:join_waitlist:{event_index}")])
                else:
                    keyboard.append([InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data=f"event:register:{event_index}")])
            # Добавим кнопку написать ответственному
            responsibles_raw = event.get("responsible") or ""
            responsibles = [s.strip() for s in responsibles_raw.split(",") if s.strip()]
            if responsibles:
                keyboard.append([InlineKeyboardButton(text="💬 Написать ответственному", callback_data=f"user:contact_resp_list:{event_index}")])
        else:
            details += "❌ Регистрация на это мероприятие закрыта\n\n"
    
    # Создаем клавиатуру
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    # Редактируем существующее сообщение
    if event.get("photo"):
        # Проверяем, является ли photo валидным file_id
        photo_value = event['photo']
        is_valid_file_id = (
            isinstance(photo_value, str) and 
            len(photo_value) > 20 and 
            not any(char in photo_value for char in [' ', '\n', '\t', 'ывп'])  # Простая проверка
        )
        
        if is_valid_file_id:
            # Если есть фото и оно валидное, редактируем как фото
            try:
                await callback.message.edit_media(
                    media=InputMediaPhoto(
                        media=photo_value,
                        caption=details
                    ),
                    reply_markup=inline_keyboard
                )
            except Exception as e:
                print(f"PHOTO_EDIT_ERROR: {e}")
                # Если не удалось отредактировать как фото, редактируем как текст
                await callback.message.edit_text(details, reply_markup=inline_keyboard)
        else:
            # Если фото невалидное, редактируем как текст
            await callback.message.edit_text(details, reply_markup=inline_keyboard)
    else:
        # Если нет фото, редактируем как текст
        await callback.message.edit_text(details, reply_markup=inline_keyboard)
    
    await callback.answer()


@router.callback_query(F.data.startswith("event:collect_stats:"))
async def on_collect_stats(callback: CallbackQuery, state: FSMContext) -> None:
    """Отправляет всем участникам прошедшего мероприятия запрос на оценку 1-10 и комментарий"""
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    event_index = int(callback.data.split(":")[2])
    data = await state.get_data()
    events = data.get("events_list", [])
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    event = events[event_index]
    event_id = event.get("id")
    title = event.get("title", "Мероприятие")
    # Получаем участников (только зарегистрированные как посетившие либо все зарегистрированные)
    participants = get_event_participants(event_id)
    if not participants:
        await callback.answer("Нет участников для опроса", show_alert=True)
        return
    sent = 0
    failed = 0
    for p in participants:
        username = p.get("username")
        chat_id = get_user_chat_id(username)
        if not chat_id:
            failed += 1
            continue
        try:
            text = (
                f"🙏 Спасибо, что были на \"{title}\"!\n\n"
                "Оцените мероприятие по шкале от 1 до 10. После оценки можно будет добавить комментарий."
            )
            await callback.bot.send_message(chat_id=chat_id, text=text, reply_markup=build_feedback_rating_keyboard(event_id))
            sent += 1
        except Exception as e:
            print(f"ERROR sending feedback request to {username}: {e}")
            failed += 1
    await callback.answer(f"Запрос отправлен. Успешно: {sent}, ошибок: {failed}", show_alert=True)
@router.callback_query(F.data.startswith("feedback:rate:"))
async def on_feedback_rate(callback: CallbackQuery, state: FSMContext) -> None:
    """Прием оценки от 1 до 10 и запрос комментария"""
    parts = callback.data.split(":")
    event_id = int(parts[2])
    rating = int(parts[3])
    username = callback.from_user.username if callback.from_user else None
    if not save_event_feedback_rating(username, event_id, rating):
        await callback.answer("Не удалось сохранить оценку", show_alert=True)
        return
    await state.update_data(feedback_event_id=event_id, feedback_rating=rating)
    await state.set_state(FeedbackForm.waiting_for_comment)
    kb = build_feedback_comment_keyboard(event_id, rating)
    await callback.message.answer(
        f"Спасибо за оценку {rating}/10!\n\nДобавьте, пожалуйста, комментарий (или нажмите \"Пропустить\").",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("feedback:skip_comment:"))
async def on_feedback_skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    event_id = int(parts[2])
    rating = int(parts[3])
    await state.clear()
    await callback.answer("Спасибо за отзыв!", show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.message(FeedbackForm.waiting_for_comment)
async def on_feedback_comment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    event_id = data.get("feedback_event_id")
    rating = data.get("feedback_rating")
    comment = message.text or ""
    username = message.from_user.username if message.from_user else None
    save_event_feedback_comment(username, event_id, comment)
    await message.answer("Спасибо! Ваш отзыв сохранен.")
    await state.clear()


@router.callback_query(F.data == "event:back_to_list")
async def on_back_to_list(callback: CallbackQuery, state: FSMContext) -> None:
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if not events:
        await callback.answer("Список мероприятий не найден", show_alert=True)
        return
    
    # Создаем клавиатуру со списком мероприятий
    keyboard = build_events_list_keyboard(events)
    
    # Определяем тип списка по первому мероприятию (все мероприятия в списке одного типа)
    is_past_events = events[0].get("is_completed", False) if events else False
    
    # Проверяем, является ли пользователь админом
    is_admin = user_is_admin(callback.from_user.username if callback.from_user else None)
    
    if is_admin:
        if is_past_events:
            list_title = f"Прошедшие мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:"
        else:
            list_title = f"Предстоящие мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:"
    else:
        # Определяем тип списка по заголовку сообщения
        current_caption = callback.message.caption or callback.message.text or ""
        
        if "Мои мероприятия" in current_caption:
            list_title = f"Мои мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:"
        else:
            list_title = f"Доступные мероприятия для регистрации ({len(events)}):\n\nВыберите мероприятие:"
    
    # Проверяем, есть ли фото в текущем сообщении
    if callback.message.photo:
        # Если сообщение содержит фото, редактируем как фото с новым caption
        await callback.message.edit_caption(
            caption=list_title,
            reply_markup=keyboard
        )
    else:
        # Если сообщение текстовое, редактируем как текст
        await callback.message.edit_text(
            list_title,
            reply_markup=keyboard
        )
    
    await callback.answer()


async def _ask_and_set_state(callback: CallbackQuery, state: FSMContext, text: str, next_state):
    prompt = await callback.message.answer(text)
    await state.update_data(prompt_message_id=prompt.message_id)
    await state.set_state(next_state)
    await callback.answer()


@router.callback_query(F.data.startswith("evt:responsible_toggle"))
async def on_responsible_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    admins = data.get("responsible_admins") or data.get("edit_responsible_admins") or []
    idx = int(callback.data.split(":")[-1])
    if idx >= len(admins):
        await callback.answer()
        return
    tg = admins[idx].get("tg") or admins[idx].get("tg_username")
    key_selected = "selected_responsibles" if "responsible_admins" in data else "edit_selected_responsibles"
    selected = data.get(key_selected, [])
    if tg in selected:
        selected = [x for x in selected if x != tg]
    else:
        selected.append(tg)
    await state.update_data(**{key_selected: selected})
    kb = build_admins_selection_keyboard(admins, selected, done_callback=("evt:responsible_done" if key_selected=="selected_responsibles" else "evt_edit:responsible_done"), toggle_prefix=("evt:responsible_toggle" if key_selected=="selected_responsibles" else "evt_edit:responsible_toggle"), back_callback=("evt:responsible_back" if key_selected=="selected_responsibles" else "evt_edit:responsible_back"))
    await _safe_edit_message(callback.message, "Выберите ответственных (можно несколько):", kb)
    await callback.answer()


@router.callback_query(F.data.startswith("evt:board_games_toggle"))
async def on_evt_board_games_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    games = data.get("evt_board_games_all", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(games):
        await callback.answer()
        return
    title = games[idx].get("title")
    selected = set(data.get("evt_board_games_selected", []))
    if title in selected:
        selected.remove(title)
    else:
        selected.add(title)
    selected_list = list(selected)
    await state.update_data(evt_board_games_selected=selected_list)
    from ..keyboards import build_board_games_selection_keyboard
    kb = build_board_games_selection_keyboard(games, selected_list, done_callback="evt:board_games_done", toggle_prefix="evt:board_games_toggle", back_callback="evt:board_games_back")
    await _safe_edit_message(callback.message, "Выберите настолки (можно несколько):", kb)
    await callback.answer()


@router.callback_query(F.data == "evt:board_games_done")
async def on_evt_board_games_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    selected = data.get("evt_board_games_selected", [])
    draft["board_games"] = ", ".join(selected) if selected else None
    await state.update_data(event_draft=draft, evt_board_games_selected=None, evt_board_games_all=None)
    await _safe_edit_message(callback.message, format_event_text(draft), build_event_inline_keyboard(draft))
    await callback.answer()


@router.callback_query(F.data == "evt:board_games_back")
async def on_evt_board_games_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    await _safe_edit_message(callback.message, format_event_text(draft), build_event_inline_keyboard(draft))
    await callback.answer()


@router.callback_query(F.data == "evt:responsible_done")
async def on_responsible_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    selected: list[str] = data.get("selected_responsibles", [])
    draft["responsible"] = ", ".join(selected) if selected else None
    await state.update_data(event_draft=draft, selected_responsibles=None, responsible_admins=None)
    # обновить карточку
    await _safe_edit_message(callback.message, format_event_text(draft), build_event_inline_keyboard(draft))
    await state.set_state(None)
    await callback.answer("Ответственные обновлены", show_alert=True)


@router.callback_query(F.data == "evt:responsible_back")
async def on_responsible_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    await _safe_edit_message(callback.message, format_event_text(draft), build_event_inline_keyboard(draft))
    await state.set_state(None)
    await callback.answer()


@router.callback_query(F.data.startswith("evt_edit:responsible_toggle"))
async def on_edit_responsible_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    admins = data.get("edit_responsible_admins") or []
    idx = int(callback.data.split(":")[-1])
    if idx >= len(admins):
        await callback.answer()
        return
    tg = admins[idx].get("tg") or admins[idx].get("tg_username")
    selected = data.get("edit_selected_responsibles", [])
    if tg in selected:
        selected = [x for x in selected if x != tg]
    else:
        selected.append(tg)
    await state.update_data(edit_selected_responsibles=selected)
    kb = build_admins_selection_keyboard(admins, selected, done_callback="evt_edit:responsible_done", toggle_prefix="evt_edit:responsible_toggle", back_callback="evt_edit:responsible_back")
    await _safe_edit_message(callback.message, "Выберите ответственных (можно несколько):", kb)
    await callback.answer()


@router.callback_query(F.data.startswith("evt_edit:board_games_toggle"))
async def on_evt_edit_board_games_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    games = data.get("evt_edit_board_games_all", [])
    idx = int(callback.data.split(":")[-1])
    if idx >= len(games):
        await callback.answer()
        return
    title = games[idx].get("title")
    selected = set(data.get("evt_edit_board_games_selected", []))
    if title in selected:
        selected.remove(title)
    else:
        selected.add(title)
    selected_list = list(selected)
    await state.update_data(evt_edit_board_games_selected=selected_list)
    from ..keyboards import build_board_games_selection_keyboard
    kb = build_board_games_selection_keyboard(games, selected_list, done_callback="evt_edit:board_games_done", toggle_prefix="evt_edit:board_games_toggle", back_callback="evt_edit:board_games_back")
    await _safe_edit_message(callback.message, "Выберите настолки (можно несколько):", kb)
    await callback.answer()


@router.callback_query(F.data == "evt_edit:board_games_done")
async def on_evt_edit_board_games_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    edit_draft = data.get("edit_draft") or {}
    selected = data.get("evt_edit_board_games_selected", [])
    edit_draft["board_games"] = ", ".join(selected) if selected else None
    await state.update_data(edit_draft=edit_draft, evt_edit_board_games_selected=None, evt_edit_board_games_all=None)
    kb = build_event_edit_keyboard(edit_draft)
    await _safe_edit_message(callback.message, "✏️ Редактирование мероприятия\n\nВыберите поле для изменения:", kb)
    await callback.answer()


@router.callback_query(F.data == "evt_edit:board_games_back")
async def on_evt_edit_board_games_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    edit_draft = data.get("edit_draft") or {}
    kb = build_event_edit_keyboard(edit_draft)
    await _safe_edit_message(callback.message, "✏️ Редактирование мероприятия\n\nВыберите поле для изменения:", kb)
    await callback.answer()


@router.callback_query(F.data == "evt_edit:responsible_done")
async def on_edit_responsible_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    edit_draft = data.get("edit_draft") or {}
    selected: list[str] = data.get("edit_selected_responsibles", [])
    edit_draft["responsible"] = ", ".join(selected) if selected else None
    await state.update_data(edit_draft=edit_draft)
    await state.set_state(None)
    # Вернуться в экран редактирования
    kb = build_event_edit_keyboard(edit_draft)
    await _safe_edit_message(callback.message, "✏️ Редактирование мероприятия\n\nВыберите поле для изменения:", kb)
    await callback.answer("Ответственные обновлены", show_alert=True)


@router.callback_query(F.data == "evt_edit:responsible_back")
async def on_edit_responsible_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    edit_draft = data.get("edit_draft") or {}
    kb = build_event_edit_keyboard(edit_draft)
    await _safe_edit_message(callback.message, "✏️ Редактирование мероприятия\n\nВыберите поле для изменения:", kb)
    await state.set_state(None)
    await callback.answer()
@router.callback_query(F.data == "evt:title")
async def cb_set_title(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_state(callback, state, "Введите название мероприятия:", EventForm.waiting_for_title)


@router.callback_query(F.data == "evt:description")
async def cb_set_description(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_state(callback, state, "Введите описание мероприятия:", EventForm.waiting_for_description)


@router.callback_query(F.data == "evt:photo")
async def cb_set_photo(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_state(callback, state, "Отправьте ссылку на картинку или просто прикрепите фото сообщением:", EventForm.waiting_for_photo)


@router.callback_query(F.data == "evt:board_games")
async def cb_set_board_games(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    games = get_board_games()
    await state.update_data(evt_board_games_all=games, evt_board_games_selected=[])
    from ..keyboards import build_board_games_selection_keyboard
    kb = build_board_games_selection_keyboard(games, [], done_callback="evt:board_games_done", toggle_prefix="evt:board_games_toggle", back_callback="evt:board_games_back")
    await _safe_edit_message(callback.message, "Выберите настолки (можно несколько):", kb)


@router.callback_query(F.data == "evt:datetime")
async def cb_set_datetime(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    hint = (
        "Введите дату и время в одном из форматов:\n"
        "- DD.MM.YYYY HH:MM (напр., 25.08.2025 18:30)\n"
        "- DD/MM/YYYY HH:MM\n"
        "- YYYY-MM-DD HH:MM\n"
        "Время обязательно."
    )
    await _ask_and_set_state(callback, state, hint, EventForm.waiting_for_datetime)


@router.callback_query(F.data == "evt:responsible")
async def cb_set_responsible(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    # Переход на выбор из списка админов
    admins = get_all_admins()
    await state.update_data(responsible_admins=admins, selected_responsibles=[])
    kb = build_admins_selection_keyboard(admins, [], done_callback="evt:responsible_done", toggle_prefix="evt:responsible_toggle", back_callback="evt:responsible_back")
    await _safe_edit_message(callback.message, "Выберите ответственных (можно несколько):", kb)
    await state.set_state(ResponsibleSelectionForm.waiting_for_responsibles)


@router.callback_query(F.data == "evt:quantity")
async def cb_set_quantity(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_state(callback, state, "Введите количество участников (число):", EventForm.waiting_for_quantity)


async def _delete_prompt_and_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    prompt_id = data.get("prompt_message_id")
    if prompt_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_id)
        except Exception:
            pass
    try:
        await message.delete()
    except Exception:
        pass


async def _update_card(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    chat_id = data.get("card_chat_id")
    msg_id = data.get("card_message_id")
    print(f"UPDATE_CARD: chat_id={chat_id}, msg_id={msg_id}, has_photo={bool(draft.get('photo'))}")
    
    if chat_id and msg_id:
        try:
            # Если есть фото, редактируем caption у фото-сообщения
            if draft.get("photo"):
                print(f"EDIT_PHOTO_CAPTION: {msg_id}")
                await message.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=msg_id,
                    caption=format_event_text(draft),
                    reply_markup=build_event_inline_keyboard(draft),
                )
                print(f"PHOTO_CAPTION_UPDATED: {msg_id}")
            else:
                # Нет фото, редактируем как текст
                print(f"EDIT_TEXT_MESSAGE: {msg_id}")
                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=format_event_text_without_photo(draft),
                    reply_markup=build_event_inline_keyboard(draft),
                )
                print(f"TEXT_MESSAGE_UPDATED: {msg_id}")
        except Exception as e:
            print(f"UPDATE_CARD_ERROR: {e}")
            # Если не удалось отредактировать, пытаемся как текст
            try:
                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=format_event_text_without_photo(draft),
                    reply_markup=build_event_inline_keyboard(draft),
                )
            except Exception:
                pass


@router.message(EventForm.waiting_for_title)
async def set_title(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    draft["title"] = (message.text or "").strip() or None
    await state.update_data(event_draft=draft)
    await _delete_prompt_and_input(message, state)
    await _update_card(message, state)
    await state.set_state(None)
    data.pop("prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventForm.waiting_for_description)
async def set_description(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    draft["description"] = (message.text or "").strip() or None
    await state.update_data(event_draft=draft)
    await _delete_prompt_and_input(message, state)
    await _update_card(message, state)
    await state.set_state(None)
    data.pop("prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventForm.waiting_for_photo)
async def set_photo(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    photo_value: Optional[str] = None
    if message.photo:
        try:
            # Берем file_id как маркер фото (текстово сохраним)
            photo_value = message.photo[-1].file_id
        except Exception:
            photo_value = None
    if not photo_value:
        photo_value = (message.text or "").strip() or None
    
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    old_photo = draft.get("photo")
    draft["photo"] = photo_value
    await _delete_prompt_and_input(message, state)
    
    # Если фото добавляется впервые, пересоздаём карточку
    if not old_photo and photo_value:
        chat_id = data.get("card_chat_id")
        msg_id = data.get("card_message_id")
        if chat_id and msg_id:
            try:
                # Удаляем старое текстовое сообщение
                await message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                # Отправляем новое с фото
                sent = await message.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_value,
                    caption=format_event_text(draft),
                    reply_markup=build_event_inline_keyboard(draft),
                )
                # Обновляем состояние с новым ID сообщения
                await state.update_data(
                    event_draft=draft,
                    card_message_id=sent.message_id,
                    prompt_message_id=None
                )
                print(f"PHOTO_CARD_CREATED: new_msg_id={sent.message_id}")
            except Exception as e:
                print(f"PHOTO_CREATE_ERROR: {e}")
                # В случае ошибки всё равно обновляем draft
                await state.update_data(event_draft=draft, prompt_message_id=None)
    else:
        # Фото уже есть или удаляется, редактируем существующую карточку
        await _update_card(message, state)
        await state.update_data(event_draft=draft, prompt_message_id=None)
    
    await state.set_state(None)


@router.message(EventForm.waiting_for_board_games)
async def set_board_games(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    draft["board_games"] = (message.text or "").strip() or None
    await state.update_data(event_draft=draft)
    await _delete_prompt_and_input(message, state)
    await _update_card(message, state)
    await state.set_state(None)
    data.pop("prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventForm.waiting_for_datetime)
async def set_datetime(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    raw = (message.text or "").strip()
    parsed = parse_event_datetime(raw)
    if not parsed:
        await message.answer(
            "Некорректный формат. Используйте один из:\n"
            "- DD.MM.YYYY HH:MM (напр., 25.08.2025 18:30)\n"
            "- DD/MM/YYYY HH:MM\n"
            "- YYYY-MM-DD HH:MM"
        )
        return
    if not is_future_datetime_str(parsed):
        await message.answer("Время должно быть в будущем")
        return
    draft["datetime"] = parsed
    await state.update_data(event_draft=draft)
    await _delete_prompt_and_input(message, state)
    await _update_card(message, state)
    await state.set_state(None)
    data.pop("prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventForm.waiting_for_responsible)
async def set_responsible(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    draft["responsible"] = (message.text or "").strip() or None
    await state.update_data(event_draft=draft)
    await _delete_prompt_and_input(message, state)
    await _update_card(message, state)
    await state.set_state(None)
    data.pop("prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventForm.waiting_for_quantity)
async def set_quantity(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    value = (message.text or "").strip()
    try:
        qty = int(value)
    except Exception:
        await message.answer("Введите целое число")
        return
    data = await state.get_data()
    draft = data.get("event_draft") or {}
    draft["quantity"] = qty
    await state.update_data(event_draft=draft)
    await _delete_prompt_and_input(message, state)
    await _update_card(message, state)
    await state.set_state(None)
    data.pop("prompt_message_id", None)
    await state.update_data(**data)


@router.callback_query(F.data == "evt:confirm")
async def cb_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    data = await state.get_data()
    draft = ensure_draft_keys(data.get("event_draft") or {})
    missing = draft_missing_fields(draft)
    if missing:
        fields_rus = {
            "title": "Название",
            "description": "Описание",
            "photo": "Картинка",
            "board_games": "Настолки",
            "datetime": "Дата и время",
            "responsible": "Ответственные",
            "quantity": "Количество участников",
        }
        pretty = ", ".join(fields_rus.get(m, m) for m in missing)
        await callback.answer(f"Заполните: {pretty}", show_alert=True)
        return

    # Показываем финальные кнопки: Сохранить / Назад
    try:
        chat_id = data.get("card_chat_id")
        msg_id = data.get("card_message_id")
        if chat_id and msg_id:
            await callback.message.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=msg_id,
                reply_markup=build_final_confirm_keyboard(),
            )
    except Exception:
        pass
    await callback.answer("Проверьте карточку и подтвердите сохранение", show_alert=True)


@router.callback_query(F.data == "evt:final_cancel")
async def cb_final_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    data = await state.get_data()
    draft = ensure_draft_keys(data.get("event_draft") or {})
    # Возвращаем клавиатуру редактирования
    try:
        chat_id = data.get("card_chat_id")
        msg_id = data.get("card_message_id")
        if chat_id and msg_id:
            await callback.message.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=msg_id,
                reply_markup=build_event_inline_keyboard(draft),
            )
    except Exception:
        pass
    await callback.answer("Продолжайте редактирование", show_alert=False)


@router.callback_query(F.data == "evt:final_confirm")
async def cb_final_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    data = await state.get_data()
    draft = ensure_draft_keys(data.get("event_draft") or {})
    supabase = get_supabase()
    try:
        payload = {
            "title": draft.get("title"),
            "description": draft.get("description"),
            "photo": draft.get("photo"),
            "board_games": draft.get("board_games"),
            "date": draft.get("datetime"),
            "responsible": draft.get("responsible"),
            "quantity": draft.get("quantity"),
        }
        supabase.table("events").insert(payload).execute()
        await callback.answer("Мероприятие добавлено", show_alert=True)
        # Убираем клавиатуру у карточки
        try:
            chat_id = data.get("card_chat_id")
            msg_id = data.get("card_message_id")
            if chat_id and msg_id:
                await callback.message.bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
        except Exception:
            pass
        await state.clear()
    except Exception as e:
        try:
            print(f"EVENT_SAVE_ERROR: {e}")
        except Exception:
            pass
        await callback.answer("Ошибка сохранения. Попробуйте позже", show_alert=True)


@router.callback_query(F.data.startswith("event:edit:"))
async def on_edit_event(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает редактирование мероприятия"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия
    try:
        event_index = int(callback.data.split(":")[2])
    except Exception:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    if event_index < 0 or event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index] or {}
    
    # Инициализируем черновик редактирования из существующих данных
    edit_draft = {
        "title": event.get("title"),
        "description": event.get("description"),
        "photo": event.get("photo"),
        "board_games": event.get("board_games"),
        # Храним и date, и datetime, чтобы корректно работали галочки и финальная карточка
        "date": event.get("date"),
        "datetime": event.get("date"),
        "responsible": event.get("responsible"),
        "quantity": event.get("quantity"),
    }
    
    # Показываем экран редактирования (редактируем текущее сообщение)
    keyboard = build_event_edit_keyboard(edit_draft)
    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption="✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
                reply_markup=keyboard,
            )
        else:
            await callback.message.edit_text(
                text="✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
                reply_markup=keyboard,
            )
    except Exception as e:
        try:
            print(f"EDIT_START_ERROR: {e}")
        except Exception:
            pass
    
    # Сохраняем состояние редактирования
    await state.update_data(
        edit_draft=edit_draft,
        original_event={k: event.get(k) for k in [
            "id", "title", "description", "photo", "board_games", "date", "responsible", "quantity",
        ]},
        editing_event_index=event_index,
        edit_card_message_id=callback.message.message_id,
        edit_prompt_message_id=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event:participants:"))
async def on_show_participants(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает список участников мероприятия"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Получаем список участников
    participants = get_event_participants(event.get("id"))
    
    if not participants:
        await callback.answer("На это мероприятие пока никто не зарегистрирован", show_alert=True)
        return
    
    # Сохраняем список участников в состоянии
    await state.update_data(participants_list=participants)
    
    # Формируем текст сообщения
    registered_count = len([p for p in participants if p.get("status") == "registered"])
    waitlist_count = len([p for p in participants if p.get("status") == "waitlist"])
    
    message_text = f"👥 **Участники мероприятия:** {event.get('title', 'Без названия')}\n\n"
    message_text += f"✅ Зарегистрировано: {registered_count}\n"
    message_text += f"⏳ В очереди: {waitlist_count}\n\n"
    message_text += "Выберите участника для просмотра подробной информации:"
    
    # Создаем клавиатуру со списком участников
    keyboard = build_participants_list_keyboard(participants, event_index)
    
    # Обновляем сообщение
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=message_text,
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("participant:show:"))
async def on_show_participant_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает подробную информацию об участнике"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индексы из callback_data
    parts = callback.data.split(":")
    event_index = int(parts[2])
    participant_index = int(parts[3])
    
    # Получаем список участников из состояния
    data = await state.get_data()
    participants = data.get("participants_list", [])
    
    if participant_index >= len(participants):
        await callback.answer("Участник не найден", show_alert=True)
        return
    
    participant = participants[participant_index]
    username = participant.get("username", "Неизвестный")
    
    # Получаем дополнительную информацию о пользователе
    user_info = get_user_info(username)
    registrations_count = get_user_registrations_count(username)
    
    # Формируем текст с информацией об участнике
    message_text = f"👤 Информация об участнике\n\n"
    message_text += f"Пользователь: {username}\n"
    message_text += f"Статус: "
    
    if participant.get("status") == "registered":
        message_text += "✅ Зарегистрирован\n"
    elif participant.get("status") == "waitlist":
        message_text += "⏳ В очереди ожидания\n"
    else:
        message_text += "❓ Неизвестный статус\n"
    
    if participant.get("registration_date"):
        message_text += f"Дата регистрации: {participant['registration_date']}\n"
    
    if user_info:
        if user_info.get("created_at"):
            message_text += f"В боте с: {user_info['created_at']}\n"
    
    message_text += f"Всего регистраций: {registrations_count}\n"
    
    # Создаем клавиатуру для управления участником
    keyboard = build_participant_info_keyboard(event_index, participant_index)
    
    # Безопасно обновляем сообщение
    await _safe_edit_message(callback.message, message_text, keyboard)
    
    await callback.answer()


@router.callback_query(F.data.startswith("participant:remove:"))
async def on_remove_participant(callback: CallbackQuery, state: FSMContext) -> None:
    """Удаляет участника с мероприятия"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индексы из callback_data
    parts = callback.data.split(":")
    event_index = int(parts[2])
    participant_index = int(parts[3])
    
    # Получаем данные из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    participants = data.get("participants_list", [])
    
    if event_index >= len(events) or participant_index >= len(participants):
        await callback.answer("Ошибка: мероприятие или участник не найден", show_alert=True)
        return
    
    event = events[event_index]
    participant = participants[participant_index]
    username = participant.get("username", "")
    
    # Удаляем участника с мероприятия
    if participant.get("status") == "registered":
        success = unregister_user_from_event(username, event.get("id"))
    elif participant.get("status") == "waitlist":
        success = remove_user_from_waitlist(username, event.get("id"))
    else:
        await callback.answer("Неизвестный статус участника", show_alert=True)
        return
    
    if success:
        await callback.answer("Участник удален с мероприятия", show_alert=True)
        
        # Обновляем список участников
        updated_participants = get_event_participants(event.get("id"))
        await state.update_data(participants_list=updated_participants)
        
        # Возвращаемся к списку участников
        await on_show_participants(callback, state)
    else:
        await callback.answer("Ошибка при удалении участника", show_alert=True)


@router.callback_query(F.data.startswith("participant:message:"))
async def on_message_participant(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает переписку с участником"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индексы из callback_data
    parts = callback.data.split(":")
    event_index = int(parts[2])
    participant_index = int(parts[3])
    
    # Получаем данные из состояния
    data = await state.get_data()
    participants = data.get("participants_list", [])
    
    if participant_index >= len(participants):
        await callback.answer("Участник не найден", show_alert=True)
        return
    
    participant = participants[participant_index]
    username = participant.get("username", "")
    
    # Сохраняем данные для отправки сообщения
    await state.update_data(
        message_target_username=username,
        message_event_index=event_index,
        message_participant_index=participant_index
    )
    
    # Переходим в состояние ожидания сообщения
    await state.set_state(MessageParticipantForm.waiting_for_message)
    
    # Показываем клавиатуру для отмены
    keyboard = build_cancel_message_keyboard(event_index, participant_index)
    
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=f"💬 Написать сообщение участнику {username}\n\nВведите текст сообщения:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            f"💬 Написать сообщение участнику {username}\n\nВведите текст сообщения:",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("participant:blacklist:"))
async def on_blacklist_participant(callback: CallbackQuery, state: FSMContext) -> None:
    """Добавляет участника в чёрный список"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индексы из callback_data
    parts = callback.data.split(":")
    event_index = int(parts[2])
    participant_index = int(parts[3])
    
    # Получаем данные из состояния
    data = await state.get_data()
    participants = data.get("participants_list", [])
    
    if participant_index >= len(participants):
        await callback.answer("Участник не найден", show_alert=True)
        return
    
    participant = participants[participant_index]
    username = participant.get("username", "")
    
    # Сохраняем данные для добавления в черный список
    await state.update_data(
        blacklist_target_username=username,
        blacklist_event_index=event_index,
        blacklist_participant_index=participant_index
    )
    
    # Переходим в состояние ожидания причины
    await state.set_state(BlacklistForm.waiting_for_reason)
    
    # Показываем клавиатуру для подтверждения
    keyboard = build_blacklist_confirm_keyboard(event_index, participant_index)
    
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=f"🚫 Добавить участника {username} в черный список\n\nВведите причину добавления в черный список:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            f"🚫 Добавить участника {username} в черный список\n\nВведите причину добавления в черный список:",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("event:blacklist:"))
async def on_event_blacklist(callback: CallbackQuery, state: FSMContext) -> None:
    """Проксирует к полноценному показу чёрного списка ниже"""
    await on_show_event_blacklist(callback, state)


@router.callback_query(F.data.startswith("event:broadcast:"))
async def on_event_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Старт ввода текста рассылки"""
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    event_index = int(callback.data.split(":")[2])
    data = await state.get_data()
    events = data.get("events_list", [])
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    await state.update_data(broadcast_event_index=event_index)
    await state.set_state(BroadcastForm.waiting_for_message)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data=f"event:broadcast_cancel:{event_index}")]])
    await _safe_edit_message(callback.message, "💬 Введите текст рассылки для участников этого мероприятия:", kb)


@router.callback_query(F.data.startswith("event:broadcast_cancel:"))
async def on_event_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    event_index = int(parts[2])
    data = await state.get_data()
    await state.clear()
    await state.update_data(events_list=data.get("events_list", []), participants_list=data.get("participants_list", []))
    # Вернуть карточку мероприятия
    await on_show_event_details(callback, state)


@router.message(BroadcastForm.waiting_for_message)
async def on_event_broadcast_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    event_index = data.get("broadcast_event_index")
    events = data.get("events_list", [])
    if event_index is None or event_index >= len(events):
        await message.answer("Ошибка: мероприятие не найдено")
        await state.clear()
        return
    event = events[event_index]
    event_id = event.get("id")
    
    # Получаем всех участников (зарегистрированные и в очереди)
    participants = get_event_participants(event_id)
    if not participants:
        await message.answer("Нет получателей для рассылки")
        await state.clear()
        return
    
    sent = 0
    failed = 0
    text = message.text
    for p in participants:
        username = p.get("username")
        chat_id = get_user_chat_id(username)
        if not chat_id:
            failed += 1
            continue
        try:
            await message.bot.send_message(chat_id=chat_id, text=text)
            sent += 1
        except Exception as e:
            print(f"ERROR broadcast to {username}: {e}")
            failed += 1
    
    await message.answer(f"✅ Рассылка завершена\nОтправлено: {sent}\nНе доставлено: {failed}")
    await state.clear()


@router.callback_query(F.data.startswith("event:cancel:"))
async def on_cancel_event_request(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    event_index = int(callback.data.split(":")[2])
    data = await state.get_data()
    events = data.get("events_list", [])
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить отмену", callback_data=f"event:cancel_confirm:{event_index}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"event:show:{event_index}")]
    ])
    await _safe_edit_message(callback.message, "⚠️ Вы уверены, что хотите отменить мероприятие?", kb)


@router.callback_query(F.data.startswith("event:cancel_confirm:"))
async def on_cancel_event_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    event_index = int(callback.data.split(":")[2])
    data = await state.get_data()
    events = data.get("events_list", [])
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    event = events[event_index]
    event_id = event.get("id")
    # Помечаем в БД как отменённое
    try:
        supabase = get_supabase()
        supabase.table("events").update({"is_cancelled": True}).eq("id", event_id).execute()
        # Обновляем локальные данные
        event["is_cancelled"] = True
        events[event_index] = event
        await state.update_data(events_list=events)
    except Exception as e:
        print(f"ERROR cancelling event: {e}")
        await callback.answer("Ошибка при отмене", show_alert=True)
        return
    # Уведомляем участников
    try:
        participants = get_event_participants(event_id)
        notify_text = f"❌ Мероприятие \"{event.get('title')}\" отменено. Приносим извинения."
        for p in participants:
            chat_id = get_user_chat_id(p.get("username"))
            if chat_id:
                try:
                    await callback.bot.send_message(chat_id=chat_id, text=notify_text)
                except Exception as e:
                    print(f"ERROR notifying cancel to {p.get('username')}: {e}")
    except Exception as e:
        print(f"ERROR collecting participants to notify: {e}")
    # Вернёмся к карточке
    await on_show_event_details(callback, state)


# Обработчики для редактирования мероприятия
@router.callback_query(F.data == "evt_edit:title")
async def cb_edit_title(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_edit_state(callback, state, "Введите новое название мероприятия:", EventEditForm.waiting_for_title)


@router.callback_query(F.data == "evt_edit:description")
async def cb_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_edit_state(callback, state, "Введите новое описание мероприятия:", EventEditForm.waiting_for_description)


@router.callback_query(F.data == "evt_edit:photo")
async def cb_edit_photo(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_edit_state(callback, state, "Отправьте новую ссылку на картинку или просто прикрепите фото сообщением:", EventEditForm.waiting_for_photo)


@router.callback_query(F.data == "evt_edit:board_games")
async def cb_edit_board_games(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    games = get_board_games()
    data = await state.get_data()
    current = (data.get("edit_draft") or {}).get("board_games") or ""
    selected = [s.strip() for s in current.split(",") if s.strip()]
    await state.update_data(evt_edit_board_games_all=games, evt_edit_board_games_selected=selected)
    from ..keyboards import build_board_games_selection_keyboard
    kb = build_board_games_selection_keyboard(games, selected, done_callback="evt_edit:board_games_done", toggle_prefix="evt_edit:board_games_toggle", back_callback="evt_edit:board_games_back")
    await _safe_edit_message(callback.message, "Выберите настолки (можно несколько):", kb)


@router.callback_query(F.data == "evt_edit:datetime")
async def cb_edit_datetime(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_edit_state(callback, state, "Введите новую дату и время (любой текстовый формат):", EventEditForm.waiting_for_datetime)


@router.callback_query(F.data == "evt_edit:responsible")
async def cb_edit_responsible(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    admins = get_all_admins()
    data = await state.get_data()
    current = (data.get("edit_draft") or {}).get("responsible") or ""
    selected = [s.strip() for s in current.split(",") if s.strip()]
    await state.update_data(edit_responsible_admins=admins, edit_selected_responsibles=selected)
    kb = build_admins_selection_keyboard(admins, selected, done_callback="evt_edit:responsible_done", toggle_prefix="evt_edit:responsible_toggle", back_callback="evt_edit:responsible_back")
    await _safe_edit_message(callback.message, "Выберите ответственных (можно несколько):", kb)
    await state.set_state(ResponsibleSelectionForm.waiting_for_responsibles)


@router.callback_query(F.data == "evt_edit:quantity")
async def cb_edit_quantity(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    await _ask_and_set_edit_state(callback, state, "Введите новое количество участников (число):", EventEditForm.waiting_for_quantity)


@router.callback_query(F.data == "evt_edit:confirm")
async def cb_edit_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    
    # Показываем финальную карточку для подтверждения
    keyboard = build_edit_final_confirm_keyboard()
    
    # Форматируем текст карточки
    card_text = format_event_text(edit_draft)
    
    # Редактируем сообщение с финальной карточкой
    if callback.message.photo:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=edit_draft.get("photo", ""),
                caption=card_text
            ),
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            card_text,
            reply_markup=keyboard
        )
    
    await callback.answer("Проверьте карточку и подтвердите изменения", show_alert=True)


@router.callback_query(F.data == "evt_edit:cancel")
async def cb_edit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Возвращаемся к деталям мероприятия
    data = await state.get_data()
    events = data.get("events_list", [])
    event_index = data.get("editing_event_index")
    
    if event_index is not None and event_index < len(events):
        event = events[event_index]
        
        # Форматируем детали мероприятия
        details = f"📋 {event.get('title', 'Без названия')}\n\n"
        
        if event.get("is_completed", False):
            details += "✅ **МЕРОПРИЯТИЕ ЗАВЕРШЕНО**\n\n"
        
        if event.get("description"):
            details += f"📝 Описание: {event['description']}\n\n"
        
        if event.get("board_games"):
            details += f"🎲 Настольные игры: {event['board_games']}\n\n"
        
        if event.get("date"):
            details += f"📅 Дата и время: {event['date']}\n\n"
        
        if event.get("responsible"):
            details += f"👥 Ответственные: {event['responsible']}\n\n"
        
        if event.get("quantity"):
            details += f"👤 Количество участников: {event['quantity']}\n\n"
        
        # Создаем клавиатуру для деталей мероприятия
        keyboard = []
        if not event.get("is_completed", False):
            keyboard.append([InlineKeyboardButton(text="🏁 Завершить мероприятие", callback_data=f"event:complete:{event_index}")])
            keyboard.append([InlineKeyboardButton(text="✏️ Изменить мероприятие", callback_data=f"event:edit:{event_index}")])
            keyboard.append([InlineKeyboardButton(text="👥 Посмотреть участников", callback_data=f"event:participants:{event_index}")])
            keyboard.append([InlineKeyboardButton(text="🚫 Чёрный список", callback_data=f"event:blacklist:{event_index}")])
            keyboard.append([InlineKeyboardButton(text="📢 Отправить рассылку", callback_data=f"event:broadcast:{event_index}")])
            keyboard.append([InlineKeyboardButton(text="❌ Отменить мероприятие", callback_data=f"event:cancel:{event_index}")])
        
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="event:back_to_list")])
        
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
        
        # Редактируем сообщение
        if event.get("photo"):
            photo_value = event['photo']
            is_valid_file_id = (
                isinstance(photo_value, str) and 
                len(photo_value) > 20 and 
                not any(char in photo_value for char in [' ', '\n', '\t', 'ывп'])
            )
            
            if is_valid_file_id:
                try:
                    await callback.message.edit_media(
                        media=InputMediaPhoto(
                            media=photo_value,
                            caption=details
                        ),
                        reply_markup=inline_keyboard
                    )
                except Exception as e:
                    print(f"PHOTO_EDIT_ERROR: {e}")
                    await callback.message.edit_text(details, reply_markup=inline_keyboard)
            else:
                await callback.message.edit_text(details, reply_markup=inline_keyboard)
        else:
            await callback.message.edit_text(details, reply_markup=inline_keyboard)
    
    # Очищаем данные редактирования
    await state.update_data(edit_draft=None, editing_event_index=None, original_event=None)
    await callback.answer()


async def _ask_and_set_edit_state(callback: CallbackQuery, state: FSMContext, text: str, next_state):
    """Вспомогательная функция для установки состояния редактирования"""
    prompt = await callback.message.answer(text)
    await state.update_data(edit_prompt_message_id=prompt.message_id)
    await state.set_state(next_state)
    await callback.answer()


# Обработчики ввода для редактирования мероприятия
@router.message(EventEditForm.waiting_for_title)
async def edit_title(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    edit_draft["title"] = (message.text or "").strip() or None
    await state.update_data(edit_draft=edit_draft)
    await _delete_edit_prompt_and_input(message, state)
    await _update_edit_card(message, state)
    await state.set_state(None)
    data.pop("edit_prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventEditForm.waiting_for_description)
async def edit_description(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    edit_draft["description"] = (message.text or "").strip() or None
    await state.update_data(edit_draft=edit_draft)
    await _delete_edit_prompt_and_input(message, state)
    await _update_edit_card(message, state)
    await state.set_state(None)
    data.pop("edit_prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventEditForm.waiting_for_photo)
async def edit_photo(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    photo_value: Optional[str] = None
    if message.photo:
        try:
            photo_value = message.photo[-1].file_id
        except Exception:
            photo_value = None
    if not photo_value:
        photo_value = (message.text or "").strip() or None
    
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    old_photo = edit_draft.get("photo")
    edit_draft["photo"] = photo_value
    await _delete_edit_prompt_and_input(message, state)
    
    # Если фото добавляется впервые, пересоздаём карточку
    if not old_photo and photo_value:
        try:
            # Удаляем старое текстовое сообщение
            await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
            # Отправляем новое с фото
            sent = await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=photo_value,
                caption="✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
                reply_markup=build_event_edit_keyboard(edit_draft)
            )
            # Обновляем состояние с новым ID сообщения
            await state.update_data(
                edit_draft=edit_draft,
                edit_card_message_id=sent.message_id,
                edit_prompt_message_id=None
            )
        except Exception as e:
            print(f"EDIT_PHOTO_CREATE_ERROR: {e}")
            await state.update_data(edit_draft=edit_draft, edit_prompt_message_id=None)
    else:
        # Фото уже есть или удаляется, редактируем существующую карточку
        await _update_edit_card(message, state)
        await state.update_data(edit_draft=edit_draft, edit_prompt_message_id=None)
    
    await state.set_state(None)


@router.message(EventEditForm.waiting_for_board_games)
async def edit_board_games(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    edit_draft["board_games"] = (message.text or "").strip() or None
    await state.update_data(edit_draft=edit_draft)
    await _delete_edit_prompt_and_input(message, state)
    await _update_edit_card(message, state)
    await state.set_state(None)
    data.pop("edit_prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventEditForm.waiting_for_datetime)
async def edit_datetime(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    raw = (message.text or "").strip()
    parsed = parse_event_datetime(raw)
    if not parsed:
        await message.answer(
            "Некорректный формат. Используйте один из:\n"
            "- DD.MM.YYYY HH:MM (напр., 25.08.2025 18:30)\n"
            "- DD/MM/YYYY HH:MM\n"
            "- YYYY-MM-DD HH:MM"
        )
        return
    if not is_future_datetime_str(parsed):
        await message.answer("Время должно быть в будущем")
        return
    edit_draft["datetime"] = parsed
    edit_draft["date"] = parsed
    await state.update_data(edit_draft=edit_draft)
    await _delete_edit_prompt_and_input(message, state)
    await _update_edit_card(message, state)
    await state.set_state(None)
    data.pop("edit_prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventEditForm.waiting_for_responsible)
async def edit_responsible(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    edit_draft["responsible"] = (message.text or "").strip() or None
    await state.update_data(edit_draft=edit_draft)
    await _delete_edit_prompt_and_input(message, state)
    await _update_edit_card(message, state)
    await state.set_state(None)
    data.pop("edit_prompt_message_id", None)
    await state.update_data(**data)


@router.message(EventEditForm.waiting_for_quantity)
async def edit_quantity(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        return
    value = (message.text or "").strip()
    try:
        qty = int(value)
    except Exception:
        await message.answer("Введите целое число")
        return
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    edit_draft["quantity"] = qty
    await state.update_data(edit_draft=edit_draft)
    await _delete_edit_prompt_and_input(message, state)
    await _update_edit_card(message, state)
    await state.set_state(None)
    data.pop("edit_prompt_message_id", None)
    await state.update_data(**data)


async def _delete_edit_prompt_and_input(message: Message, state: FSMContext) -> None:
    """Удаляет промпт и ввод пользователя при редактировании"""
    data = await state.get_data()
    prompt_id = data.get("edit_prompt_message_id")
    if prompt_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_id)
        except Exception:
            pass
    try:
        await message.delete()
    except Exception:
        pass


async def _update_edit_card(message: Message, state: FSMContext) -> None:
    """Обновляет карточку редактирования"""
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    card_msg_id = data.get("edit_card_message_id")
    
    if card_msg_id:
        try:
            # Если есть фото, редактируем caption у фото-сообщения
            if edit_draft.get("photo"):
                await message.bot.edit_message_caption(
                    chat_id=message.chat.id,
                    message_id=card_msg_id,
                    caption="✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
                    reply_markup=build_event_edit_keyboard(edit_draft),
                )
            else:
                # Нет фото, редактируем как текст
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=card_msg_id,
                    text="✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
                    reply_markup=build_event_edit_keyboard(edit_draft),
                )
        except Exception as e:
            print(f"UPDATE_EDIT_CARD_ERROR: {e}")
            # Если не удалось отредактировать, пытаемся как текст
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=card_msg_id,
                    text="✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
                    reply_markup=build_event_edit_keyboard(edit_draft),
                )
            except Exception:
                pass


# Обработчики финального подтверждения редактирования
@router.callback_query(F.data == "evt_edit:final_confirm")
async def cb_edit_final_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    original_event = data.get("original_event", {})
    
    supabase = get_supabase()
    try:
        # Обновляем мероприятие в базе данных
        payload = {
            "title": edit_draft.get("title"),
            "description": edit_draft.get("description"),
            "photo": edit_draft.get("photo"),
            "board_games": edit_draft.get("board_games"),
            "date": edit_draft.get("datetime"),  # Используем "datetime" из draft как "date" в БД
            "responsible": edit_draft.get("responsible"),
            "quantity": edit_draft.get("quantity"),
        }
        
        # Используем title для идентификации мероприятия
        supabase.table("events").update(payload).eq("title", original_event.get("title")).execute()
        
        await callback.answer("Мероприятие обновлено! ✅", show_alert=True)
        
        # Возвращаемся к деталям обновлённого мероприятия
        events = data.get("events_list", [])
        event_index = data.get("editing_event_index")
        
        if event_index is not None and event_index < len(events):
            # Обновляем мероприятие в локальном списке
            events[event_index].update(payload)
            
            # Форматируем детали обновлённого мероприятия
            details = f"📋 {payload.get('title', 'Без названия')}\n\n"
            
            if events[event_index].get("is_completed", False):
                details += "✅ **МЕРОПРИЯТИЕ ЗАВЕРШЕНО**\n\n"
            
            if payload.get("description"):
                details += f"📝 Описание: {payload['description']}\n\n"
            
            if payload.get("board_games"):
                details += f"🎲 Настольные игры: {payload['board_games']}\n\n"
            
            if payload.get("date"):
                details += f"📅 Дата и время: {payload['date']}\n\n"
            
            if payload.get("responsible"):
                details += f"👥 Ответственные: {payload['responsible']}\n\n"
            
            if payload.get("quantity"):
                details += f"👤 Количество участников: {payload['quantity']}\n\n"
            
            # Создаем клавиатуру для деталей мероприятия
            keyboard = []
            if not events[event_index].get("is_completed", False):
                keyboard.append([InlineKeyboardButton(text="🏁 Завершить мероприятие", callback_data=f"event:complete:{event_index}")])
                keyboard.append([InlineKeyboardButton(text="✏️ Изменить мероприятие", callback_data=f"event:edit:{event_index}")])
                keyboard.append([InlineKeyboardButton(text="👥 Посмотреть участников", callback_data=f"event:participants:{event_index}")])
                keyboard.append([InlineKeyboardButton(text="🚫 Чёрный список", callback_data=f"event:blacklist:{event_index}")])
                keyboard.append([InlineKeyboardButton(text="📢 Отправить рассылку", callback_data=f"event:broadcast:{event_index}")])
                keyboard.append([InlineKeyboardButton(text="❌ Отменить мероприятие", callback_data=f"event:cancel:{event_index}")])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="event:back_to_list")])
            
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
            
            # Обновляем сообщение
            if payload.get("photo"):
                photo_value = payload['photo']
                is_valid_file_id = (
                    isinstance(photo_value, str) and 
                    len(photo_value) > 20 and 
                    not any(char in photo_value for char in [' ', '\n', '\t', 'ывп'])
                )
                
                if is_valid_file_id:
                    try:
                        await callback.message.edit_media(
                            media=InputMediaPhoto(
                                media=photo_value,
                                caption=details
                            ),
                            reply_markup=inline_keyboard
                        )
                    except Exception as e:
                        print(f"PHOTO_EDIT_ERROR: {e}")
                        await callback.message.edit_text(details, reply_markup=inline_keyboard)
                else:
                    await callback.message.edit_text(details, reply_markup=inline_keyboard)
            else:
                await callback.message.edit_text(details, reply_markup=inline_keyboard)
        
        # Уведомляем участников об изменениях
        try:
            event_id = events[event_index].get("id")
            # Берём только зарегистрированных, без очереди
            regs = get_event_registrations(event_id)
            # Определяем изменения
            changes = []
            def add_change(label: str, old_val, new_val):
                if (old_val or "") != (new_val or ""):
                    changes.append(f"- {label}: {new_val if new_val else '—'}")
            add_change("Название", original_event.get("title"), payload.get("title"))
            add_change("Описание", original_event.get("description"), payload.get("description"))
            add_change("Картинка", bool(original_event.get("photo")), bool(payload.get("photo")))
            add_change("Настолки", original_event.get("board_games"), payload.get("board_games"))
            add_change("Дата и время", original_event.get("date"), payload.get("date"))
            add_change("Ответственные", original_event.get("responsible"), payload.get("responsible"))
            add_change("Количество участников", str(original_event.get("quantity")), str(payload.get("quantity")))
            changes_text = "\n".join(changes) if changes else "(детали обновлены)"
            notify_text = (
                f"📢 Обновление мероприятия \"{events[event_index].get('title') or 'Мероприятие'}\"\n\n"
                f"Изменено:\n{changes_text}"
            )
            for p in regs:
                username = (p.get("users") or {}).get("tg_username") or p.get("user_tg_username")
                chat_id = get_user_chat_id(username)
                if not chat_id:
                    continue
                try:
                    await callback.bot.send_message(chat_id=chat_id, text=notify_text)
                except Exception as e:
                    print(f"ERROR notifying edit to {username}: {e}")
        except Exception as e:
            print(f"ERROR during edit notifications: {e}")
        
        # Очищаем данные редактирования
        await state.update_data(edit_draft=None, editing_event_index=None, original_event=None)
        
    except Exception as e:
        print(f"EVENT_UPDATE_ERROR: {e}")
        await callback.answer("Ошибка обновления. Попробуйте позже", show_alert=True)


@router.callback_query(F.data == "evt_edit:final_cancel")
async def cb_edit_final_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    data = await state.get_data()
    edit_draft = data.get("edit_draft", {})
    
    # Возвращаемся к клавиатуре редактирования
    keyboard = build_event_edit_keyboard(edit_draft)
    
    # Редактируем сообщение
    if callback.message.photo:
        await callback.message.edit_caption(
            caption="✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "✏️ Редактирование мероприятия\n\nВыберите поле для изменения:",
            reply_markup=keyboard
        )
    
    await callback.answer("Продолжайте редактирование", show_alert=False)


@router.message(lambda m: m.text == "Зарегистрироваться на мероприятие")
async def on_register_for_event(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return
    
    # Проверяем, не является ли пользователь админом
    if user_is_admin(user.username):
        await message.answer("Админы не могут регистрироваться на мероприятия")
        return
    
    supabase = get_supabase()
    try:
        # Получаем только незавершённые и неотменённые мероприятия
        response = (
            supabase
            .table("events")
            .select("*")
            .eq("is_completed", False)
            .eq("is_cancelled", False)
            .execute()
        )
        events = response.data
        
        if not events:
            await message.answer("Пока нет доступных мероприятий для регистрации")
            return
        
        # Сортируем по дате
        events.sort(key=lambda x: x.get("date", ""), reverse=False)
        
        # Сохраняем список мероприятий в состоянии
        await state.update_data(events_list=events)
        
        # Создаем клавиатуру со списком мероприятий
        keyboard = build_events_list_keyboard(events)
        
        await message.answer(
            f"Доступные мероприятия для регистрации ({len(events)}):\n\nВыберите мероприятие:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        print(f"REGISTER_EVENTS_ERROR: {e}")
        await message.answer("Ошибка при загрузке мероприятий")


@router.message(lambda m: m.text == "Настольные игры")
async def on_admin_games_menu(message: Message, state: FSMContext) -> None:
    if not user_is_admin(message.from_user.username if message.from_user else None):
        await message.answer("Доступно только админам")
        return
    games = get_board_games()
    await state.update_data(board_games_list=games)
    kb = build_games_list_keyboard(games)
    await message.answer("🎲 Настольные игры:", reply_markup=kb)


@router.message(lambda m: m.text == "Мои мероприятия")
async def on_my_events(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return
    
    # Проверяем, не является ли пользователь админом
    if user_is_admin(user.username):
        await message.answer("Эта функция недоступна для админов")
        return
    
    # Получаем регистрации пользователя и отфильтровываем завершённые/отменённые
    registrations = get_user_registrations(user.username)
    
    if not registrations:
        await message.answer("У вас пока нет зарегистрированных мероприятий")
        return
    
    # Формируем список мероприятий (исключая завершённые/отменённые)
    events = []
    for reg in registrations:
        event = reg.get("events")
        if not event:
            continue
        if event.get("is_completed") or event.get("is_cancelled"):
            continue
        events.append(event)
    
    if not events:
        await message.answer("У вас пока нет зарегистрированных мероприятий")
        return
    
    # Сохраняем список мероприятий в состоянии
    await state.update_data(events_list=events)
    
    # Создаем клавиатуру со списком мероприятий
    keyboard = build_events_list_keyboard(events)
    
    await message.answer(
        f"Мои мероприятия ({len(events)}):\n\nВыберите мероприятие для просмотра деталей:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("event:register:"))
async def on_register_for_event_callback(callback: CallbackQuery, state: FSMContext) -> None:
    # Проверяем, не является ли пользователь админом
    if user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Админы не могут регистрироваться на мероприятия", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Блокируем если отменено
    if event.get("is_cancelled", False):
        await callback.answer("Мероприятие отменено", show_alert=True)
        return
    
    # Проверяем, не зарегистрирован ли уже пользователь
    if is_user_registered_for_event(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        await callback.answer("Вы уже зарегистрированы на это мероприятие", show_alert=True)
        return
    
    # Проверяем, не заполнено ли мероприятие
    if is_event_full(event.get("id")):
        await callback.answer("К сожалению, все места на это мероприятие уже заняты", show_alert=True)
        return
    
    # Проверяем, не находится ли пользователь в черном списке
    if is_user_in_event_blacklist(event.get("id"), callback.from_user.username if callback.from_user else None):
        await callback.answer("Вы находитесь в черном списке этого мероприятия", show_alert=True)
        return
    # Глобальный ЧС
    try:
        from ..utils import get_global_blacklist
        gbl = get_global_blacklist()
        tg = (callback.from_user.username or "")
        tg = tg if tg.startswith("@") else (f"@{tg}" if tg else tg)
        if any(item.get("user_tg_username") == tg for item in gbl):
            await callback.answer("Вы заблокированы для участия в мероприятиях", show_alert=True)
            return
    except Exception:
        pass
    
    # Регистрируем пользователя
    if register_user_for_event(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        # Сохраняем chat_id пользователя в базе данных
        ensure_user_exists(
            callback.from_user.username if callback.from_user else None,
            callback.from_user.id if callback.from_user else None
        )
        
        # Получаем обновленную информацию о доступных местах
        available_slots = get_event_available_slots_count(event.get("id"))
        if available_slots == 0:
            message = "Вы успешно зарегистрированы на мероприятие! ✅\n\n🎫 Это было последнее свободное место!"
        elif available_slots == -1:
            message = "Вы успешно зарегистрированы на мероприятие! ✅"
        else:
            message = f"Вы успешно зарегистрированы на мероприятие! ✅\n\n🎫 Осталось свободных мест: {available_slots}"
        
        await callback.answer(message, show_alert=True)
        
        # Отправляем уведомление о регистрации
        try:
            event_info = f"📋 {event.get('title', 'Мероприятие')}\n📅 {event.get('date', 'Дата не указана')}\n📍 {event.get('responsible', 'Ответственные не указаны')}"
            
            if available_slots == 0:
                notification_text = f"✅ **Регистрация подтверждена!**\n\n{event_info}\n\n🎫 Вы заняли последнее свободное место!\n\nЖдём вас на мероприятии! 🎉"
            elif available_slots == -1:
                notification_text = f"✅ **Регистрация подтверждена!**\n\n{event_info}\n\n🎫 Количество мест не ограничено\n\nЖдём вас на мероприятии! 🎉"
            else:
                notification_text = f"✅ **Регистрация подтверждена!**\n\n{event_info}\n\n🎫 Осталось свободных мест: {available_slots}\n\nЖдём вас на мероприятии! 🎉"
            
            await callback.bot.send_message(
                chat_id=callback.from_user.id,
                text=notification_text
            )
        except Exception as notify_error:
            print(f"ERROR sending registration notification: {notify_error}")
            # Уведомление не критично, продолжаем работу
        
        # Обновляем кнопку на "Отменить регистрацию"
        keyboard = []
        keyboard.append([InlineKeyboardButton(text="❌ Отменить регистрацию", callback_data=f"event:unregister:{event_index}")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="event:back_to_list")])
        
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Обновляем сообщение
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=callback.message.caption,
                reply_markup=inline_keyboard
            )
        else:
            await callback.message.edit_reply_markup(reply_markup=inline_keyboard)
    else:
        await callback.answer("Ошибка при регистрации. Попробуйте позже", show_alert=True)


@router.callback_query(F.data.startswith("event:unregister:"))
async def on_unregister_from_event_callback(callback: CallbackQuery, state: FSMContext) -> None:
    # Проверяем, не является ли пользователь админом
    if user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Админы не могут отменять регистрации", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Проверяем, зарегистрирован ли пользователь
    if not is_user_registered_for_event(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        await callback.answer("Вы не зарегистрированы на это мероприятие", show_alert=True)
        return
    
    # Отменяем регистрацию
    if unregister_user_from_event(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        # Получаем обновленную информацию о доступных местах
        available_slots = get_event_available_slots_count(event.get("id"))
        
        # Проверяем, есть ли люди в очереди ожидания
        supabase = get_supabase()
        try:
            # Получаем первого пользователя из очереди
            waitlist_resp = (
                supabase
                .table("event_registrations")
                .select("user_tg_username, id")
                .eq("event_id", event.get("id"))
                .eq("status", "waitlist")
                .order("registration_date", desc=False)
                .limit(1)
                .execute()
            )
            
            if waitlist_resp.data and len(waitlist_resp.data) > 0:
                # Автоматически регистрируем первого из очереди
                first_in_waitlist = waitlist_resp.data[0]
                supabase.table("event_registrations").update({
                    "status": "registered",
                    "registration_date": "NOW()"
                }).eq("id", first_in_waitlist["id"]).execute()
                
                # Обновляем количество доступных мест
                available_slots = get_event_available_slots_count(event.get("id"))
                
                message = f"Регистрация отменена\n\n🎫 Свободных мест: {available_slots}\n\n✅ Первый из очереди автоматически зарегистрирован!"
                
                # Отправляем уведомление пользователю, который автоматически зарегистрировался
                try:
                    # Убираем символ @ из username для поиска пользователя
                    notify_username = first_in_waitlist["user_tg_username"].lstrip("@")
                    
                    # Получаем chat_id пользователя из базы данных
                    user_chat_id = get_user_chat_id(notify_username)
                    
                    if user_chat_id:
                        # Получаем информацию о мероприятии для уведомления
                        event_info = f"📋 {event.get('title', 'Мероприятие')}\n📅 {event.get('date', 'Дата не указана')}"
                        
                        notification_text = f"🎉 **Отличные новости!**\n\n{event_info}\n\n✅ Вы автоматически зарегистрированы на мероприятие!\n\nМесто освободилось, и вы были первым в очереди ожидания.\n\nЖдём вас на мероприятии!"
                        
                        # Отправляем уведомление через chat_id
                        await callback.bot.send_message(
                            chat_id=user_chat_id,
                            text=notification_text
                        )
                        print(f"NOTIFICATION_SENT: sent to chat_id {user_chat_id} (@{notify_username})")
                    else:
                        print(f"NOTIFICATION_FAILED: no chat_id found for @{notify_username}")
                except Exception as notify_error:
                    print(f"ERROR sending notification to {first_in_waitlist['user_tg_username']}: {notify_error}")
                    # Уведомление не критично, продолжаем работу
            else:
                if available_slots == 1:
                    message = "Регистрация отменена\n\n🎫 Теперь есть 1 свободное место!"
                elif available_slots == -1:
                    message = "Регистрация отменена"
                else:
                    message = f"Регистрация отменена\n\n🎫 Свободных мест: {available_slots}"
        except Exception as e:
            print(f"ERROR processing waitlist: {e}")
            if available_slots == 1:
                message = "Регистрация отменена\n\n🎫 Теперь есть 1 свободное место!"
            elif available_slots == -1:
                message = "Регистрация отменена"
            else:
                message = f"Регистрация отменена\n\n🎫 Свободных мест: {available_slots}"
        
        await callback.answer(message, show_alert=True)
    else:
        await callback.answer("Ошибка при отмене регистрации. Попробуйте позже", show_alert=True)


@router.callback_query(F.data.startswith("event:join_waitlist:"))
async def on_join_waitlist_callback(callback: CallbackQuery, state: FSMContext) -> None:
    # Проверяем, не является ли пользователь админом
    if user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Админы не могут занимать места в очереди", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Блокируем если отменено
    if event.get("is_cancelled", False):
        await callback.answer("Мероприятие отменено", show_alert=True)
        return
    
    # Проверяем, не завершено ли мероприятие
    if event.get("is_completed", False):
        await callback.answer("Регистрация на завершённые мероприятия невозможна", show_alert=True)
        return
    
    # Проверяем, не зарегистрирован ли уже пользователь
    if is_user_registered_for_event(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        await callback.answer("Вы уже зарегистрированы на это мероприятие", show_alert=True)
        return
    
    # Проверяем, не в очереди ли уже пользователь
    if is_user_on_waitlist(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        await callback.answer("Вы уже в очереди ожидания", show_alert=True)
        return
    
    # Проверяем, не находится ли пользователь в черном списке
    if is_user_in_event_blacklist(event.get("id"), callback.from_user.username if callback.from_user else None):
        await callback.answer("Вы находитесь в черном списке этого мероприятия", show_alert=True)
        return
    # Глобальный ЧС
    try:
        from ..utils import get_global_blacklist
        gbl = get_global_blacklist()
        tg = (callback.from_user.username or "")
        tg = tg if tg.startswith("@") else (f"@{tg}" if tg else tg)
        if any(item.get("user_tg_username") == tg for item in gbl):
            await callback.answer("Вы заблокированы для участия в мероприятиях", show_alert=True)
            return
    except Exception:
        pass
    
    # Проверяем, что мероприятие действительно заполнено
    if not is_event_full(event.get("id")):
        await callback.answer("Мероприятие не заполнено, используйте обычную регистрацию", show_alert=True)
        return
    
    # Добавляем в очередь ожидания
    if add_user_to_waitlist(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        # Сохраняем chat_id пользователя в базе данных
        ensure_user_exists(
            callback.from_user.username if callback.from_user else None,
            callback.from_user.id if callback.from_user else None
        )
        
        # Получаем позицию в очереди
        position = get_waitlist_position(
            callback.from_user.username if callback.from_user else None,
            event.get("id")
        )
        
        message = f"Вы добавлены в очередь ожидания! ✅\n\n⏳ Ваша позиция: №{position}\n\nКогда освободится место, вы автоматически получите уведомление."
        await callback.answer(message, show_alert=True)
        
        # Отправляем уведомление о добавлении в очередь
        try:
            event_info = f"📋 {event.get('title', 'Мероприятие')}\n📅 {event.get('date', 'Дата не указана')}"
            waitlist_text = f"⏳ **Вы в очереди ожидания!**\n\n{event_info}\n\n🎫 Ваша позиция: №{position}\n\nКогда освободится место, вы автоматически получите уведомление о регистрации! 📱"
            
            await callback.bot.send_message(
                chat_id=callback.from_user.id,
                text=waitlist_text
            )
        except Exception as notify_error:
            print(f"ERROR sending waitlist notification: {notify_error}")
            # Уведомление не критично, продолжаем работу
        
        # Обновляем кнопку на "В очереди"
        keyboard = []
        keyboard.append([InlineKeyboardButton(text=f"⏳ В очереди (№{position})", callback_data=f"event:leave_waitlist:{event_index}")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="event:back_to_list")])
        
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Обновляем сообщение
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=callback.message.caption,
                reply_markup=inline_keyboard
            )
        else:
            await callback.message.edit_reply_markup(reply_markup=inline_keyboard)
    else:
        await callback.answer("Ошибка при добавлении в очередь. Попробуйте позже", show_alert=True)


@router.callback_query(F.data.startswith("event:leave_waitlist:"))
async def on_leave_waitlist_callback(callback: CallbackQuery, state: FSMContext) -> None:
    # Проверяем, не является ли пользователь админом
    if user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Админы не могут покидать очередь", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем список мероприятий из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Проверяем, в очереди ли пользователь
    if not is_user_on_waitlist(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        await callback.answer("Вы не в очереди ожидания", show_alert=True)
        return
    
    # Удаляем из очереди
    if remove_user_from_waitlist(
        callback.from_user.username if callback.from_user else None,
        event.get("id")
    ):
        await callback.answer("Вы покинули очередь ожидания", show_alert=True)
        
        # Обновляем кнопку на "Занять место" (если мероприятие всё ещё заполнено)
        keyboard = []
        # Проверяем, не заполнено ли мероприятие
        if is_event_full(event.get("id")):
            # Проверяем, не в очереди ли пользователь
            if is_user_on_waitlist(
                callback.from_user.username if callback.from_user else None,
                event.get("id")
            ):
                position = get_waitlist_position(
                    callback.from_user.username if callback.from_user else None,
                    event.get("id")
                )
                keyboard.append([InlineKeyboardButton(text=f"⏳ В очереди (№{position})", callback_data=f"event:leave_waitlist:{event_index}")])
            else:
                keyboard.append([InlineKeyboardButton(text="📋 Занять место", callback_data=f"event:join_waitlist:{event_index}")])
        else:
            keyboard.append([InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data=f"event:register:{event_index}")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="event:back_to_list")])
        
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Обновляем сообщение
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=callback.message.caption,
                reply_markup=inline_keyboard
            )
        else:
            await callback.message.edit_reply_markup(reply_markup=inline_keyboard)
    else:
        await callback.answer("Ошибка при выходе из очереди. Попробуйте позже", show_alert=True)


# Обработчики для отправки сообщений участникам
@router.message(MessageParticipantForm.waiting_for_message)
async def on_message_text_received(message: Message, state: FSMContext) -> None:
    """Обрабатывает текст сообщения для участника"""
    data = await state.get_data()
    target_username = data.get("message_target_username")
    event_index = data.get("message_event_index")
    participant_index = data.get("message_participant_index")
    
    if not target_username:
        await message.answer("Ошибка: получатель не найден")
        await state.clear()
        return
    
    # Получаем chat_id получателя
    target_chat_id = get_user_chat_id(target_username)
    
    if not target_chat_id:
        await message.answer(f"Не удалось отправить сообщение пользователю {target_username}. Возможно, он не запускал бота.")
        await state.clear()
        return
    
    try:
        # Отправляем сообщение получателю
        await message.bot.send_message(
            chat_id=target_chat_id,
            text=f"💬 **Сообщение от администратора:**\n\n{message.text}"
        )
        
        await message.answer("✅ Сообщение успешно отправлено!")
        
        # Возвращаемся к информации об участнике
        await state.clear()
        await state.update_data(
            events_list=data.get("events_list", []),
            participants_list=data.get("participants_list", [])
        )
        
        # Возвращаемся к информации об участнике
        await _return_to_participant_info(message, state, event_index, participant_index)
        
    except Exception as e:
        print(f"ERROR sending message to participant: {e}")
        await message.answer("❌ Ошибка при отправке сообщения. Попробуйте позже.")


@router.callback_query(F.data.startswith("participant:cancel_message:"))
async def on_cancel_message(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменяет отправку сообщения"""
    parts = callback.data.split(":")
    event_index = int(parts[2])
    participant_index = int(parts[3])
    
    # Сохраняем необходимые данные до очистки состояния
    data = await state.get_data()
    await state.clear()
    await state.update_data(
        events_list=data.get("events_list", []),
        participants_list=data.get("participants_list", [])
    )
    
    await _return_to_participant_info(callback, state, event_index, participant_index)


# Обработчики для работы с черным списком
@router.message(BlacklistForm.waiting_for_reason)
async def on_blacklist_reason_received(message: Message, state: FSMContext) -> None:
    """Обрабатывает причину добавления в черный список"""
    data = await state.get_data()
    target_username = data.get("blacklist_target_username")
    event_index = data.get("blacklist_event_index")
    participant_index = data.get("blacklist_participant_index")
    
    if not target_username:
        await message.answer("Ошибка: пользователь не найден")
        await state.clear()
        return
    
    # Добавляем пользователя в черный список
    success = add_user_to_event_blacklist(
        event_id=data.get("events_list", [])[event_index].get("id"),
        username=target_username,
        added_by=message.from_user.username if message.from_user else "unknown",
        reason=message.text
    )
    
    if success:
        await message.answer(f"✅ Пользователь {target_username} добавлен в черный список мероприятия")
        
        # Удаляем пользователя с мероприятия, если он был зарегистрирован
        event = data.get("events_list", [])[event_index]
        if is_user_registered_for_event(target_username, event.get("id")):
            unregister_user_from_event(target_username, event.get("id"))
        
        # Уведомляем пользователя о добавлении в черный список
        target_chat_id = get_user_chat_id(target_username)
        if target_chat_id:
            try:
                await message.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"🚫 Вы были добавлены в черный список мероприятия \"{event.get('title')}\".\n\nПричина: {message.text}"
                )
            except Exception as e:
                print(f"ERROR notifying user about blacklist: {e}")
    else:
        await message.answer("❌ Ошибка при добавлении в черный список. Попробуйте позже.")
    
    # Возвращаемся к информации об участнике
    await state.clear()
    await state.update_data(
        events_list=data.get("events_list", []),
        participants_list=data.get("participants_list", [])
    )
    
    await _return_to_participant_info(message, state, event_index, participant_index)


@router.callback_query(F.data.startswith("participant:cancel_blacklist:"))
async def on_cancel_blacklist(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменяет добавление в черный список"""
    parts = callback.data.split(":")
    event_index = int(parts[2])
    participant_index = int(parts[3])
    
    await state.clear()
    
    # Возвращаемся к информации об участнике
    data = await state.get_data()
    await state.update_data(
        events_list=data.get("events_list", []),
        participants_list=data.get("participants_list", [])
    )
    
    await _return_to_participant_info(callback, state, event_index, participant_index)


@router.callback_query(F.data.startswith("participant:confirm_blacklist:"))
async def on_confirm_blacklist(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждает добавление в черный список (использует сохраненную причину)"""
    data = await state.get_data()
    target_username = data.get("blacklist_target_username")
    event_index = data.get("blacklist_event_index")
    participant_index = data.get("blacklist_participant_index")
    
    if not target_username:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        await state.clear()
        return
    
    # Добавляем пользователя в черный список без причины
    success = add_user_to_event_blacklist(
        event_id=data.get("events_list", [])[event_index].get("id"),
        username=target_username,
        added_by=callback.from_user.username if callback.from_user else "unknown",
        reason="Причина не указана"
    )
    
    if success:
        await callback.answer("✅ Пользователь добавлен в черный список", show_alert=True)
        
        # Удаляем пользователя с мероприятия, если он был зарегистрирован
        event = data.get("events_list", [])[event_index]
        if is_user_registered_for_event(target_username, event.get("id")):
            unregister_user_from_event(target_username, event.get("id"))
        
        # Уведомляем пользователя о добавлении в черный список
        target_chat_id = get_user_chat_id(target_username)
        if target_chat_id:
            try:
                await callback.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"🚫 Вы были добавлены в черный список мероприятия \"{event.get('title')}\"."
                )
            except Exception as e:
                print(f"ERROR notifying user about blacklist: {e}")
    else:
        await callback.answer("❌ Ошибка при добавлении в черный список", show_alert=True)
    
    # Возвращаемся к информации об участнике
    await state.clear()
    await state.update_data(
        events_list=data.get("events_list", []),
        participants_list=data.get("participants_list", [])
    )
    
    await _return_to_participant_info(callback, state, event_index, participant_index)


# Обработчики для просмотра черного списка
@router.callback_query(F.data.startswith("event:blacklist:"))
async def on_show_event_blacklist(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает черный список мероприятия"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индекс мероприятия из callback_data
    event_index = int(callback.data.split(":")[2])
    
    # Получаем данные из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    
    if event_index >= len(events):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event = events[event_index]
    
    # Получаем черный список мероприятия
    blacklist = get_event_blacklist(event.get("id"))
    
    if not blacklist:
        empty_text = f"📋 Черный список мероприятия \"{event.get('title')}\"\n\nСписок пуст"
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад к мероприятию", callback_data=f"event:show:{event_index}")
        ]])
        await _safe_edit_message(callback.message, empty_text, back_keyboard)
        return
    
    # Сохраняем черный список в состоянии
    await state.update_data(blacklist_list=blacklist)
    
    # Создаем клавиатуру со списком пользователей в черном списке
    keyboard = build_blacklist_view_keyboard(blacklist, event_index)
    
    await _safe_edit_message(
        callback.message,
        f"📋 Черный список мероприятия \"{event.get('title')}\"\n\nВыберите пользователя для просмотра деталей:",
        keyboard
    )


@router.callback_query(F.data.startswith("blacklist:show:"))
async def on_show_blacklist_user_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает информацию о пользователе в черном списке"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индексы из callback_data
    parts = callback.data.split(":")
    event_index = int(parts[2])
    blacklist_index = int(parts[3])
    
    # Получаем данные из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    blacklist = data.get("blacklist_list", [])
    
    if event_index >= len(events) or blacklist_index >= len(blacklist):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    event = events[event_index]
    blacklisted_user = blacklist[blacklist_index]
    
    username = blacklisted_user.get("username", "")
    added_by = blacklisted_user.get("added_by", "")
    added_at = blacklisted_user.get("added_at", "")
    reason = blacklisted_user.get("reason", "Причина не указана")
    
    # Формируем текст с информацией о пользователе в черном списке
    message_text = f"🚫 Информация о пользователе в черном списке\n\n"
    message_text += f"Пользователь: {username}\n"
    message_text += f"Добавлен: {added_by}\n"
    message_text += f"Дата добавления: {added_at}\n"
    message_text += f"Причина: {reason}\n"
    
    # Создаем клавиатуру для управления пользователем в черном списке
    keyboard = build_blacklist_user_info_keyboard(event_index, blacklist_index)
    
    await _safe_edit_message(
        callback.message,
        message_text,
        keyboard
    )


@router.callback_query(F.data.startswith("blacklist:remove:"))
async def on_remove_from_blacklist(callback: CallbackQuery, state: FSMContext) -> None:
    """Удаляет пользователя из черного списка"""
    # Проверяем, является ли пользователь админом
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    # Извлекаем индексы из callback_data
    parts = callback.data.split(":")
    event_index = int(parts[2])
    blacklist_index = int(parts[3])
    
    # Получаем данные из состояния
    data = await state.get_data()
    events = data.get("events_list", [])
    blacklist = data.get("blacklist_list", [])
    
    if event_index >= len(events) or blacklist_index >= len(blacklist):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    event = events[event_index]
    blacklisted_user = blacklist[blacklist_index]
    username = blacklisted_user.get("username", "")
    
    # Удаляем пользователя из черного списка
    success = remove_user_from_event_blacklist(event.get("id"), username)
    
    if success:
        await callback.answer("✅ Пользователь удален из черного списка", show_alert=True)
        
        # Уведомляем пользователя об удалении из черного списка
        target_chat_id = get_user_chat_id(username)
        if target_chat_id:
            try:
                await callback.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"✅ Вы были удалены из черного списка мероприятия \"{event.get('title')}\"."
                )
            except Exception as e:
                print(f"ERROR notifying user about blacklist removal: {e}")
        
        # Обновляем список черного списка
        updated_blacklist = get_event_blacklist(event.get("id"))
        await state.update_data(blacklist_list=updated_blacklist)
        
        # Возвращаемся к черному списку
        await on_show_event_blacklist(callback, state)
    else:
        await callback.answer("❌ Ошибка при удалении из черного списка", show_alert=True)


# Вспомогательные функции
async def _return_to_participant_info(message_or_callback, state: FSMContext, event_index: int, participant_index: int) -> None:
    """Вспомогательная функция для возврата к информации об участнике"""
    data = await state.get_data()
    events = data.get("events_list", [])
    participants = data.get("participants_list", [])
    
    if event_index >= len(events) or participant_index >= len(participants):
        return
    
    event = events[event_index]
    participant = participants[participant_index]
    username = participant.get("username", "")
    
    # Получаем информацию о пользователе
    user_info = get_user_info(username)
    registrations_count = get_user_registrations_count(username)
    
    # Формируем текст с информацией об участнике
    message_text = f"👤 Информация об участнике\n\n"
    message_text += f"Пользователь: {username}\n"
    message_text += f"Статус: "
    
    if participant.get("status") == "registered":
        message_text += "✅ Зарегистрирован\n"
    elif participant.get("status") == "waitlist":
        message_text += "⏳ В очереди ожидания\n"
    else:
        message_text += "❓ Неизвестный статус\n"
    
    if participant.get("registration_date"):
        message_text += f"Дата регистрации: {participant['registration_date']}\n"
    
    if user_info:
        if user_info.get("created_at"):
            message_text += f"В боте с: {user_info['created_at']}\n"
    
    message_text += f"Всего регистраций: {registrations_count}\n"
    
    # Создаем клавиатуру для управления участником
    keyboard = build_participant_info_keyboard(event_index, participant_index)
    
    # Обновляем сообщение безопасно
    if hasattr(message_or_callback, 'message'):
        await _safe_edit_message(message_or_callback.message, message_text, keyboard)
    else:
        await message_or_callback.answer(message_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("blacklist:message:"))
async def on_message_blacklist_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало отправки сообщения пользователю из ЧС"""
    if not user_is_admin(callback.from_user.username if callback.from_user else None):
        await callback.answer("Только для админов", show_alert=True)
        return
    
    parts = callback.data.split(":")
    event_index = int(parts[2])
    blacklist_index = int(parts[3])
    
    data = await state.get_data()
    events = data.get("events_list", [])
    blacklist = data.get("blacklist_list", [])
    
    if event_index >= len(events) or blacklist_index >= len(blacklist):
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    blacklisted_user = blacklist[blacklist_index]
    username = blacklisted_user.get("username", "")
    
    await state.update_data(
        bl_msg_event_index=event_index,
        bl_msg_index=blacklist_index,
        bl_msg_username=username
    )
    await state.set_state(MessageBlacklistUserForm.waiting_for_message)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data=f"blacklist:cancel_message:{event_index}:{blacklist_index}")]])
    await _safe_edit_message(
        callback.message,
        f"💬 Написать пользователю {username} (в ЧС)\n\nВведите текст сообщения:",
        keyboard
    )


@router.callback_query(F.data.startswith("blacklist:cancel_message:"))
async def on_cancel_message_blacklist(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    event_index = int(parts[2])
    blacklist_index = int(parts[3])
    
    # Возврат к карточке пользователя в ЧС
    data = await state.get_data()
    await state.clear()
    await state.update_data(
        events_list=data.get("events_list", []),
        blacklist_list=data.get("blacklist_list", [])
    )
    await on_show_blacklist_user_info(callback, state)


@router.message(MessageBlacklistUserForm.waiting_for_message)
async def on_blacklist_message_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    username = data.get("bl_msg_username")
    event_index = data.get("bl_msg_event_index")
    blacklist_index = data.get("bl_msg_index")
    
    if not username:
        await message.answer("Ошибка: пользователь не найден")
        await state.clear()
        return
    
    chat_id = get_user_chat_id(username)
    if not chat_id:
        await message.answer(f"Не удалось отправить: {username} не запускал бота")
        await state.clear()
        return
    
    try:
        await message.bot.send_message(chat_id=chat_id, text=message.text)
        await message.answer("✅ Сообщение отправлено")
    except Exception as e:
        print(f"ERROR sending message to blacklisted user: {e}")
        await message.answer("❌ Ошибка при отправке сообщения")
    
    # Возврат к карточке пользователя в ЧС
    await state.clear()
    await state.update_data(bl_msg_username=username)  # сохранить минимум, если нужно
    # Создаем компактную клавиатуру назад
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к ЧС", callback_data=f"event:blacklist:{event_index}")]])
    await message.answer("Возврат к чёрному списку", reply_markup=kb)


