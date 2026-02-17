import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import time

class Database:
    """データベース接続マネージャー"""
    
    def __init__(self, db_url):
        self.db_url = db_url
        # 接続テスト（最大10回リトライ）
        for i in range(10):
            try:
                with self.get_connection() as conn:
                    print("✅ Connected to PostgreSQL!")
                break
            except Exception as e:
                print(f"⏳ Waiting for PostgreSQL... ({i+1}/10)")
                time.sleep(2)
    
    @contextmanager
    def get_connection(self):
        """データベース接続を取得"""
        conn = psycopg2.connect(self.db_url)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_attack(self, attack_data):
        """攻撃データを保存"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # idを文字列に変換
                    event_id = str(attack_data.get('id', 'unknown'))
                    
                    print(f"[DB] Inserting attack with event_id={event_id}")
                    
                    cursor.execute(
                        """
                        INSERT INTO attack_events (
                            event_id, timestamp, session_id, user_id, command, attack_number
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (event_id) DO NOTHING
                        """,
                        (
                            event_id,  # ← 文字列に統一
                            attack_data.get('timestamp'),
                            'session_001',
                            attack_data.get('user'),
                            attack_data.get('command'),
                            attack_data.get('id')
                        )
                    )
                    
                    print(f"[DB] ✓ Attack saved: event_id={event_id}")
                    
                except Exception as e:
                    print(f"[DB] ✗ Error saving attack: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
    
    def save_detection(self, event_id, is_dangerous, keyword=None, score=0.0):
        """検知結果を保存"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # event_idを文字列に変換（重要！）
                    event_id_str = str(event_id)

                    print(f"[DB] Inserting detection for event_id={event_id_str}")

                    cursor.execute(
                        """
                        INSERT INTO detection_results (
                            event_id, timestamp, is_dangerous, detected_keyword, anomaly_score
                        ) VALUES (%s, NOW(), %s, %s, %s)
                        """,
                        (event_id_str, is_dangerous, keyword, score)
                    )

                    print(f"[DB] ✓ Detection saved: event_id={event_id_str}, is_dangerous={is_dangerous}")

                except Exception as e:
                    print(f"[DB] ✗ Error saving detection: {e}")
                    import traceback
                    traceback.print_exc()
                    raise  # エラーを上に伝える
    
    def get_attack_count(self):
        """攻撃の総数を取得"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM attack_events")
                return cursor.fetchone()[0]
    
    def get_detection_count(self):
        """検知された脅威の数を取得"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM detection_results WHERE is_dangerous = true"
                )
                return cursor.fetchone()[0]
    
    def get_recent_attacks(self, limit=10):
        """最近の攻撃を取得"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT a.*, d.is_dangerous, d.detected_keyword
                    FROM attack_events a
                    LEFT JOIN detection_results d ON a.event_id = d.event_id
                    ORDER BY a.timestamp DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
                return cursor.fetchall()
    
    def get_recent_attacks(self, limit=50):
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT 
                        a.event_id,
                        a.timestamp,
                        a.command,
                        d.is_dangerous,
                        d.detected_keyword,
                        d.anomaly_score
                    FROM attack_events a
                    LEFT JOIN detection_results d ON a.event_id = d.event_id
                    ORDER BY a.timestamp DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
                return cursor.fetchall()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 新規メソッド: メトリクス用データ取得
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_detection_timeline(self, domain='powershell'):
        """時系列での検知率データを取得"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM detection_timeline
                    WHERE domain = %s
                    ORDER BY elapsed_hours
                    """,
                    (domain,)
                )
                return cursor.fetchall()
    
    def get_generation_stats(self, domain='powershell'):
        """世代別統計を取得"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM generation_stats
                    WHERE domain = %s
                    ORDER BY generation_number
                    """,
                    (domain,)
                )
                return cursor.fetchall()
    
    def get_evolution_types(self, domain='powershell'):
        """進化タイプ別の統計を取得"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT 
                        et.evolution_type,
                        COUNT(*) as count
                    FROM evolution_types et
                    JOIN attack_events a ON et.attack_id = a.event_id
                    WHERE a.domain = %s
                    GROUP BY et.evolution_type
                    """,
                    (domain,)
                )
                results = cursor.fetchall()
                return {row['evolution_type']: row['count'] for row in results}
    
    def get_known_commands(self, domain='powershell'):
        """既知の攻撃コマンド一覧を取得（新規性評価用）"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT command
                    FROM attack_events
                    WHERE domain = %s AND generation = 1
                    """,
                    (domain,)
                )
                return [row[0] for row in cursor.fetchall()]
    
    def save_detection_timeline_entry(self, domain, elapsed_hours, total, detected, missed, rate, phase):
        """検知率のタイムラインエントリを保存"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO detection_timeline 
                    (domain, elapsed_hours, total_attacks, detected_count, missed_count, detection_rate, phase)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (domain, elapsed_hours, total, detected, missed, rate, phase)
                )
    
    def save_generation_stat(self, domain, generation, count, avg_novelty, zeroday_count):
        """世代別統計を保存"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO generation_stats
                    (domain, generation_number, attack_count, avg_novelty_score, zeroday_count)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (domain, generation, count, avg_novelty, zeroday_count)
                )
    
    def save_av_detection_result(self, attack_id, detections):
        """AV検知結果を保存"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                detection_count = sum(detections.values())
                is_zeroday = detection_count == 0
                
                cursor.execute("""
                    SELECT 1 FROM av_detection_results WHERE attack_id = %s
                """, (attack_id,))
                
                exists = cursor.fetchone()
                
                if exists:
                    cursor.execute(
                        """
                        UPDATE av_detection_results SET
                            windows_defender = %s,
                            symantec = %s,
                            mcafee = %s,
                            crowdstrike = %s,
                            sentinelone = %s,
                            detection_count = %s,
                            is_zeroday = %s,
                            timestamp = NOW()
                        WHERE attack_id = %s
                        """,
                        (
                            detections.get('windows_defender', False),
                            detections.get('symantec', False),
                            detections.get('mcafee', False),
                            detections.get('crowdstrike', False),
                            detections.get('sentinelone', False),
                            detection_count,
                            is_zeroday,
                            attack_id
                        )
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO av_detection_results
                        (attack_id, windows_defender, symantec, mcafee, crowdstrike, sentinelone, detection_count, is_zeroday)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            attack_id,
                            detections.get('windows_defender', False),
                            detections.get('symantec', False),
                            detections.get('mcafee', False),
                            detections.get('crowdstrike', False),
                            detections.get('sentinelone', False),
                            detection_count,
                            is_zeroday
                        )
                    )
    
    def update_domain_summary(self, domain, summary_data):
        """ドメインサマリーを更新"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
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
                        experiment_duration_hours = EXCLUDED.experiment_duration_hours,
                        last_updated = NOW()
                    """,
                    (
                        domain,
                        summary_data.get('known_patterns_count', 0),
                        summary_data.get('novel_patterns_count', 0),
                        summary_data.get('generation_rate', 0.0),
                        summary_data.get('avg_novelty_score', 0.0),
                        summary_data.get('zeroday_count', 0),
                        summary_data.get('zeroday_rate', 0.0),
                        summary_data.get('max_generation', 1),
                        summary_data.get('experiment_duration_hours', 0)
                    )
                )
