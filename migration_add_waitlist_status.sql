-- Миграция: добавление статуса "waitlist" в ограничение CHECK для таблицы event_registrations
-- Выполните этот скрипт в Supabase SQL Editor

-- Удаляем старое ограничение CHECK
ALTER TABLE event_registrations DROP CONSTRAINT IF EXISTS event_registrations_status_check;

-- Добавляем новое ограничение CHECK с включением статуса "waitlist"
ALTER TABLE event_registrations ADD CONSTRAINT event_registrations_status_check 
CHECK (status IN ('registered', 'cancelled', 'attended', 'waitlist'));

-- Проверяем, что ограничение применено
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'event_registrations'::regclass 
AND contype = 'c';

-- Показываем текущие статусы в таблице (для информации)
SELECT status, COUNT(*) as count 
FROM event_registrations 
GROUP BY status 
ORDER BY status;
