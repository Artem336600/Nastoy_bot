-- Миграция: добавление поля is_completed к таблице events
-- Выполните этот SQL в Supabase SQL Editor

-- Добавляем поле is_completed, если его нет
ALTER TABLE events ADD COLUMN IF NOT EXISTS is_completed BOOLEAN DEFAULT FALSE;

-- Добавляем поле created_at, если его нет
ALTER TABLE events ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Убеждаемся, что у всех существующих записей is_completed = FALSE
UPDATE events SET is_completed = FALSE WHERE is_completed IS NULL;
