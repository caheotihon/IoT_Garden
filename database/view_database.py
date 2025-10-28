"""
Database Viewer - Xem dữ liệu từ SQLite database
ĐÃ ĐƯỢC CẬP NHẬT CHO "demo/garden" (Dùng "light" và "pump")
"""

import sqlite3
from datetime import datetime, timedelta
import sys

DB_FILE = "iot_garden_data.db" 

def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def view_sensor_data(limit=20):
    # (Hàm này giữ nguyên)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, temperature, humidity, rain_analog, is_raining, rssi
        FROM sensor_data
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print_header(f"🌡️  SENSOR DATA (Latest {limit} records)")
    print(f"{'Time':<20} {'Temp (°C)':<12} {'Humidity (%)':<15} {'Rain Analog':<15} {'Is Raining?':<15} {'RSSI (dBm)':<12}")
    print("-"*90)
    
    for row in rows:
        timestamp, temp, hum, rain_a, is_rain, rssi = row
        rssi_str = str(rssi) if rssi is not None else "N/A"
        temp_str = f"{temp:.1f}" if temp is not None else "N/A"
        hum_str = f"{hum:.1f}" if hum is not None else "N/A"
        rain_a_str = str(rain_a) if rain_a is not None else "N/A"
        is_rain_str = "YES" if is_rain else "NO"
        
        print(f"{timestamp:<20} {temp_str:<12} {hum_str:<15} {rain_a_str:<15} {is_rain_str:<15} {rssi_str:<12}")
    
    print(f"\nTotal records: {len(rows)}")

def view_device_state(limit=20):
    """Xem trạng thái thiết bị"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # <<< SỬA: Đổi lại thành 'light'
    cursor.execute("""
        SELECT timestamp, light, pump, pumpSpeed, rssi
        FROM device_state
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print_header(f"💡 DEVICE STATE (Latest {limit} records)")
    # <<< SỬA: Cập nhật tiêu đề
    print(f"{'Time':<20} {'Light':<10} {'Pump':<10} {'Pump Speed (%)':<18} {'RSSI (dBm)':<12}")
    print("-"*80)
    
    for row in rows:
        # <<< SỬA: Đổi lại thành 'light'
        timestamp, light, pump, pumpSpeed, rssi = row
        rssi_str = str(rssi) if rssi is not None else "N/A"
        pumpSpeed_str = str(pumpSpeed) if pumpSpeed is not None else "N/A"
        light_str = str(light) if light is not None else "N/A" # Xử lý lỗi None
        pump_str = str(pump) if pump is not None else "N/A"   # Xử lý lỗi None

        # <<< SỬA: Cập nhật in
        print(f"{timestamp:<20} {light_str:<10} {pump_str:<10} {pumpSpeed_str:<18} {rssi_str:<12}")
    
    print(f"\nTotal records: {len(rows)}")

def view_online_status(limit=10):
    # (Hàm này giữ nguyên)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, online, device_id, firmware, rssi
        FROM device_online
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print_header(f"🟢 ONLINE STATUS (Latest {limit} records)")
    print(f"{'Time':<20} {'Status':<10} {'Device ID':<20} {'Firmware':<20} {'RSSI':<10}")
    print("-"*80)
    
    for row in rows:
        timestamp, online, device_id, firmware, rssi = row
        status = "🟢 Online" if online else "🔴 Offline"
        device_id = device_id or "N/A"
        firmware = firmware or "N/A"
        rssi_str = str(rssi) if rssi is not None else "N/A"
        print(f"{timestamp:<20} {status:<10} {device_id:<20} {firmware:<20} {rssi_str:<10}")
    
    print(f"\nTotal records: {len(rows)}")

def view_commands(limit=20):
    # (Hàm này giữ nguyên)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, command_type, command_value, source
        FROM commands
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print_header(f"📥 COMMAND HISTORY (Latest {limit} records)")
    print(f"{'Time':<20} {'Type':<15} {'Value':<15} {'Source':<10}")
    print("-"*80)
    
    for row in rows:
        timestamp, cmd_type, cmd_value, source = row
        print(f"{timestamp:<20} {cmd_type:<15} {cmd_value:<15} {source:<10}")
    
    print(f"\nTotal records: {len(rows)}")

def view_statistics():
    # (Hàm này giữ nguyên)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print_header("📊 DATABASE STATISTICS")
    
    cursor.execute("SELECT COUNT(*) FROM sensor_data")
    sensor_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM device_state")
    state_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM device_online")
    online_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM commands")
    cmd_count = cursor.fetchone()[0]
    
    print(f"📊 Total Records:")
    print(f"  • Sensor Data:    {sensor_count:>8}")
    print(f"  • Device State:   {state_count:>8}")
    print(f"  • Online Status:  {online_count:>8}")
    print(f"  • Commands:       {cmd_count:>8}")
    
    cursor.execute("""
        SELECT AVG(temperature), AVG(humidity), MIN(temperature), MAX(temperature)
        FROM sensor_data
        WHERE timestamp > datetime('now', '-24 hours')
    """)
    row = cursor.fetchone()
    if row and row[0] is not None:
        avg_temp, avg_hum, min_temp, max_temp = row
        print(f"\n🌡️  Last 24 Hours:")
        print(f"  • Avg Temperature: {avg_temp:>6.1f}°C")
        print(f"  • Min Temperature: {min_temp:>6.1f}°C")
        print(f"  • Max Temperature: {max_temp:>6.1f}°C")
        print(f"  • Avg Humidity:    {avg_hum:>6.1f}%")
        
    cursor.execute("""
        SELECT COUNT(*) 
        FROM sensor_data
        WHERE timestamp > datetime('now', '-24 hours') AND is_raining = 1
    """)
    row = cursor.fetchone()
    if row and row[0] is not None:
        rain_events = row[0]
        print(f"  • Rain Events:     {rain_events} records")
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN online = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as uptime_pct
        FROM device_online
        WHERE timestamp > datetime('now', '-24 hours')
    """)
    row = cursor.fetchone()
    if row and row[0] is not None:
        uptime = row[0]
        print(f"\n🟢 Device Uptime (24h): {uptime:.1f}%")
    
    conn.close()

def interactive_menu():
    # (Hàm này giữ nguyên)
    while True:
        print("\n" + "="*80)
        print("  📊 IoT DATABASE VIEWER (Garden Version)")
        print("="*80)
        print("\n[1] View Sensor Data")
        print("[2] View Device State")
        print("[3] View Online Status")
        print("[4] View Command History")
        print("[5] View Statistics")
        print("[6] View All")
        print("[0] Exit")
        
        choice = input("\nSelect option (0-6): ").strip()
        
        if choice == '1':
            limit = input("How many records? (default 20): ").strip() or "20"
            view_sensor_data(int(limit))
        elif choice == '2':
            limit = input("How many records? (default 20): ").strip() or "20"
            view_device_state(int(limit))
        elif choice == '3':
            limit = input("How many records? (default 10): ").strip() or "10"
            view_online_status(int(limit))
        elif choice == '4':
            limit = input("How many records? (default 20): ").strip() or "20"
            view_commands(int(limit))
        elif choice == '5':
            view_statistics()
        elif choice == '6':
            view_statistics()
            view_sensor_data(10)
            view_device_state(10)
            view_online_status(5)
            view_commands(10)
        elif choice == '0':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option!")

def main():
    # (Hàm này giữ nguyên)
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.close()
    except Exception as e:
        print(f"❌ Cannot open database: {e}")
        print(f"Make sure '{DB_FILE}' exists. Run mqtt_logger.py first!")
        return
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == 'sensor':
            view_sensor_data()
        elif cmd == 'state':
            view_device_state()
        elif cmd == 'online':
            view_online_status()
        elif cmd == 'commands':
            view_commands()
        elif cmd == 'stats':
            view_statistics()
        elif cmd == 'all':
            view_statistics()
            view_sensor_data(10)
            view_device_state(10)
            view_online_status(5)
            view_commands(10)
        else:
            print("Usage: python view_database.py [sensor|state|online|commands|stats|all]")
    else:
        interactive_menu()

if __name__ == "__main__":
    main()