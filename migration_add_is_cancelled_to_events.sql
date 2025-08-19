-- Миграция: добавление флага отмены мероприятия
DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_name='events' AND column_name='is_cancelled'
	) THEN
		ALTER TABLE events ADD COLUMN is_cancelled BOOLEAN DEFAULT FALSE;
	END IF;
END $$;
