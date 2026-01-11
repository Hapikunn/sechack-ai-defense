import redis
import json
import time

class EventBus:
    """メッセージバス（簡易版）"""
    
    def __init__(self, redis_url="redis://localhost:6379"):
        print(f"Connecting to Redis: {redis_url}")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        print("✅ Connected to Redis!")
    
    def send_attack(self, attack_data):
        """攻撃データを送信"""
        message = json.dumps(attack_data)
        self.redis.xadd('attacks', {'data': message})
        print(f"📤 Sent attack: {attack_data['command']}")
    
    def receive_attacks(self):
        """攻撃データを受信（ループ）"""
        print("👂 Listening for attacks...")
        last_id = '0-0'
        
        while True:
            messages = self.redis.xread({'attacks': last_id}, count=1, block=5000)
            
            if messages:
                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        attack = json.loads(message_data['data'])
                        yield attack
                        last_id = message_id