-- Миграция: добавление колонки chat_id к таблице users
-- Выполните этот скрипт в Supabase SQL Editor

-- Проверяем, существует ли колонка chat_id в таблице users
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'chat_id'
    ) THEN
        -- Добавляем колонку chat_id
        ALTER TABLE users ADD COLUMN chat_id BIGINT;
        RAISE NOTICE 'Колонка chat_id добавлена к таблице users';
    ELSE
        RAISE NOTICE 'Колонка chat_id уже существует в таблице users';
    END IF;
END $$;

-- Создаем индекс для быстрого поиска по chat_id
CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id);

-- Проверка структуры таблицы
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
ORDER BY ordinal_position;
