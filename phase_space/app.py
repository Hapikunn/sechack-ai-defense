from flask import Flask, render_template, jsonify
import sys
import os

sys.path.append('/app/shared')
from database import Database
from phase_space import PhaseSpaceModel

app = Flask(__name__)

# データベース接続
db_url = os.getenv('DB_URL', 'postgresql://user:password@timescaledb:5432/sechack')
db = Database(db_url)

# 相空間モデル
phase_space = PhaseSpaceModel(db)

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

@app.route('/api/phase-space')
def get_phase_space():
    """相空間モデルの現在状態"""
    try:
        state = phase_space.get_current_state()
        return jsonify(state)
    except Exception as e:
        print(f"⚠️ Phase Space Error: {e}")
        return jsonify({
            'D': 0.5,
            'R': 0.5,
            'V': 0.5,
            'status': 'ERROR',
            'color': '#808080',
            'timestamp': None
        })

@app.route('/api/phase-space/history')
def get_phase_space_history():
    """相空間の履歴"""
    try:
        minutes = int(request.args.get('minutes', 5))
        history = phase_space.get_history(minutes=minutes)
        return jsonify(history)
    except Exception as e:
        print(f"⚠️ History Error: {e}")
        return jsonify([])

if __name__ == '__main__':
    print("🌌 Dashboard Starting on http://localhost:3000")
    app.run(host='0.0.0.0', port=3000)