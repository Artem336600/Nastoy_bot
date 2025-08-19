-- Глобальный чёрный список пользователей (блокировка на всех мероприятиях)
CREATE TABLE IF NOT EXISTS global_blacklist (
    id SERIAL PRIMARY KEY,
    user_tg_username TEXT NOT NULL UNIQUE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_tg_username) REFERENCES users(tg_username) ON DELETE CASCADE
);

ALTER TABLE global_blacklist ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS global_blacklist_allow_all ON global_blacklist;
CREATE POLICY global_blacklist_allow_all ON global_blacklist FOR ALL USING (true);


