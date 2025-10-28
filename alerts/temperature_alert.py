"""
Temperature Alert System - Discord Notifications
Theo dõi nhiệt độ TỪ MQTT và gửi cảnh báo qua Discord khi vượt ngưỡng
(Phiên bản cập nhật, có thêm trạng thái MƯA)
"""

import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

# MQTT Configuration
MQTT_BROKER = "192.168.1.9" 
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
TOPIC_SENSOR = "demo/garden/sensor/state"

# Discord Webhook Configuration
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1424942108313129005/24l_Jies7HOFm0e283fWE47QJYvNm9uWC5-g3-gKmyub7KuZmcT4rd62km-G2Klkykco"

# Alert Configuration
TEMP_THRESHOLD = 30.0  # Ngưỡng nhiệt độ (°C)
ALERT_COOLDOWN = 300   # Thời gian chờ giữa các cảnh báo (5 phút = 300 giây)

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

last_alert_time = 0
alert_active = False

# =============================================================================
# DISCORD FUNCTIONS
# =============================================================================

# <<< SỬA: Thêm 'is_raining' vào hàm
def send_discord_alert(temperature, humidity, rssi, is_raining):
    """Gửi cảnh báo lên Discord"""
    global last_alert_time
    
    current_time = time.time()
    
    if current_time - last_alert_time < ALERT_COOLDOWN:
        print(f"⏳ Cooldown active, skipping alert (wait {ALERT_COOLDOWN - (current_time - last_alert_time):.0f}s)")
        return
    
    # <<< SỬA: Thêm logic cho trạng thái mưa
    rain_status_str = "🌧️ Đang mưa" if is_raining else "☀️ Khô ráo"
    
    embed = {
        "title": "🚨 CẢNH BÁO NHIỆT ĐỘ CAO (VƯỜN)",
        "description": f"⚠️ Nhiệt độ vượt ngưỡng **{TEMP_THRESHOLD}°C**",
        "color": 16711680,  # Màu đỏ
        "fields": [
            {
                "name": "🌡️ Nhiệt độ hiện tại",
                "value": f"**{temperature}°C**",
                "inline": True
            },
            {
                "name": "💧 Độ ẩm",
                "value": f"{humidity}%",
                "inline": True
            },
            # <<< SỬA: Thêm trường Tình trạng mưa
            {
                "name": "🌧️ Tình trạng mưa",
                "value": f"**{rain_status_str}**",
                "inline": True
            },
            {
                "name": "📶 Tín hiệu",
                "value": f"{rssi} dBm",
                "inline": True # Sẽ tự động xuống dòng mới
            },
            {
                "name": "⏰ Thời gian",
                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "inline": False
            }
        ],
        "footer": { "text": "IoT Garden Alert System" },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    payload = {
        "username": "IoT Garden Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3093/3093173.png",
        "embeds": [embed]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        
        if response.status_code == 204:
            print(f"✅ Discord alert sent: {temperature}°C")
            last_alert_time = current_time
        else:
            print(f"❌ Failed to send Discord alert: {response.status_code}")
            print(f"   Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error sending Discord alert: {e}")

# <<< SỬA: Thêm 'is_raining' vào hàm
def send_discord_normal(temperature, humidity, is_raining):
    """Gửi thông báo nhiệt độ đã trở về bình thường"""
    
    # <<< SỬA: Thêm logic cho trạng thái mưa
    rain_status_str = "🌧️ Đang mưa" if is_raining else "☀️ Khô ráo"

    embed = {
        "title": "✅ NHIỆT ĐỘ TRỞ VỀ BÌNH THƯỜNG (VƯỜN)",
        "description": f"Nhiệt độ hiện tại dưới ngưỡng {TEMP_THRESHOLD}°C",
        "color": 65280,  # Màu xanh lá
        "fields": [
            {
                "name": "🌡️ Nhiệt độ hiện tại",
                "value": f"**{temperature}°C**",
                "inline": True
            },
            {
                "name": "💧 Độ ẩm",
                "value": f"{humidity}%",
                "inline": True
            },
            # <<< SỬA: Thêm trường Tình trạng mưa
            {
                "name": "🌧️ Tình trạng mưa",
                "value": f"{rain_status_str}",
                "inline": True
            },
            {
                "name": "⏰ Thời gian",
                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "inline": False
            }
        ],
        "footer": { "text": "IoT Garden Alert System" },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    payload = {
        "username": "IoT Garden Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3093/3093173.png",
        "embeds": [embed]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        
        if response.status_code == 204:
            print(f"✅ Discord normal notification sent: {temperature}°C")
        else:
            print(f"❌ Failed to send Discord notification: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error sending Discord notification: {e}")

# =============================================================================
# MQTT CALLBACKS
# =============================================================================

def on_connect(client, userdata, flags, rc):
    """Callback khi kết nối MQTT thành công"""
    if rc == 0:
        print("✅ Connected to MQTT broker: " + MQTT_BROKER)
        client.subscribe(TOPIC_SENSOR)
        print(f"📡 Subscribed to: {TOPIC_SENSOR}")
        print(f"🌡️  Monitoring temperature threshold: {TEMP_THRESHOLD}°C")
        print(f"⏱️  Alert cooldown: {ALERT_COOLDOWN} seconds")
    else:
        print(f"❌ Connection failed with code: {rc}")

def on_message(client, userdata, msg):
    """Callback khi nhận được message từ MQTT"""
    global alert_active
    
    try:
        data = json.loads(msg.payload.decode())
        
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        rssi = data.get('rssi')
        is_raining = data.get('is_raining') # <<< SỬA: Đọc thêm trạng thái mưa
        
        # <<< SỬA: Kiểm tra cả 2 giá trị
        if temperature is None or is_raining is None:
            print(" → ⚠️ Missing temp or rain data, skipping")
            return
        
        rain_status_str = "Raining" if is_raining else "Dry"
        print(f"🌡️  Current: {temperature}°C, {humidity}%, {rssi}dBm, Rain: {rain_status_str}", end="")
        
        if temperature > TEMP_THRESHOLD:
            print(f" → 🚨 HIGH TEMPERATURE!")
            if not alert_active:
                # <<< SỬA: Truyền 'is_raining'
                send_discord_alert(temperature, humidity, rssi, is_raining)
                alert_active = True
            else:
                # Vẫn kiểm tra cooldown
                send_discord_alert(temperature, humidity, rssi, is_raining)
        else:
            print(f" → ✅ Normal")
            if alert_active:
                # <<< SỬA: Truyền 'is_raining'
                send_discord_normal(temperature, humidity, is_raining)
                alert_active = False
                global last_alert_time
                last_alert_time = 0 
    
    except json.JSONDecodeError:
        print(f"⚠️  Invalid JSON: {msg.payload.decode()}")
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("╔════════════════════════════════════════════╗")
    print("║   Temperature Alert System (Garden)        ║")
    print("║   Discord Notifications (Rain Enabled)     ║") # <<< SỬA
    print("╚════════════════════════════════════════════╝")
    print(f"📡 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"🔔 Discord Webhook: Configured")
    print(f"🌡️  Temperature Threshold: {TEMP_THRESHOLD}°C")
    print(f"⏱️  Alert Cooldown: {ALERT_COOLDOWN} seconds")
    print("────────────────────────────────────────────")
    
    # Test Discord webhook
    print("\n🧪 Testing Discord webhook...")
    test_embed = {
        "title": "🚀 Garden Alert System Started",
        "description": f"Temperature & Rain monitoring active with threshold: **{TEMP_THRESHOLD}°C**", # <<< SỬA
        "color": 3447003,  # Màu xanh dương
        "fields": [
            { "name": "Status", "value": "✅ Online", "inline": True },
            { "name": "MQTT Broker", "value": f"{MQTT_BROKER}:{MQTT_PORT}", "inline": True }
        ],
        "footer": { "text": "IoT Garden Alert System" },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    test_payload = {
        "username": "IoT Garden Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3093/3093173.png",
        "embeds": [test_embed]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=test_payload)
        if response.status_code == 204:
            print("✅ Discord webhook test successful!")
        else:
            print(f"⚠️  Discord webhook test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord webhook test error: {e}")
    
    print("\n────────────────────────────────────────────")
    
    client = mqtt.Client(client_id="temp_alert_" + str(int(time.time())), protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        if MQTT_USERNAME:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        print("\n✅ Alert system started! Press Ctrl+C to stop")
        print("────────────────────────────────────────────\n")
        
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Alert system stopped by user")
        client.disconnect()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()