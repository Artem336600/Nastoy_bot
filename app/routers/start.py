from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from ..keyboards import build_admin_main_keyboard, build_user_main_keyboard
from ..utils import user_is_admin, ensure_user_exists


router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return
    # Сохраняем пользователя и его chat_id для возможности связи
    try:
        ensure_user_exists(user.username, user.id)
    except Exception:
        pass
    
    # Проверяем, является ли пользователь админом
    if user_is_admin(user.username):
        # Отправляем админскую клавиатуру
        await message.answer(
            "Добро пожаловать! Вы являетесь администратором.",
            reply_markup=build_admin_main_keyboard()
        )
    else:
        # Отправляем клавиатуру для обычных пользователей
        await message.answer(
            "Добро пожаловать! Выберите действие:",
            reply_markup=build_user_main_keyboard()
        )


