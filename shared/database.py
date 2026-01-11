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
                cursor.execute(
                    """
                    INSERT INTO attack_events (
                        event_id, timestamp, session_id, user_id, command, attack_number
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        attack_data.get('id', 'unknown'),
                        attack_data.get('timestamp'),
                        'session_001',  # 後で動的に変更可能
                        attack_data.get('user'),
                        attack_data.get('command'),
                        attack_data.get('id')
                    )
                )
    
    def save_detection(self, event_id, is_dangerous, keyword=None, score=0.0):
        """検知結果を保存"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO detection_results (
                        event_id, timestamp, is_dangerous, detected_keyword, anomaly_score
                    ) VALUES (%s, NOW(), %s, %s, %s)
                    """,
                    (event_id, is_dangerous, keyword, score)
                )
    
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