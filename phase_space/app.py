from flask import Flask, render_template, jsonify
import sys
import os

sys.path.append('/app/shared')
from database import Database

app = Flask(__name__)

# データベース接続
db_url = os.getenv('DB_URL', 'postgresql://user:password@timescaledb:5432/sechack')
db = Database(db_url)

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """システム状態を返す（実データ）"""
    try:
        attacks_count = db.get_attack_count()
        threats_count = db.get_detection_count()
        
        return jsonify({
            'attacks_detected': attacks_count,
            'threats_blocked': threats_count,
            'system_health': 'OK'
        })
    except Exception as e:
        print(f"⚠️ DB Error: {e}")
        return jsonify({
            'attacks_detected': 0,
            'threats_blocked': 0,
            'system_health': 'DB Error'
        })

@app.route('/api/recent')
def recent_attacks():
    """最近の攻撃を取得"""
    try:
        recent = db.get_recent_attacks(limit=10)
        return jsonify({'attacks': [dict(r) for r in recent]})
    except Exception as e:
        print(f"⚠️ DB Error: {e}")
        return jsonify({'attacks': []})

if __name__ == '__main__':
    print("🌌 Dashboard Starting on http://localhost:3000")
    app.run(host='0.0.0.0', port=3000)