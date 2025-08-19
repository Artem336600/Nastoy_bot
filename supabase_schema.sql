-- Создайте таблицы через Supabase SQL Editor, выполнив этот скрипт

-- Таблица админов: только tg (формат @username)
create table if not exists public.admin (
    tg text primary key
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    tg_username TEXT UNIQUE NOT NULL,
    chat_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Чистка старых колонок и индексов, если таблица была создана ранее
alter table if exists public.users drop column if exists user_id;
alter table if exists public.users drop column if exists username;
alter table if exists public.users drop column if exists first_name;
alter table if exists public.users drop column if exists last_name;
alter table if exists public.users drop column if exists created_at;
alter table if exists public.users drop constraint if exists users_pkey;
drop index if exists users_username_idx;

-- Убедимся, что у admin есть колонка tg
alter table if exists public.admin
    add column if not exists tg text;

-- На всякий случай удалим флаг is_admin, если он был добавлен ранее
alter table if exists public.admin drop column if exists is_admin;

-- Убедимся, что нужная колонка существует
alter table if exists public.users
    add column if not exists tg_username text;

-- Индексы/уникальность по tg_username
-- Первичный ключ по tg_username (создаст индекс автоматически)
alter table if exists public.users
    add constraint users_pkey primary key (tg_username);

-- Бэкфилл tg_username на основе старого поля username (если колонка username существует)
do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'admin'
          and column_name = 'username'
    ) then
        update public.admin
        set tg_username = '@' || username
        where tg_username is null and username is not null and username !~ '^@';

        update public.admin
        set tg_username = username
        where tg_username is null and username ~ '^@';
    end if;
end $$;


-- Миграция: если ранее использовалась колонка tg_username, переносим данные в tg и чистим
do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'admin'
          and column_name = 'tg_username'
    ) then
        update public.admin
        set tg = coalesce(tg, tg_username)
        where tg is null and tg_username is not null;

        -- Удаляем старые артефакты и ставим PK по tg
        begin
            alter table if exists public.admin drop constraint if exists admin_pkey;
        exception when others then null;
        end;

        alter table if exists public.admin drop column if exists username;
        alter table if exists public.admin drop column if exists tg_username;
        alter table if exists public.admin add constraint admin_pkey primary key (tg);
    else
        -- Если tg_username нет, просто убедимся, что PK по tg
        begin
            alter table if exists public.admin add constraint admin_pkey primary key (tg);
        exception when others then null;
        end;
    end if;
end $$;


-- Создание таблицы мероприятий
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    photo TEXT,
    board_games TEXT,
    date TEXT,
    responsible TEXT,
    quantity INTEGER,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Включение RLS для таблицы events
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Политика для разрешения анонимных вставок
DROP POLICY IF EXISTS events_allow_all ON events;
CREATE POLICY events_allow_all ON events FOR ALL USING (true);

-- Добавляем поле is_cancelled в events, если его нет
DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_name='events' AND column_name='is_cancelled'
	) THEN
		ALTER TABLE events ADD COLUMN is_cancelled BOOLEAN DEFAULT FALSE;
	END IF;
END $$;

-- Флаги отправленных напоминаний для events
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='events' AND column_name='reminder_1day_sent'
    ) THEN
        ALTER TABLE events ADD COLUMN reminder_1day_sent BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='events' AND column_name='reminder_1hour_sent'
    ) THEN
        ALTER TABLE events ADD COLUMN reminder_1hour_sent BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Таблица регистраций пользователей на мероприятия
CREATE TABLE IF NOT EXISTS event_registrations (
    id SERIAL PRIMARY KEY,
    user_tg_username TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    registration_date TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'registered' CHECK (status IN ('registered', 'cancelled', 'attended', 'waitlist')),
    notes TEXT,
    
    -- Уникальность: один пользователь может зарегистрироваться на одно мероприятие только один раз
    UNIQUE(user_tg_username, event_id),
    
    -- Внешние ключи
    FOREIGN KEY (user_tg_username) REFERENCES users(tg_username) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_event_registrations_user ON event_registrations(user_tg_username);
CREATE INDEX IF NOT EXISTS idx_event_registrations_event ON event_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_event_registrations_status ON event_registrations(status);

-- Включение RLS для таблицы регистраций
ALTER TABLE event_registrations ENABLE ROW LEVEL SECURITY;

-- Политика для разрешения анонимных операций с регистрациями
DROP POLICY IF EXISTS event_registrations_allow_all ON event_registrations;
CREATE POLICY event_registrations_allow_all ON event_registrations FOR ALL USING (true);

-- Таблица для черного списка мероприятий
CREATE TABLE IF NOT EXISTS event_blacklist (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_tg_username TEXT NOT NULL,
    added_by_tg_username TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    reason TEXT,
    UNIQUE(event_id, user_tg_username),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_tg_username) REFERENCES users(tg_username) ON DELETE CASCADE,
    FOREIGN KEY (added_by_tg_username) REFERENCES users(tg_username) ON DELETE CASCADE
);

-- Включаем RLS для event_blacklist
ALTER TABLE event_blacklist ENABLE ROW LEVEL SECURITY;

-- Политика для event_blacklist
DROP POLICY IF EXISTS event_blacklist_allow_all ON event_blacklist;
CREATE POLICY event_blacklist_allow_all ON event_blacklist FOR ALL USING (true);


-- Таблица отзывов по мероприятиям
CREATE TABLE IF NOT EXISTS event_feedback (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_tg_username TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 10),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, user_tg_username),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_tg_username) REFERENCES users(tg_username) ON DELETE CASCADE
);

ALTER TABLE event_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS event_feedback_allow_all ON event_feedback;
CREATE POLICY event_feedback_allow_all ON event_feedback FOR ALL USING (true);