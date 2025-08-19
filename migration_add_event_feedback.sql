-- Создание таблицы отзывов по мероприятиям
CREATE TABLE IF NOT EXISTS event_feedback (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_tg_username TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 10),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, user_tg_username),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_tg_username) REFERENCES users(tg_username) ON DELETE CASCADE
);

ALTER TABLE event_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS event_feedback_allow_all ON event_feedback;
CREATE POLICY event_feedback_allow_all ON event_feedback FOR ALL USING (true);


