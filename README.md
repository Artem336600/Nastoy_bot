### Что сделано
- Бот на aiogram 3: `bot.py`
- Подключение к Supabase через `supabase-py`
- Переменные окружения в `.env`
- SQL для таблиц в `supabase_schema.sql`

### Как создать таблицы в Supabase
1) Откройте Supabase → Project → SQL Editor.
2) Вставьте содержимое файла `supabase_schema.sql` и выполните.
3) В таблицу `admin` вручную добавляйте TG-ник в колонку `tg` в формате `@my_admin_nick`.

Примечание: проверка админа идёт по колонке `tg` (формат `@username`). Если у пользователя нет username, он будет считаться обычным пользователем.

### Структура проекта (по образцу BAS Media Bot)

```
.
├── deployment/
│   ├── docker-compose.yaml
│   └── bot.env
├── docs/
│   └── README.md
├── migrations/
├── script/
├── src/
│   └── run.py
├── app/
│   ├── main.py
│   ├── config.py
│   ├── supabase_client.py
│   ├── keyboards.py
│   ├── states.py
│   └── routers/
│       ├── __init__.py
│       ├── start.py
│       └── events.py
├── requirements.txt
└── bot.py
```

### Запуск

- Вариант 1: локально
```powershell
py -3 -m venv .venv
./.venv/Scripts/python -m pip install --upgrade pip
./.venv/Scripts/pip install -r requirements.txt
./.venv/Scripts/python -m src.run
```

- Вариант 2: через docker-compose
```bash
cd deployment
docker compose up --build
```


