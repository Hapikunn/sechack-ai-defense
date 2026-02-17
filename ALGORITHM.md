# 🧬 Algorithm Details

本ドキュメントでは、sechack-ai-defenseシステムのアルゴリズムと実装の詳細を説明する。

---

## 🏗️ システム全体のフロー

```
┌─────────────────────────────────────────────────────────────┐
│                     Red Team AI                              │
│  GPT-4で攻撃コマンド生成 → Redis pub/sub に送信              │
└────────────────────────────┬────────────────────────────────┘
                             │  Redis (メッセージキュー)
┌────────────────────────────▼────────────────────────────────┐
│                     Blue AI                                  │
│  キーワードマッチングで検知 → PostgreSQL に結果を保存         │
└────────────────────────────┬────────────────────────────────┘
                             │  PostgreSQL
┌────────────────────────────▼────────────────────────────────┐
│                  Phase Space Dashboard                       │
│  D/R/V 計算 + 進化メトリクス + ポスター用グラフ生成           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔴 Red Team AI のアルゴリズム

### 攻撃生成ループ

```python
while True:
    attack_type = random.choice(ATTACK_TYPES)   # 攻撃タイプをランダム選択
    command = gpt4_generate(attack_type)         # GPT-4で生成
    event_bus.send(command)                      # Redisに送信
    db.save_attack(command)                      # DBに保存
    time.sleep(20)                               # 20秒待機
```

### GPT-4 プロンプト設計

**現在の実装（第1世代のみ）:**
```
あなたは侵入テストの専門家です。
「{attack_type}」するコマンドを1つ生成してください。
条件: ステルス性重視, 1行のみ
```

**改良案（進化的プロンプト）:**
```
以下の攻撃コマンドをベースに、検知を回避するよう進化させて:
親攻撃: {parent_command}
検知されたキーワード: {detected_keyword}
→ このキーワードを使わずに同等の攻撃を実現せよ
```

> ⚠️ **現状の課題**: 前世代の検知結果を参照しておらず、真の意味での「進化」は未実装。
> 親子関係は`populate_test_data.py`によるシミュレーションデータのみ。

### 攻撃タイプの分類

| カテゴリ | 攻撃例 |
|----------|--------|
| ファイル探索 | `Get-ChildItem -Recurse -Filter *.pdf` |
| 認証情報窃取 | `findstr password credentials.json` |
| データ外部送信 | `Invoke-WebRequest -Method POST` |
| 権限昇格 | `net user hacker /add` |
| 情報収集 | `Get-Process`, `systeminfo` |
| データ圧縮 | `Compress-Archive` |

---

## 🔵 Blue AI のアルゴリズム

### 検知ロジック（現在: ルールベース）

```python
DANGEROUS_KEYWORDS = [
    'Recurse', 'Invoke-WebRequest', 'net user',
    'password', 'Credential', 'Out-File',
    'Compress-Archive', 'ErrorAction SilentlyContinue',
    ...
]

def is_dangerous(command):
    for keyword in DANGEROUS_KEYWORDS:
        if keyword.lower() in command.lower():
            return True, keyword   # ← 単純なキーワードマッチ
    return False, None
```

**検知率の特性:**
- 第1世代攻撃: 約87% (既知キーワードが多い)
- 第2世代以降: キーワードを回避した変異により低下傾向
- 限界: 難読化・エンコード攻撃に無力

### anomaly_score の計算

```python
if dangerous:
    score = 0.8   # 危険と判定
else:
    score = 0.2   # 安全と判定
```

> ⚠️ **現状の課題**: 二値分類のみ。本来は機械学習による連続スコアが望ましい。

---

## 🌌 相空間モデル (D, R, V)

攻撃の動態を3次元の物理量として表現する。

### D (Dispersion: 拡散性)

攻撃コマンドの多様性を Shannon Entropy で計量する。

```python
def calculate_D(recent_attacks):
    # 攻撃を16種類に分類
    command_types = [classify_command(a) for a in recent_attacks]

    # 確率分布を計算
    unique, counts = np.unique(command_types, return_counts=True)
    probs = counts / counts.sum()

    # Shannon Entropy で多様性を計量
    H = scipy.stats.entropy(probs, base=2)
    D = H / log2(num_unique_types)   # 正規化 → [0, 1]
    return D
```

- D → 1.0: 攻撃が多様（広範囲を探索中）
- D → 0.0: 攻撃が収束（特定手法に集中）

### R (Rhythm: リズム性)

攻撃間隔の規則性を変動係数 (CV) で計量する。

```python
def calculate_R(timestamps):
    intervals = [t[i+1] - t[i] for i in range(len(t)-1)]
    CV = std(intervals) / mean(intervals)
    R = 1 / (1 + CV)   # CV低い → R高い（規則的）
    return R
```

- R → 1.0: 規則的な攻撃（自動化ツール）
- R → 0.0: 不規則な攻撃（人間的・回避的）

### V (Controllability: 制御可能性)

直近50件の検知率を制御可能性として表現する。

```python
def calculate_V(recent_attacks):
    detected = sum(1 for a in recent_attacks if a.is_dangerous)
    V = detected / len(recent_attacks)   # 検知率そのもの
    return V
```

| V値 | 状態 | 色 |
|-----|------|----|
| V > 0.7 | SAFE | 🟢 緑 |
| 0.3 < V ≤ 0.7 | WARNING | 🟡 黄 |
| V ≤ 0.3 | CRITICAL | 🔴 赤 |

---

## 🧬 進化メトリクス

### RQ1: 共進化の定量評価

#### フェーズ別検知率

実験開始からの経過時間で3フェーズに分割する。

```
Phase 1 (0-6h):   初期 → 既知パターンを高確率で検知
Phase 2 (6-24h):  進化 → 変異攻撃により検知率が低下
Phase 3 (24-72h): 適応 → 防御側の再学習で回復
```

#### 検知率低下の傾き

```python
slope, intercept, *_ = scipy.stats.linregress(hours, detection_rates)
# slope < 0 → 検知率が時間とともに低下（攻撃の進化が有効）
```

#### 世代統計

```python
# 世代数の分布
distribution = {
    1: 277,  # 第1世代（元祖攻撃）
    2: 39,   # 第2世代
    3: 19,   # 第3世代
    4: 13,   # 第4世代
    5: 9,    # 第5世代
    6: 7     # 第6世代（最高世代）
}

# 3世代以上の割合（高度変異の指標）
gen_3plus_ratio = sum(v for k,v in distribution.items() if k >= 3) / total
```

---

### RQ2: 新規性の系統学的評価

3つの指標を統合して「系統学的距離（新規性スコア）」を計算する。

#### ① 遺伝的距離（Genetic Distance）

コマンド文字列の編集距離をベースにした類似度。

```python
from difflib import SequenceMatcher

similarity = SequenceMatcher(None, cmd1, cmd2).ratio()
genetic_distance = 1 - similarity
# 0.0 = 同一, 1.0 = 完全に異なる
```

#### ② 形態的距離（Morphological Distance）

コマンドの構文的特徴を12次元ベクトルで表現し、ユークリッド距離を計算。

```python
feature_vector = [
    len(command),          # 文字数
    len(command.split()),  # 単語数
    count('|'),            # パイプ数（連結の複雑さ）
    count(';'),            # セミコロン数
    count('$'),            # 変数参照数
    count('-'),            # オプション数
    has('invoke'),         # Invoke系コマンド使用
    has('get-'),           # Get系コマンド使用
    has('set-'),           # Set系コマンド使用
    has('new-'),           # New系コマンド使用
    has('iex|curl|wget'),  # ダウンロード系
    has('hidden|bypass'),  # ステルス系
]

distance = ||features_new - features_known||  # ユークリッド距離
```

#### ③ 生殖隔離（Reproductive Isolation）

5つのAVツールによる検知結果から「隔離スコア」を計算。
生物学の「生殖隔離」（新種が旧来の個体と交配できない）をAV検知回避に対応づけた指標。

```python
isolation_score = (5 - detection_count) / 5
# 0/5検知 → isolation = 1.0 (完全隔離 = Zero-Day)
# 5/5検知 → isolation = 0.0 (完全検知 = 既知パターン)
```

#### 統合新規性スコア（Phylogenetic Distance）

```python
phylogenetic_distance = (
    0.4 * genetic_distance       # 文字列レベルの新規性（重み: 40%）
    + 0.3 * morphological_distance  # 構造レベルの新規性（重み: 30%）
    + 0.3 * reproductive_isolation  # 検知回避レベル（重み: 30%）
)
```

| スコア範囲 | 分類 | 意味 |
|------------|------|------|
| 0.7 〜 1.0 | **New_Species** | 既知パターンと本質的に異なる |
| 0.5 〜 0.7 | **New_Variant** | 既知パターンの変異体 |
| 0.3 〜 0.5 | **Similar_Pattern** | 類似する既知パターンあり |
| 0.0 〜 0.3 | **Known_Pattern** | 既知パターンと一致 |

---

### RQ3: ドメイン間の適応放散

#### 系統樹形状メトリクス

| 指標 | 計算方法 | 意味 |
|------|----------|------|
| branch_factor | 各ノードの子ノード数の平均 | 1世代あたりの変異の広がり |
| tree_depth | MAX(generation) | 進化の深さ |
| colless_index | std(gen_counts) / mean(gen_counts) | 系統樹の非対称性 |
| leaf_count | 子を持たないノード数 | 末端変異体の数 |

#### ドメイン間統計検定

```python
# ノンパラメトリック検定（分布の仮定が不要）
h_stat, p_value = scipy.stats.kruskal(
    powershell_rates,
    webapp_rates,
    iot_rates,
    cloud_rates
)

# p < 0.05 → ドメイン間に有意差あり（適応放散が起きている）
# p ≥ 0.05 → ドメイン間に有意差なし（進化パターンは普遍的）
```

---

## 💾 データベース設計

### テーブル関係図

```
attack_events (中心テーブル)
├── event_id (PK)
├── command
├── domain           ← ドメイン分類
├── generation       ← 世代数
├── parent_ids[]     ← 親攻撃のID（系統樹の構築に使用）
├── novelty_score    ← 計算済みの新規性スコア
└── elapsed_hours    ← 実験開始からの経過時間
    │
    ├── detection_results (1:1)
    │   ├── is_dangerous
    │   └── anomaly_score
    │
    ├── av_detection_results (1:1)
    │   ├── windows_defender / symantec / mcafee / crowdstrike / sentinelone
    │   ├── detection_count
    │   └── is_zeroday
    │
    └── evolution_types (1:1)
        ├── evolution_type  (combination/derivation/mutation/advanced_mutation)
        └── generation_number

domain_summary (集計テーブル)
├── domain
├── known_patterns_count / novel_patterns_count
├── generation_rate
├── avg_novelty_score
└── zeroday_rate
```

---

## 🔧 既知の問題と改善案

### 1. 進化ロジックの未実装（最重要）

**現状**: Red TeamはGPT-4にランダムなプロンプトを投げるだけ。前世代を参照しない。

**改善案**:
```python
# 検知された攻撃を取得
detected = db.get_detected_attacks(domain)

# 進化プロンプトで再生成
prompt = f"""
この攻撃は検知された: {detected[-1]['command']}
検知キーワード: {detected[-1]['keyword']}

同じ目的を達成しつつ、上記キーワードを使わない
代替コマンドを1つ生成せよ。
"""
evolved = gpt4.generate(prompt)
db.save_attack(evolved, parent_id=detected[-1]['event_id'], generation=gen+1)
```

### 2. Blue AIの機械学習化

**現状**: キーワードマッチングのみ。難読化に無力。

**改善案**: `Invoke-Expression ([System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String('...')))` のようなBase64エンコード攻撃を検知できない。

→ **LSTMやBERTベースの異常検知モデル**への移行が必要。

### 3. 実環境AVスキャンの統合

**現状**: AV検知はシミュレーション（乱数）。

**改善案**: VirusTotal API や Windows Defender API との実統合。

---

## 📚 参考文献

- [Red Queen Hypothesis](https://en.wikipedia.org/wiki/Red_Queen_hypothesis) - 共進化の生物学的背景
- [Phylogenetic Analysis](https://en.wikipedia.org/wiki/Phylogenetics) - 系統学的距離の理論
- [MITRE ATT&CK Framework](https://attack.mitre.org/) - サイバー攻撃の分類体系
- [Adversarial Machine Learning](https://arxiv.org/abs/1810.00069) - 機械学習への攻撃
