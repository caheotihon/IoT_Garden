"""
MQTT to Database Logger
Lắng nghe MQTT messages và lưu vào SQLite database
ĐÃ ĐƯỢC CẬP NHẬT CHO "demo/garden" (Dùng "light" và "pump")
"""

import sqlite3
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# =============================================================================
# CONFIGURATION
# =============================================================================

# MQTT Configuration
MQTT_BROKER = "192.168.1.7" # <<< SỬA: Dùng IP của bạn
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
TOPIC_NS = "demo/garden"

# Database Configuration
DB_FILE = "iot_garden_data.db" 

# =============================================================================
# DATABASE SETUP
# =============================================================================

def init_database():
    """Tạo database và các bảng nếu chưa có"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Bảng sensor_data (Giữ nguyên)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_timestamp INTEGER,
            temperature REAL,
            humidity REAL,
            rain_analog INTEGER, 
            rain_digital INTEGER,
            is_raining BOOLEAN, 
            rssi INTEGER
        )
    """)
    
    # Bảng device_state
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_timestamp INTEGER,
            light TEXT, 
            pump TEXT, 
            pumpSpeed INTEGER, 
            rssi INTEGER
        )
    """) # <<< SỬA: Đổi lại thành 'light'
    
    # Bảng device_online (Giữ nguyên)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_online (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_timestamp INTEGER,
            online BOOLEAN,
            device_id TEXT,
            firmware TEXT,
            rssi INTEGER
        )
    """)
    
    # Bảng commands (Giữ nguyên)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            command_type TEXT,
            command_value TEXT,
            source TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized: " + DB_FILE)

# =============================================================================
# MQTT CALLBACKS
# =============================================================================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker: " + MQTT_BROKER)
        client.subscribe(f"{TOPIC_NS}/sensor/state")
        client.subscribe(f"{TOPIC_NS}/device/state")
        client.subscribe(f"{TOPIC_NS}/sys/online")
        client.subscribe(f"{TOPIC_NS}/device/cmd")
        print(f"📡 Subscribed to: {TOPIC_NS}/*")
    else:
        print(f"❌ Connection failed with code: {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    
    try:
        data = json.loads(payload)
        
        if topic.endswith("/sensor/state"):
            save_sensor_data(data)
        elif topic.endswith("/device/state"):
            save_device_state(data)
        elif topic.endswith("/sys/online"):
            save_online_status(data)
        elif topic.endswith("/device/cmd"):
            save_command(data)
            
    except json.JSONDecodeError:
        print(f"⚠️  Invalid JSON from {topic}: {payload}")
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def save_sensor_data(data):
    # (Hàm này giữ nguyên)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    temperature = data.get('temperature')
    humidity = data.get('humidity')
    rain_analog = data.get('rain_analog')
    rain_digital = data.get('rain_digital')
    is_raining = data.get('is_raining')
    rssi = data.get('rssi')
    device_timestamp = data.get('timestamp')
    
    cursor.execute("""
        INSERT INTO sensor_data (device_timestamp, temperature, humidity, rain_analog, rain_digital, is_raining, rssi)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (device_timestamp, temperature, humidity, rain_analog, rain_digital, is_raining, rssi))
    
    conn.commit()
    conn.close()
    
    rain_status = "Raining" if is_raining else "Dry"
    print(f"🌡️  Sensor: {temperature}°C, {humidity}%, {rain_status} (A:{rain_analog}) - Saved to DB")

def save_device_state(data):
    """Lưu trạng thái thiết bị vào database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    light = data.get('light')       # <<< SỬA: Đổi lại thành 'light'
    pump = data.get('pump')
    pumpSpeed = data.get('pumpSpeed')
    rssi = data.get('rssi')
    device_timestamp = data.get('timestamp')
    
    cursor.execute("""
        INSERT INTO device_state (device_timestamp, light, pump, pumpSpeed, rssi)
        VALUES (?, ?, ?, ?, ?)
    """, (device_timestamp, light, pump, pumpSpeed, rssi)) # <<< SỬA
    
    conn.commit()
    conn.close()
    
    print(f"📊 State: Light={light}, Pump={pump} ({pumpSpeed}%) - Saved to DB") # <<< SỬA

def save_online_status(data):
    # (Hàm này giữ nguyên)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    online = data.get('online')
    device_id = data.get('deviceId')
    firmware = data.get('firmware')
    rssi = data.get('rssi')
    device_timestamp = data.get('timestamp')
    
    cursor.execute("""
        INSERT INTO device_online (device_timestamp, online, device_id, firmware, rssi)
        VALUES (?, ?, ?, ?, ?)
    """, (device_timestamp, online, device_id, firmware, rssi))
    
    conn.commit()
    conn.close()
    
    status = "🟢 Online" if online else "🔴 Offline"
    print(f"{status}: {device_id} - Saved to DB")

def save_command(data):
    """Lưu lệnh điều khiển vào database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if 'light' in data:               # <<< SỬA: Đổi lại thành 'light'
        cmd_type = 'light'
        cmd_value = data['light']
    elif 'pump' in data:
        cmd_type = 'pump'
        cmd_value = data['pump']
    elif 'pumpSpeed' in data:
        cmd_type = 'pumpSpeed'
        cmd_value = str(data['pumpSpeed'])
    else:
        cmd_type = 'unknown'
        cmd_value = json.dumps(data)
    
    cursor.execute("""
        INSERT INTO commands (command_type, command_value, source)
        VALUES (?, ?, ?)
    """, (cmd_type, cmd_value, 'mqtt'))
    
    conn.commit()
    conn.close()
    
    print(f"📥 Command: {cmd_type}={cmd_value} - Saved to DB")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("╔════════════════════════════════════════════╗")
    print("║   MQTT to Database Logger (Garden Version) ║")
    print("╚════════════════════════════════════════════╝")
    print(f"📡 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"💾 Database: {DB_FILE}")
    print(f"📊 Topic Namespace: {TOPIC_NS}")
    print("────────────────────────────────────────────")
    
    init_database()
    
    client = mqtt.Client(client_id="mqtt_logger_" + str(int(time.time())), protocol=mqtt.MQTTv311)
    # <<< SỬA: Thêm protocol=mqtt.MQTTv311 để hết lỗi DeprecationWarning
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        if MQTT_USERNAME:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        print("\n✅ Logger started! Press Ctrl+C to stop")
        print("────────────────────────────────────────────\n")
        
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Logger stopped by user")
        client.disconnect()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()