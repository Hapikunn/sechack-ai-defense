"""
進化的メトリクス計算モジュール
生物学的視点での共進化・新規性・適応放散の定量評価
"""
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from difflib import SequenceMatcher
import re


class EvolutionaryMetrics:
    """
    生物学的視点での進化評価指標
    """
    
    def __init__(self, db):
        self.db = db
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RQ1: 共進化の測定
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def calculate_coevolution_metrics(self, domain='powershell'):
        """
        時系列での検知率変化を分析
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 時系列データ取得
                cursor.execute("""
                    SELECT 
                        EXTRACT(EPOCH FROM (a.timestamp - MIN(a.timestamp) OVER())) / 3600 as hours,
                        d.is_dangerous
                    FROM attack_events a
                    LEFT JOIN detection_results d ON a.event_id = d.event_id
                    WHERE a.domain = %s
                    ORDER BY a.timestamp
                """, (domain,))
                
                data = cursor.fetchall()
                
                if not data or len(data) == 0:
                    return {
                        'phase_1_detection_rate': 0.0,
                        'phase_2_detection_rate': 0.0,
                        'phase_3_detection_rate': 0.0,
                        'decline_rate': 0.0,
                        'equilibrium_point': 0.0
                    }
                
                # フェーズ別の検知率計算
                phase_1 = [d[1] for d in data if d[0] is not None and d[0] <= 6]
                phase_2 = [d[1] for d in data if d[0] is not None and 6 < d[0] <= 24]
                phase_3 = [d[1] for d in data if d[0] is not None and d[0] > 24]
                
                phase_1_rate = sum(1 for x in phase_1 if x) / len(phase_1) if phase_1 else 0.0
                phase_2_rate = sum(1 for x in phase_2 if x) / len(phase_2) if phase_2 else 0.0
                phase_3_rate = sum(1 for x in phase_3 if x) / len(phase_3) if phase_3 else 0.0
                
                # 線形回帰で傾きを計算
                valid_data = [(d[0], d[1]) for d in data if d[0] is not None]
                
                if len(valid_data) > 1:
                    hours = np.array([d[0] for d in valid_data])
                    detections = np.array([1 if d[1] else 0 for d in valid_data])
                    
                    try:
                        slope, intercept, r_value, p_value, std_err = stats.linregress(hours, detections)
                        decline_rate = float(slope)
                    except:
                        decline_rate = 0.0
                else:
                    decline_rate = 0.0
                    intercept = 0.0
                
                # 平衡点（検知率50%に達する時間）
                if decline_rate < 0 and intercept != 0:
                    equilibrium = (0.5 - intercept) / decline_rate
                else:
                    equilibrium = 0.0
                
                return {
                    'phase_1_detection_rate': round(float(phase_1_rate), 4),
                    'phase_2_detection_rate': round(float(phase_2_rate), 4),
                    'phase_3_detection_rate': round(float(phase_3_rate), 4),
                    'decline_rate': round(float(decline_rate), 4),
                    'equilibrium_point': round(float(max(0, equilibrium)), 2)
                }
    
    def calculate_generation_statistics(self, domain='powershell'):
        """
        世代数の統計
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT generation, COUNT(*) as count
                    FROM attack_events
                    WHERE domain = %s AND generation IS NOT NULL
                    GROUP BY generation
                    ORDER BY generation
                """, (domain,))
                
                results = cursor.fetchall()
                
                if not results:
                    return {
                        'max_generation': 1,
                        'mean_generation': 1.0,
                        'generation_distribution': {1: 0},
                        'generation_3plus_ratio': 0.0
                    }
                
                generations = []
                distribution = {}
                total_count = 0
                gen_3plus_count = 0
                
                for gen, count in results:
                    distribution[int(gen)] = int(count)
                    generations.extend([gen] * count)
                    total_count += count
                    if gen >= 3:
                        gen_3plus_count += count
                
                mean_gen = float(np.mean(generations)) if generations else 1.0
                
                return {
                    'max_generation': int(max(distribution.keys())) if distribution else 1,
                    'mean_generation': round(mean_gen, 2),
                    'generation_distribution': distribution,
                    'generation_3plus_ratio': round(float(gen_3plus_count) / float(total_count), 4) if total_count > 0 else 0.0
                }
    
    def classify_evolution_type(self, attack):
        """
        進化タイプの分類
        """
        if not attack.get('parent_ids') or len(attack['parent_ids']) == 0:
            return 'original'
        
        parent_count = len(attack['parent_ids'])
        generation = attack.get('generation', 1)
        
        if parent_count >= 2:
            return 'combination'
        
        if generation >= 4:
            return 'advanced_mutation'
        elif generation >= 2:
            return 'mutation'
        else:
            return 'derivation'
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RQ2: 新規性の系統学的評価
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def calculate_genetic_distance(self, cmd1, cmd2):
        """
        遺伝的距離（編集距離）
        """
        if not cmd1 or not cmd2:
            return {
                'levenshtein_distance': 0,
                'max_length': 0,
                'similarity': 0.0,
                'is_similar': False
            }
        
        similarity = SequenceMatcher(None, cmd1, cmd2).ratio()
        max_len = max(len(cmd1), len(cmd2))
        lev_distance = int(max_len * (1 - similarity))
        
        return {
            'levenshtein_distance': lev_distance,
            'max_length': max_len,
            'similarity': round(float(similarity), 4),
            'is_similar': similarity >= 0.85
        }
    
    def calculate_morphological_distance(self, command, known_commands):
        """
        形態的距離（構文的特徴の差）
        """
        features = self._extract_command_features(command)
        
        if not known_commands:
            return {
                'feature_vector': features,
                'distance_from_known': 1.0,
                'cluster_assignment': 'Novel_Cluster_1'
            }
        
        min_distance = float('inf')
        for known_cmd in known_commands:
            known_features = self._extract_command_features(known_cmd)
            distance = float(np.linalg.norm(np.array(features) - np.array(known_features)))
            min_distance = min(min_distance, distance)
        
        normalized_distance = min(min_distance / 10.0, 1.0)
        
        if normalized_distance < 0.3:
            cluster = 'Known_Cluster'
        elif normalized_distance < 0.7:
            cluster = 'Similar_Cluster'
        else:
            cluster = f'Novel_Cluster_{int(normalized_distance * 10)}'
        
        return {
            'feature_vector': features,
            'distance_from_known': round(float(normalized_distance), 4),
            'cluster_assignment': cluster
        }
    
    def _extract_command_features(self, command):
        """
        コマンドから12次元の特徴ベクトルを抽出
        """
        if not command:
            return [0] * 12
        
        cmd_lower = command.lower()
        
        features = [
            len(command),
            len(command.split()),
            command.count('|'),
            command.count(';'),
            command.count('$'),
            command.count('-'),
            1 if 'invoke' in cmd_lower else 0,
            1 if 'get-' in cmd_lower else 0,
            1 if 'set-' in cmd_lower else 0,
            1 if 'new-' in cmd_lower else 0,
            1 if any(x in cmd_lower for x in ['iex', 'iwr', 'curl', 'wget']) else 0,
            1 if any(x in cmd_lower for x in ['hidden', 'bypass', 'encoded']) else 0,
        ]
        
        return features
    
    def calculate_reproductive_isolation(self, attack_id):
        """
        生殖隔離（検知隔離）
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        detection_count,
                        is_zeroday
                    FROM av_detection_results
                    WHERE attack_id = %s
                """, (attack_id,))
                
                result = cursor.fetchone()
                
                if not result:
                    return {
                        'detection_count': 0,
                        'total_av': 5,
                        'isolation_score': 1.0,
                        'is_zeroday': True
                    }
                
                detection_count, is_zeroday = result
                total_av = 5
                isolation_score = (total_av - detection_count) / total_av
                
                return {
                    'detection_count': int(detection_count),
                    'total_av': total_av,
                    'isolation_score': round(float(isolation_score), 4),
                    'is_zeroday': bool(is_zeroday)
                }
    
    def calculate_novelty_score(self, attack_id, command, known_commands):
        """
        統合新規性スコア
        """
        genetic_distances = []
        for known_cmd in known_commands:
            dist = self.calculate_genetic_distance(command, known_cmd)
            genetic_distances.append(1 - dist['similarity'])
        
        genetic_distance = min(genetic_distances) if genetic_distances else 1.0
        
        morph_result = self.calculate_morphological_distance(command, known_commands)
        morphological_distance = morph_result['distance_from_known']
        
        isolation_result = self.calculate_reproductive_isolation(attack_id)
        reproductive_isolation = isolation_result['isolation_score']
        
        phylogenetic_distance = (
            0.4 * genetic_distance +
            0.3 * morphological_distance +
            0.3 * reproductive_isolation
        )
        
        if phylogenetic_distance >= 0.7:
            classification = 'New_Species'
        elif phylogenetic_distance >= 0.5:
            classification = 'New_Variant'
        elif phylogenetic_distance >= 0.3:
            classification = 'Similar_Pattern'
        else:
            classification = 'Known_Pattern'
        
        return {
            'genetic_distance': round(float(genetic_distance), 4),
            'morphological_distance': round(float(morphological_distance), 4),
            'reproductive_isolation': round(float(reproductive_isolation), 4),
            'phylogenetic_distance': round(float(phylogenetic_distance), 4),
            'classification': classification
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RQ3: 適応放散の測定
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def calculate_tree_shape_metrics(self, domain='powershell'):
        """
        系統樹形状の定量化
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        MAX(generation) as max_gen,
                        COUNT(*) as total_attacks,
                        COUNT(DISTINCT generation) as gen_count
                    FROM attack_events
                    WHERE domain = %s
                """, (domain,))
                
                stats = cursor.fetchone()
                max_gen, total_attacks, gen_count = stats
                
                cursor.execute("""
                    SELECT 
                        event_id,
                        generation,
                        parent_ids
                    FROM attack_events
                    WHERE domain = %s
                    ORDER BY generation, event_id
                """, (domain,))
                
                nodes = cursor.fetchall()
                
                parent_child_counts = {}
                leaf_nodes = set()
                
                for event_id, generation, parent_ids in nodes:
                    leaf_nodes.add(event_id)
                    
                    if parent_ids:
                        for parent_id in parent_ids:
                            if parent_id in leaf_nodes:
                                leaf_nodes.remove(parent_id)
                            parent_child_counts[parent_id] = parent_child_counts.get(parent_id, 0) + 1
                
                branch_factors = list(parent_child_counts.values())
                avg_branch_factor = float(np.mean(branch_factors)) if branch_factors else 0.0
                
                cursor.execute("""
                    SELECT generation, COUNT(*) as count
                    FROM attack_events
                    WHERE domain = %s
                    GROUP BY generation
                    ORDER BY generation
                """, (domain,))
                
                gen_counts = [row[1] for row in cursor.fetchall()]
                
                if gen_counts and np.mean(gen_counts) > 0:
                    colless_index = float(np.std(gen_counts)) / float(np.mean(gen_counts))
                else:
                    colless_index = 0.0
                
                if colless_index < 0.3:
                    tree_balance = 'Balanced'
                elif colless_index < 0.6:
                    tree_balance = 'Moderately_Imbalanced'
                else:
                    tree_balance = 'Imbalanced'
                
                return {
                    'branch_factor': round(avg_branch_factor, 2),
                    'tree_depth': int(max_gen) if max_gen else 1,
                    'colless_index': round(colless_index, 4),
                    'leaf_count': len(leaf_nodes),
                    'tree_balance': tree_balance
                }
    
    def compare_domains(self, domains=['powershell', 'webapp', 'iot', 'cloud']):
        """
        ドメイン間比較
        """
        domain_data = {}
        
        for domain in domains:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            generation_rate,
                            avg_novelty_score,
                            zeroday_rate
                        FROM domain_summary
                        WHERE domain = %s
                    """, (domain,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        domain_data[domain] = {
                            'generation_rate': float(result[0]) if result[0] else 0.0,
                            'avg_novelty_score': float(result[1]) if result[1] else 0.0,
                            'zeroday_rate': float(result[2]) if result[2] else 0.0
                        }
        
        if len(domain_data) < 2:
            return {
                'kruskal_wallis_h': 0.0,
                'p_value': 1.0,
                'significant': False,
                'coefficient_of_variation': {
                    'generation_rate': 0.0,
                    'novelty_score': 0.0,
                    'zeroday_rate': 0.0
                }
            }
        
        generation_rates = [d['generation_rate'] for d in domain_data.values()]
        
        if len(set(generation_rates)) > 1:
            try:
                h_stat, p_value = stats.kruskal(*[[rate] for rate in generation_rates])
                h_stat = float(h_stat)
                p_value = float(p_value)
            except:
                h_stat, p_value = 0.0, 1.0
        else:
            h_stat, p_value = 0.0, 1.0
        
        cv_gen_rate = float(np.std(generation_rates)) / float(np.mean(generation_rates)) if np.mean(generation_rates) > 0 else 0.0
        
        novelty_scores = [d['avg_novelty_score'] for d in domain_data.values()]
        cv_novelty = float(np.std(novelty_scores)) / float(np.mean(novelty_scores)) if np.mean(novelty_scores) > 0 else 0.0
        
        zeroday_rates = [d['zeroday_rate'] for d in domain_data.values()]
        cv_zeroday = float(np.std(zeroday_rates)) / float(np.mean(zeroday_rates)) if np.mean(zeroday_rates) > 0 else 0.0
        
        return {
            'kruskal_wallis_h': round(h_stat, 2),
            'p_value': round(p_value, 3),
            'significant': p_value < 0.05,
            'coefficient_of_variation': {
                'generation_rate': round(cv_gen_rate, 4),
                'novelty_score': round(cv_novelty, 4),
                'zeroday_rate': round(cv_zeroday, 4)
            }
        }
