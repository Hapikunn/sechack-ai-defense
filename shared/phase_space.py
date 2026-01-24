"""
相空間モデル (D, R, V) 計算
"""
import numpy as np
from scipy.stats import entropy as shannon_entropy
from datetime import datetime, timedelta

class PhaseSpaceModel:
    """
    相空間モデル - AIの判断を物理量に変換
    """
    
    def __init__(self, db):
        self.db = db
        self.window_size = 50  # 過去50イベントを分析
    
    def calculate_D(self):
        """
        D (Dispersion): 拡散性
        Shannon Entropy - コマンドの多様性
        """
        try:
            recent = self.db.get_recent_attacks(limit=self.window_size)
            
            if len(recent) == 0:
                return 0.5
            
            command_types = []
            for attack in recent:
                cmd = attack['command']
                cmd_type = self._classify_command(cmd)
                command_types.append(cmd_type)
            
            unique, counts = np.unique(command_types, return_counts=True)
            
            if len(unique) == 1:
                return 0.0
            
            probabilities = counts / counts.sum()
            H = shannon_entropy(probabilities, base=2)
            
            max_entropy = np.log2(len(unique))
            D = H / max_entropy if max_entropy > 0 else 0.0
            
            return float(np.clip(D, 0.0, 1.0))
            
        except Exception as e:
            print(f"⚠️ Error calculating D: {e}")
            return 0.5
    
    def calculate_R(self):
        """
        R (Rhythm): リズム
        """
        try:
            recent = self.db.get_recent_attacks(limit=self.window_size)
            
            if len(recent) < 10:
                return 0.5
            
            timestamps = []
            for attack in recent:
                ts = attack['timestamp']
                
                if isinstance(ts, datetime):
                    timestamps.append(ts)
                elif isinstance(ts, str):
                    timestamps.append(datetime.fromisoformat(ts))
                else:
                    continue
            
            if len(timestamps) < 10:
                return 0.5
            
            intervals = []
            for i in range(1, len(timestamps)):
                delta = (timestamps[i] - timestamps[i-1]).total_seconds()
                intervals.append(abs(delta))
            
            if len(intervals) < 5:
                return 0.5
            
            intervals_array = np.array(intervals)
            mean_interval = np.mean(intervals_array)
            std_interval = np.std(intervals_array)
            
            cv = std_interval / mean_interval if mean_interval > 0 else 1.0
            R = 1.0 / (1.0 + cv)
            
            return float(np.clip(R, 0.0, 1.0))
            
        except Exception as e:
            print(f"⚠️ Error calculating R: {e}")
            return 0.5
    
    def calculate_V(self):
        """
        V (Controllability): 制御可能性
        """
        try:
            recent = self.db.get_recent_attacks(limit=self.window_size)
            
            if len(recent) == 0:
                print("[V] No attacks - returning 1.0")
                return 1.0
            
            print(f"[V] Analyzing {len(recent)} attacks")
            
            # 検知カウント
            detected_count = 0
            total_count = 0
            
            for attack in recent:
                total_count += 1
                is_dangerous = attack.get('is_dangerous')
                
                # is_dangerousがTrueの場合のみカウント
                # Noneやfalseは「検知失敗」
                if is_dangerous is True:
                    detected_count += 1
                    print(f"[V] ✓ Attack {attack.get('event_id')}: DETECTED")
                else:
                    print(f"[V] ✗ Attack {attack.get('event_id')}: MISSED (is_dangerous={is_dangerous})")
            
            detection_rate = detected_count / total_count if total_count > 0 else 0.0
            
            print(f"[V] Detection rate: {detected_count}/{total_count} = {detection_rate:.3f}")
            
            V = detection_rate
            
            return float(np.clip(V, 0.0, 1.0))
            
        except Exception as e:
            print(f"⚠️ Error calculating V: {e}")
            import traceback
            traceback.print_exc()
            return 0.5
    
    def _classify_command(self, cmd):
        """コマンド分類"""
        cmd_lower = cmd.lower()

        # 詳細な分類
        keywords = {
            'file_search_recursive': ['recurse', '-r '],
            'file_search_filter': ['include', 'filter', 'findstr'],
            'file_search_simple': ['get-childitem', 'dir', 'ls'],
            'network_download': ['invoke-webrequest', 'wget', 'iwr'],
            'network_upload': ['curl', 'upload', 'post'],
            'network_scan': ['test-connection', 'ping', 'nslookup'],
            'user_create': ['net user', 'useradd', '/add'],
            'user_modify': ['passwd', 'password', 'usermod'],
            'process_list': ['get-process', 'ps', 'tasklist'],
            'process_kill': ['stop-process', 'kill', 'taskkill'],
            'archive_create': ['compress-archive', 'zip'],
            'archive_extract': ['expand-archive', 'unzip'],
            'execution_invoke': ['invoke-expression', 'iex'],
            'execution_script': ['powershell', '.ps1', '.bat'],
            'data_exfiltration': ['out-file', 'export', '> '],
            'stealth_ops': ['erroraction', 'silentlycontinue', 'hidden'],
        }

        # 優先順位で分類（より具体的なものから）
        for category, words in keywords.items():
            if any(word in cmd_lower for word in words):
                return category
    
        return 'other'
    
    def get_current_state(self):
        """現在の相空間状態"""
        print("\n" + "="*50)
        print("Calculating Phase Space State")
        print("="*50)
        
        D = self.calculate_D()
        R = self.calculate_R()
        V = self.calculate_V()
        
        print(f"\nResults: D={D:.3f}, R={R:.3f}, V={V:.3f}")
        
        # 状態判定
        if V > 0.7:
            status = 'SAFE'
            color = '#00ff00'
        elif V > 0.3:
            status = 'WARNING'
            color = '#ffff00'
        else:
            status = 'CRITICAL'
            color = '#ff0000'
        
        print(f"Status: {status}\n")
        
        return {
            'D': round(D, 3),
            'R': round(R, 3),
            'V': round(V, 3),
            'status': status,
            'color': color,
            'timestamp': datetime.now().isoformat()
        }