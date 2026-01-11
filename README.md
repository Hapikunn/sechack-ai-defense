# SecHack AI Defense System

AIを使ったサイバー攻撃検知システムのMVP

## 🎯 プロジェクト概要

- **Red Team AI**: 攻撃コマンドを自動生成
- **Blue AI**: ルールベースで脅威を検知
- **PostgreSQL**: 攻撃ログと検知結果を永続化
- **Dashboard**: リアルタイムで状態を可視化

## 🚀 起動方法
```bash
# 初回起動
docker-compose up --build

# 2回目以降
docker-compose up
```

ブラウザで http://localhost:3000 を開く

## 🛑 停止方法
```bash
# Ctrl+C でコンテナ停止
# その後、完全削除する場合
docker-compose down -v
```

## 📊 データベース確認
```bash
docker exec -it sechack_db psql -U user -d sechack
```

## 🏗️ アーキテクチャ
```
Red Team → Redis → Blue AI → PostgreSQL → Dashboard
```

## 📝 現在の実装状況

- ✅ Docker Compose環境
- ✅ Redis メッセージング
- ✅ PostgreSQL データ永続化
- ✅ リアルタイムダッシュボード
- ⏳ OpenAI API統合（未実装）
- ⏳ 機械学習モデル（未実装）
- ⏳ 相空間モデル（未実装）

## 📚 技術スタック

- Docker / Docker Compose
- Python 3.11
- PostgreSQL 15 (TimescaleDB)
- Redis 7
- Flask
- HTML/CSS/JavaScript

## 👥 開発者

[Hotaku Komatsu]

## 📄 ライセンス

MIT License