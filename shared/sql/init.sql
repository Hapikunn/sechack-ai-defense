-- 攻撃イベントテーブル
CREATE TABLE IF NOT EXISTS attack_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    session_id VARCHAR(64),
    user_id VARCHAR(64),
    command TEXT,
    attack_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 検知結果テーブル
CREATE TABLE IF NOT EXISTS detection_results (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    is_dangerous BOOLEAN,
    detected_keyword VARCHAR(256),
    anomaly_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (event_id) REFERENCES attack_events(event_id)
);

-- インデックス作成（検索を高速化）
CREATE INDEX IF NOT EXISTS idx_attack_timestamp ON attack_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detection_event_id ON detection_results(event_id);
CREATE INDEX IF NOT EXISTS idx_detection_timestamp ON detection_results(timestamp DESC);

-- 初期データ確認用
SELECT 'Database initialized successfully' AS status;