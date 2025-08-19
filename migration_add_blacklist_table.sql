-- Миграция для добавления таблицы черного списка мероприятий

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
