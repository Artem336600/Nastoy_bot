-- Миграция: добавление колонки id к существующей таблице events
-- Выполните этот скрипт в Supabase SQL Editor

-- Проверяем, существует ли колонка id в таблице events
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'events'
          AND column_name = 'id'
    ) THEN
        -- Добавляем колонку id как SERIAL PRIMARY KEY
        ALTER TABLE events ADD COLUMN id SERIAL PRIMARY KEY;
        RAISE NOTICE 'Колонка id добавлена к таблице events';
    ELSE
        RAISE NOTICE 'Колонка id уже существует в таблице events';
    END IF;
END $$;

-- Проверяем, существует ли колонка is_completed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'events'
          AND column_name = 'is_completed'
    ) THEN
        -- Добавляем колонку is_completed
        ALTER TABLE events ADD COLUMN is_completed BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Колонка is_completed добавлена к таблице events';
    ELSE
        RAISE NOTICE 'Колонка is_completed уже существует в таблице events';
    END IF;
END $$;

-- Проверяем, существует ли колонка created_at
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'events'
          AND column_name = 'created_at'
    ) THEN
        -- Добавляем колонку created_at
        ALTER TABLE events ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Колонка created_at добавлена к таблице events';
    ELSE
        RAISE NOTICE 'Колонка created_at уже существует в таблице events';
    END IF;
END $$;

-- Проверка структуры таблицы
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'events'
ORDER BY ordinal_position;
