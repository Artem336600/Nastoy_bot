-- Миграция: добавление таблицы регистраций пользователей на мероприятия
-- Выполните этот скрипт в Supabase SQL Editor

-- Проверяем, что таблица events имеет колонку id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'events'
          AND column_name = 'id'
    ) THEN
        RAISE EXCEPTION 'Таблица events не имеет колонку id. Сначала выполните migration_add_id_to_events.sql';
    END IF;
END $$;

-- Таблица регистраций пользователей на мероприятия
CREATE TABLE IF NOT EXISTS event_registrations (
    id SERIAL PRIMARY KEY,
    user_tg_username TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    registration_date TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'registered' CHECK (status IN ('registered', 'cancelled', 'attended')),
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

-- Проверка создания таблицы
SELECT 'Таблица event_registrations успешно создана' as status;
