-- Таблица настольных игр
CREATE TABLE IF NOT EXISTS board_games (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    photo TEXT,
    rules TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE board_games ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS board_games_allow_all ON board_games;
CREATE POLICY board_games_allow_all ON board_games FOR ALL USING (true);


