### Что сделано
- Бот на aiogram 3: `bot.py`
- Подключение к Supabase через `supabase-py`
- Переменные окружения в `.env`
- SQL для таблиц в `supabase_schema.sql`

### Как создать таблицы в Supabase
1) Откройте Supabase → Project → SQL Editor.
2) Вставьте содержимое файла `supabase_schema.sql` и выполните.
3) В таблицу `admin` вручную добавляйте TG-ник в колонку `tg_username` в формате `@my_admin_nick`.

Примечание: проверка админа идёт по колонке `tg_username` (формат `@username`). Если у пользователя нет username, он будет считаться обычным пользователем.

### Запуск локально (Windows PowerShell)
```powershell
cd "C:\\Users\\Артём\\Desktop\\test1"
py -3 -m venv .venv
./.venv/Scripts/python -m pip install --upgrade pip
./.venv/Scripts/pip install -r requirements.txt
./.venv/Scripts/python bot.py
```

После запуска нажмите /start в боте. Он ответит «Вы админ» или «Вы пользователь».


