# 🛡️ SecHack AI Defense System

> **生物学的進化理論を応用したサイバー攻撃・防御の共進化研究プラットフォーム**

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)](https://postgresql.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black)](https://flask.palletsprojects.com)

---

## 🎯 概要

GPT-4による攻撃生成AIと検知AIを対戦させ、攻撃と防御の**共進化ダイナミクス**を定量的に評価する研究プラットフォーム。生物学の系統学的手法（遺伝的距離・形態的距離・生殖隔離）をサイバーセキュリティに適用する。

### 研究設問（Research Questions）

| RQ | 問い | 指標 |
|----|------|------|
| **RQ1** | 攻撃と防御の共進化は観測されるか？ | 時系列検知率・世代統計 |
| **RQ2** | 進化した攻撃はどれだけ新規性が高いか？ | 系統学的距離スコア |
| **RQ3** | 適応放散はドメイン間で一様か？ | Kruskal-Wallis検定 |

---

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Network                           │
│                                                                  │
│  ┌──────────────┐    attack    ┌──────────────┐                 │
│  │  Red Team AI │─────────────▶│    Redis     │                 │
│  │  (GPT-4)     │              │  (Pub/Sub)   │                 │
│  └──────┬───────┘              └──────┬───────┘                 │
│         │                             │ subscribe               │
│         │ save                        ▼                          │
│         │              ┌──────────────────────┐                 │
│         │              │      Blue AI         │                 │
│         │              │ (Keyword Detection)  │                 │
│         │              └──────────┬───────────┘                 │
│         │                         │ save                        │
│         ▼                         ▼                             │
│  ┌─────────────────────────────────────────┐                    │
│  │           PostgreSQL (TimescaleDB)       │                    │
│  │  attack_events / detection_results /    │                    │
│  │  av_detection_results / domain_summary  │                    │
│  └────────────────────┬────────────────────┘                    │
│                        │ query                                   │
│                        ▼                                         │
│  ┌──────────────────────────────────────────┐                   │
│  │         Phase Space Dashboard            │                   │
│  │  ┌──────────┐  ┌───────────┐             │                   │
│  │  │ D/R/V    │  │ Evolution │  Flask API  │                   │
│  │  │ Model    │  │ Metrics   │  :3000      │                   │
│  │  └──────────┘  └───────────┘             │                   │
│  └──────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### コンポーネント詳細

| コンポーネント | 技術 | 役割 |
|--------------|------|------|
| **Red Team AI** | Python + GPT-4 | 攻撃コマンドの自動生成 |
| **Blue AI** | Python | キーワードベースの脅威検知 |
| **Redis** | Redis 7 | リアルタイムメッセージング |
| **PostgreSQL** | TimescaleDB | 攻撃・検知ログの永続化 |
| **Dashboard** | Flask + Plotly.js | 可視化・メトリクス API |

---

## 🚀 セットアップ

### 前提条件

- Docker Desktop (Windows/Mac) または Docker Engine (Linux)
- OpenAI API キー（GPT-4アクセス権）

### 1. リポジトリのクローン

```bash
git clone https://github.com/Hapikunn/sechack-ai-defense.git
cd sechack-ai-defense
```

### 2. 環境変数の設定

`.env` ファイルをプロジェクトルートに作成：

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
DB_URL=postgresql://user:password@timescaledb:5432/sechack
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=sechack
REDIS_URL=redis://redis:6379/0
```

### 3. 起動

```bash
docker-compose up --build
```

### 4. DBスキーマ初期化

別ターミナルで：

```bash
docker exec -i sechack_db psql -U user -d sechack < shared/sql/metrics.sql
```

### 5. テストデータ投入（オプション）

```bash
docker cp scripts/populate_test_data.py sechack_dashboard:/app/scripts/
docker exec -it sechack_dashboard python /app/scripts/populate_test_data.py
```

### 6. アクセス

| URL | 内容 |
|-----|------|
| http://localhost:3000 | メインダッシュボード（相空間 D/R/V） |
| http://localhost:3000/poster | ポスター用グラフ・エクスポート |
| http://localhost:3000/api/rq1/coevolution | RQ1 API |
| http://localhost:3000/api/rq2/novelty | RQ2 API |
| http://localhost:3000/api/rq3/domain_comparison | RQ3 API |

---

## 📊 実験結果（テストデータ）

### RQ1: 共進化の観測

| フェーズ | 時間帯 | 検知率 |
|---------|--------|--------|
| Phase 1 | 0-6h | **87.4%** |
| Phase 2 | 6-24h | **59.2%** ↓ 攻撃の進化 |
| Phase 3 | 24-72h | **84.5%** ↑ 防御の適応 |

世代分布（PowerShellドメイン）:

```
第1世代: ████████████████████████ 277件
第2世代: ████ 39件
第3世代: ██ 19件
第4世代: █ 13件
第5世代: ▌ 9件
第6世代: ▌ 7件
```

### RQ2: 新規性評価

| 指標 | 値 |
|------|-----|
| 平均新規性スコア | 0.73 |
| Zero-Day (0/5検知) | 15件 (4.1%) |
| 最大新規性スコア | 0.94 |

### RQ3: ドメイン間比較

| ドメイン | 世代率 | Kruskal-Wallis |
|----------|--------|----------------|
| PowerShell | 20.6% | H=3.42 |
| WebApp | 18.9% | p=0.331 |
| IoT | 19.7% | **有意差なし** |
| Cloud | 22.0% | (p>0.05) |

---

## 🗂️ ディレクトリ構成

```
sechack-ai-defense/
├── docker-compose.yml
├── .env
├── red_team/
│   └── main.py                # GPT-4攻撃生成
├── blue_ai/
│   └── main.py                # キーワード検知
├── phase_space/
│   ├── app.py                 # Flask API
│   └── templates/
│       ├── index.html         # メインダッシュボード
│       └── poster_data.html   # ポスター用グラフ
├── shared/
│   ├── database.py            # PostgreSQL操作
│   ├── messaging.py           # Redis pub/sub
│   ├── phase_space.py         # D/R/V計算
│   ├── metrics.py             # 進化メトリクス（RQ1-3）
│   └── sql/
│       ├── init.sql
│       └── metrics.sql
└── scripts/
    └── populate_test_data.py
```

---

## ✅ 実装状況

### 完成
- [x] Docker Compose による自動起動
- [x] GPT-4 による攻撃コマンド自動生成
- [x] キーワードベースの脅威検知
- [x] 相空間モデル (D/R/V)
- [x] RQ1-3 の定量メトリクス API
- [x] ポスター用グラフ・PNGエクスポート

### 未実装・改良予定
- [ ] **進化的プロンプト** — 前世代の検知結果を参照した攻撃進化（最重要）
- [ ] **Blue AI の機械学習化** — キーワードマッチから ML 検知へ
- [ ] **実 AV スキャン統合** — VirusTotal API との接続
- [ ] **長期実験** — 72h → 数週間の連続観測

> アルゴリズムの詳細は [ALGORITHM.md](./ALGORITHM.md) を参照。

---

## 🛑 停止

```bash
docker-compose down        # 停止
docker-compose down -v     # 完全削除（DBデータも消去）
```

---

## 👥 開発者

[Hotaku Komatsu] — SecHack365

## 📄 ライセンス

MIT License
