-- Миграция: исправление структуры таблицы users
-- Выполните этот скрипт в Supabase SQL Editor

-- Проверяем и добавляем колонку id, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'id'
    ) THEN
        -- Добавляем колонку id как SERIAL (без PRIMARY KEY)
        ALTER TABLE users ADD COLUMN id SERIAL;
        RAISE NOTICE 'Колонка id добавлена к таблице users';
    ELSE
        RAISE NOTICE 'Колонка id уже существует в таблице users';
    END IF;
END $$;

-- Проверяем и добавляем колонку chat_id, если её нет
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

-- Проверяем и добавляем колонку created_at, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'created_at'
    ) THEN
        -- Добавляем колонку created_at
        ALTER TABLE users ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Колонка created_at добавлена к таблице users';
    ELSE
        RAISE NOTICE 'Колонка created_at уже существует в таблице users';
    END IF;
END $$;

-- Создаем индекс для быстрого поиска по chat_id
CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id);

-- Создаем уникальный индекс для id, если его нет
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_id ON users(id);

-- Проверка структуры таблицы
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
ORDER BY ordinal_position;

-- Показываем текущие данные в таблице (для информации)
SELECT COUNT(*) as total_users FROM users;

-- Показываем существующие ограничения
SELECT conname, contype, pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'users'::regclass;
