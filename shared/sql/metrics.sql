-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 進化系統樹と定量評価のためのDBスキーマ拡張
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 1. 既存テーブルの拡張（攻撃に進化情報を追加）
ALTER TABLE attack_events 
ADD COLUMN IF NOT EXISTS domain VARCHAR(50) DEFAULT 'powershell',
ADD COLUMN IF NOT EXISTS generation INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS parent_ids TEXT[],
ADD COLUMN IF NOT EXISTS evolution_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS novelty_score DECIMAL(5,4),
ADD COLUMN IF NOT EXISTS elapsed_hours DECIMAL(10,2);

-- 2. 時系列での検知率記録
CREATE TABLE IF NOT EXISTS detection_timeline (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    elapsed_hours DECIMAL(10,2),
    domain VARCHAR(50),
    total_attacks INTEGER,
    detected_count INTEGER,
    missed_count INTEGER,
    detection_rate DECIMAL(5,4),
    phase VARCHAR(20)  -- 'phase_1' (0-6h), 'phase_2' (6-24h), 'phase_3' (24-72h)
);

-- 3. 世代別統計
CREATE TABLE IF NOT EXISTS generation_stats (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(50),
    generation_number INTEGER,
    attack_count INTEGER,
    avg_novelty_score DECIMAL(5,4),
    zeroday_count INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 進化タイプ別統計
CREATE TABLE IF NOT EXISTS evolution_types (
    id SERIAL PRIMARY KEY,
    attack_id VARCHAR(64) REFERENCES attack_events(event_id),
    evolution_type VARCHAR(50),  -- combination, derivation, mutation, advanced_mutation
    parent_ids TEXT[],
    generation_number INTEGER,
    novelty_score DECIMAL(5,4),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 系統樹形状メトリクス
CREATE TABLE IF NOT EXISTS tree_metrics (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(50),
    experiment_run INTEGER DEFAULT 1,
    branch_factor DECIMAL(5,2),
    tree_depth INTEGER,
    colless_index DECIMAL(5,4),
    leaf_count INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 6. AV検知結果詳細（シミュレーション用）
CREATE TABLE IF NOT EXISTS av_detection_results (
    id SERIAL PRIMARY KEY,
    attack_id VARCHAR(64) REFERENCES attack_events(event_id),
    windows_defender BOOLEAN DEFAULT FALSE,
    symantec BOOLEAN DEFAULT FALSE,
    mcafee BOOLEAN DEFAULT FALSE,
    crowdstrike BOOLEAN DEFAULT FALSE,
    sentinelone BOOLEAN DEFAULT FALSE,
    detection_count INTEGER DEFAULT 0,
    is_zeroday BOOLEAN DEFAULT TRUE,  -- 0/5検知
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 7. ドメイン別サマリー
CREATE TABLE IF NOT EXISTS domain_summary (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(50) UNIQUE,
    known_patterns_count INTEGER DEFAULT 0,
    novel_patterns_count INTEGER DEFAULT 0,
    generation_rate DECIMAL(5,4),
    avg_novelty_score DECIMAL(5,4),
    zeroday_count INTEGER DEFAULT 0,
    zeroday_rate DECIMAL(5,4),
    max_generation INTEGER DEFAULT 1,
    experiment_duration_hours INTEGER,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- 8. インデックス作成（検索高速化）
CREATE INDEX IF NOT EXISTS idx_attack_domain ON attack_events(domain);
CREATE INDEX IF NOT EXISTS idx_attack_generation ON attack_events(generation);
CREATE INDEX IF NOT EXISTS idx_timeline_domain ON detection_timeline(domain, elapsed_hours);
CREATE INDEX IF NOT EXISTS idx_generation_stats_domain ON generation_stats(domain, generation_number);

-- 9. 初期データ確認用
SELECT 'Metrics schema initialized successfully' AS status;
