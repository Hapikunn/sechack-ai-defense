from flask import Flask, render_template, jsonify, request
import sys
import os

sys.path.append('/app/shared')
from database import Database
from phase_space import PhaseSpaceModel
from metrics import EvolutionaryMetrics

app = Flask(__name__)

# データベース接続
db_url = os.getenv('DB_URL', 'postgresql://user:password@timescaledb:5432/sechack')
db = Database(db_url)

# 相空間モデル
phase_space = PhaseSpaceModel(db)

# 進化メトリクス
metrics = EvolutionaryMetrics(db)

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/poster')
def poster():
    """ポスター用データエクスポートページ"""
    return render_template('poster_data.html')

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RQ1: 共進化の結果取得
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/rq1/coevolution')
def get_coevolution_results():
    """
    共進化の定量的結果を返す
    
    GET /api/rq1/coevolution?domain=powershell
    """
    try:
        domain = request.args.get('domain', 'powershell')
        
        # データ取得
        timeline = db.get_detection_timeline(domain)
        gen_stats = db.get_generation_stats(domain)
        evo_types = db.get_evolution_types(domain)
        
        # メトリクス計算
        coevo_metrics = metrics.calculate_coevolution_metrics(domain)
        gen_metrics = metrics.calculate_generation_statistics(domain)
        
        return jsonify({
            'domain': domain,
            'coevolution': coevo_metrics,
            'generations': gen_metrics,
            'evolution_types': evo_types,
            'timeline': timeline
        })
    except Exception as e:
        print(f"⚠️ RQ1 Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RQ2: 新規性評価の結果取得
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/rq2/novelty')
def get_novelty_results():
    """
    新規性評価の統計を返す
    
    GET /api/rq2/novelty?domain=powershell
    """
    try:
        domain = request.args.get('domain', 'powershell')
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 新規攻撃の統計取得
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_novel,
                        AVG(novelty_score) as avg_score,
                        STDDEV(novelty_score) as std_score,
                        MIN(novelty_score) as min_score,
                        MAX(novelty_score) as max_score
                    FROM attack_events
                    WHERE domain = %s AND novelty_score IS NOT NULL
                """, (domain,))
                
                stats = cursor.fetchone()
                
                # AV検知統計
                cursor.execute("""
                    SELECT 
                        detection_count,
                        COUNT(*) as count
                    FROM av_detection_results av
                    JOIN attack_events a ON av.attack_id = a.event_id
                    WHERE a.domain = %s
                    GROUP BY detection_count
                    ORDER BY detection_count
                """, (domain,))
                
                av_stats = {f"{row[0]}_of_5": row[1] for row in cursor.fetchall()}
        
        return jsonify({
            'domain': domain,
            'total_novel': int(stats[0]) if stats[0] else 0,
            'novelty_score_stats': {
                'mean': round(float(stats[1]), 4) if stats[1] else 0.0,
                'std': round(float(stats[2]), 4) if stats[2] else 0.0,
                'min': round(float(stats[3]), 4) if stats[3] else 0.0,
                'max': round(float(stats[4]), 4) if stats[4] else 0.0
            },
            'av_detection_stats': av_stats
        })
    except Exception as e:
        print(f"⚠️ RQ2 Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RQ3: ドメイン比較の結果取得
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/rq3/domain_comparison')
def get_domain_comparison():
    """
    4ドメインの比較統計を返す
    
    GET /api/rq3/domain_comparison
    """
    try:
        domains = ['powershell', 'webapp', 'iot', 'cloud']
        
        domain_results = {}
        for domain in domains:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            known_patterns_count,
                            novel_patterns_count,
                            generation_rate,
                            avg_novelty_score,
                            zeroday_count,
                            zeroday_rate,
                            max_generation
                        FROM domain_summary
                        WHERE domain = %s
                    """, (domain,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        domain_results[domain] = {
                            'known': result[0],
                            'novel': result[1],
                            'generation_rate': float(result[2]) if result[2] else 0.0,
                            'avg_novelty_score': float(result[3]) if result[3] else 0.0,
                            'zeroday_count': result[4],
                            'zeroday_rate': float(result[5]) if result[5] else 0.0,
                            'max_generation': result[6]
                        }
                    
                    # 系統樹メトリクス
                    tree_metrics = metrics.calculate_tree_shape_metrics(domain)
                    domain_results[domain]['tree_metrics'] = tree_metrics
        
        # 統計的検定
        statistical_tests = metrics.compare_domains(domains)
        
        return jsonify({
            'domains': domain_results,
            'statistical_tests': statistical_tests
        })
    except Exception as e:
        print(f"⚠️ RQ3 Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ポスター用グラフデータ生成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/api/poster/graphs')
def get_poster_graphs():
    """
    ポスター掲載用のグラフデータを一括取得
    """
    try:
        domain = request.args.get('domain', 'powershell')
        
        # RQ1データ
        rq1_data = get_coevolution_results().get_json()
        
        # RQ2データ
        rq2_data = get_novelty_results().get_json()
        
        # RQ3データ
        rq3_data = get_domain_comparison().get_json()
        
        return jsonify({
            'rq1': rq1_data,
            'rq2': rq2_data,
            'rq3': rq3_data
        })
    except Exception as e:
        print(f"⚠️ Poster Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌌 Dashboard Starting on http://localhost:3000")
    app.run(host='0.0.0.0', port=3000)