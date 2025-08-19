import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import BOT_TOKEN, validate_config
from .routers.start import router as start_router
from .routers.events import router as events_router
from .utils import get_events_needing_reminders, mark_event_reminder_sent, get_event_participants


async def run() -> None:
	validate_config()
	assert BOT_TOKEN
	# Совместимая инициализация для разных версий aiogram
	try:
		from aiogram.client.default import DefaultBotProperties
		from aiogram.enums import ParseMode
		bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
	except Exception:
		bot = Bot(BOT_TOKEN)
	
	dp = Dispatcher(storage=MemoryStorage())
	dp.include_router(start_router)
	dp.include_router(events_router)
	await bot.delete_webhook(drop_pending_updates=True)

	async def reminders_worker():
		while True:
			try:
				tasks = get_events_needing_reminders()
				for t in tasks:
					event = t.get("event")
					reminder_type = t.get("type")
					event_id = event.get("id")
					title = event.get("title") or "Мероприятие"
					date = event.get("date") or "-"
					if reminder_type == "1day":
						text = f"⏰ Напоминание: завтра состоится '{title}'\nДата и время: {date}"
					else:
						text = f"⏰ Напоминание: через час '{title}'\nДата и время: {date}"
					# Отправляем всем зарегистрированным
					try:
						participants = get_event_participants(event_id)
						for p in participants:
							chat_id = p.get("chat_id")
							if not chat_id:
								continue
							try:
								await bot.send_message(chat_id=chat_id, text=text)
							except Exception as e:
								print(f"ERROR send reminder to {p.get('username')}: {e}")
					except Exception as e:
						print(f"ERROR fetching participants for reminder: {e}")
					mark_event_reminder_sent(event_id, reminder_type)
			except Exception as e:
				print(f"REMINDERS_WORKER_ERROR: {e}")
			await asyncio.sleep(60)

	asyncio.create_task(reminders_worker())
	await dp.start_polling(bot)


def main() -> None:
	asyncio.run(run())


