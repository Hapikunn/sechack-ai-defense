import sys
import os

sys.path.append('/app/shared')
from messaging import EventBus
from database import Database

# 危険なキーワード
DANGEROUS_KEYWORDS = ['Recurse', 'Invoke-WebRequest', 'net user', 'password']

def is_dangerous(command):
    """コマンドが危険かチェック"""
    for keyword in DANGEROUS_KEYWORDS:
        if keyword.lower() in command.lower():
            return True, keyword
    return False, None

def main():
    print("🔵 Blue AI Starting...")
    
    # Redis接続
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    event_bus = EventBus(redis_url)
    
    # データベース接続
    db_url = os.getenv('DB_URL', 'postgresql://user:password@timescaledb:5432/sechack')
    db = Database(db_url)
    
    for attack in event_bus.receive_attacks():
        print(f"\n📥 Received: {attack['command']}")
        
        # 危険性をチェック
        dangerous, keyword = is_dangerous(attack['command'])
        
        if dangerous:
            print(f"🚨 ALERT! Dangerous command detected!")
            print(f"   Reason: Contains '{keyword}'")
            score = 0.8
        else:
            print(f"✅ Safe command")
            score = 0.2
        
        # データベースに保存
        try:
            db.save_detection(
                event_id=attack['id'],
                is_dangerous=dangerous,
                keyword=keyword,
                score=score
            )
            print(f"💾 Detection result saved to database")
        except Exception as e:
            print(f"⚠️ DB Error: {e}")

if __name__ == '__main__':
    main()