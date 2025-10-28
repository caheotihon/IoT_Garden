/*
 * ESP32-S3 IoT Garden Demo Firmware
 *
 * Hardware (Dựa trên sơ đồ nối dây mới):
 * - ESP32-S3
 * - DHT22 Temperature & Humidity Sensor (GPIO 4) 
 * - External LED for Light control (GPIO 10) 
 * - L298N Motor Driver for Pump control: 
 * - IN1: GPIO 5
 * - IN2: GPIO 6
 * - ENA (PWM): GPIO 9
 * - Rain Sensor Module: 
 * - DO: GPIO 15
 * - AO: GPIO 16
 *
 * Features:
 * - WiFi connection with auto-reconnect
 * - MQTT client
 * - Real DHT22 sensor readings
 * - Real Rain sensor readings (Digital & Analog)
 * - Device control via MQTT commands (Light & Pump)
 * - PWM pump speed control
 * - Retained device state messages for UI synchronization
 *
 * MQTT Topics (Namespace: demo/garden):
 * - Publish sensor data: demo/garden/sensor/state
 * - Publish device state: demo/garden/device/state (retained)
 * - Publish online status: demo/garden/sys/online (retained)
 * - Subscribe commands: demo/garden/device/cmd
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// =============================================================================
// CONFIGURATION
// =============================================================================

// WiFi Configuration
const char *WIFI_SSID = "Ca Phe Muoi  01 - Binh Duong"; // Tên WiFi của bạn
const char *WIFI_PASSWORD = "0932155101"; // Mật khẩu WiFi

// MQTT Broker Configuration
const char *MQTT_HOST = "192.168.1.7"; // IP của máy tính (hoặc MQTT broker)
const int MQTT_PORT = 1883;
const char *MQTT_USERNAME = ""; // Bỏ trống nếu không dùng
const char *MQTT_PASSWORD = ""; // Bỏ trống nếu không dùng

// Device Configuration
const char *DEVICE_ID = "esp32s3_garden_real"; // ID thiết bị mới
const char *FIRMWARE_VERSION = "s3-hw-1.0.0"; // Phiên bản firmware mới
const char *TOPIC_NS = "demo/garden"; // Giữ nguyên namespace

// GPIO Pin Configuration for ESP32-S3 (THEO SƠ ĐỒ MỚI)
#define DHT_PIN 4      //  Chân DATA của DHT22
#define DHT_TYPE DHT22 //  Đổi sang DHT22

#define LED_PIN 20 //  Chân điều khiển LED (Anode)

// L298N Motor Driver pins (Bơm)
#define PUMP_IN1 5  //  L298N IN1
#define PUMP_IN2 6  //  L298N IN2
#define PUMP_ENA 9  //  L298N ENA (PWM)

// Rain Sensor pins
#define RAIN_DO_PIN 15 //  Chân Digital Out
#define RAIN_AO_PIN 16 //  Chân Analog Out

// PWM Configuration for Pump
#define PWM_FREQ 5000 // 5 KHz
#define PWM_CHANNEL 0
#define PWM_RESOLUTION 8 // 8-bit (0-255)

// Timing Configuration
const unsigned long SENSOR_PUBLISH_INTERVAL = 3000; // 3 giây
const unsigned long HEARTBEAT_INTERVAL = 15000;     // 15 giây
const unsigned long WIFI_RECONNECT_INTERVAL = 5000; // 5 giây
const unsigned long MQTT_RECONNECT_INTERVAL = 5000; // 5 giây

// =============================================================================
// GLOBAL VARIABLES
// =============================================================================

WiFiClient espClient;
PubSubClient mqttClient(espClient);
DHT dht(DHT_PIN, DHT_TYPE);

// Device state
bool lightState = false;
bool pumpState = false;  // Đổi từ fanState
int pumpSpeed = 255; // Đổi từ fanSpeed (PWM 0-255)

// Timing variables
unsigned long lastSensorPublish = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastWifiCheck = 0;

// MQTT Topics
String topicSensorState;
String topicDeviceState;
String topicDeviceCmd;
String topicSysOnline;

// =============================================================================
// FUNCTION DECLARATIONS
// =============================================================================

void initGPIO();
void initTopics();
void initWiFi();
void initMQTT();
void reconnectWiFi();
void reconnectMQTT();
void mqttCallback(char *topic, byte *payload, unsigned int length);
void handleCommand(JsonDocument &doc);
void publishSensorData();
void publishDeviceState();
void publishOnlineStatus(bool online);
void setLight(bool state);
void setPump(bool state); // Đổi từ setFan
void setPumpSpeed(int speed); // Đổi từ setFanSpeed

// =============================================================================
// SETUP FUNCTION
// =============================================================================

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n╔════════════════════════════════════════════╗");
    Serial.println("║    ESP32-S3 IoT Garden Demo (Real HW)    ║");
    Serial.println("╚════════════════════════════════════════════╝");
    Serial.printf("🆔 Device ID: %s\n", DEVICE_ID);
    Serial.printf("📦 Firmware: %s\n", FIRMWARE_VERSION);
    Serial.printf("📡 Topic Namespace: %s\n", TOPIC_NS);
    Serial.printf("🌡️  DHT22 Sensor: GPIO%d\n", DHT_PIN);
    Serial.printf("💡 LED: GPIO%d\n", LED_PIN);
    Serial.printf("💧 Pump (L298N): IN1=GPIO%d, IN2=GPIO%d, ENA=GPIO%d\n", PUMP_IN1, PUMP_IN2, PUMP_ENA);
    Serial.printf("🌧️  Rain Sensor: DO=GPIO%d, AO=GPIO%d\n", RAIN_DO_PIN, RAIN_AO_PIN);
    Serial.println("────────────────────────────────────────────");

    // Initialize GPIO pins
    initGPIO();

    // Initialize DHT sensor
    dht.begin();
    Serial.println("✅ DHT22 sensor initialized");

    // Initialize MQTT topics
    initTopics();

    // Initialize WiFi
    initWiFi();

    // Initialize MQTT
    initMQTT();

    Serial.println("✅ Setup complete!");
    Serial.println("────────────────────────────────────────────\n");
}

// =============================================================================
// MAIN LOOP
// =============================================================================

void loop()
{
    unsigned long currentMillis = millis();

    // Check WiFi connection
    if (currentMillis - lastWifiCheck >= WIFI_RECONNECT_INTERVAL)
    {
        lastWifiCheck = currentMillis;
        if (WiFi.status() != WL_CONNECTED)
        {
            Serial.println("⚠️  WiFi disconnected, reconnecting...");
            reconnectWiFi();
        }
    }

    // Check MQTT connection
    if (!mqttClient.connected())
    {
        reconnectMQTT();
    }
    mqttClient.loop();

    // Publish sensor data periodically
    if (currentMillis - lastSensorPublish >= SENSOR_PUBLISH_INTERVAL)
    {
        lastSensorPublish = currentMillis;
        publishSensorData();
    }

    // Publish heartbeat (device state + online status)
    if (currentMillis - lastHeartbeat >= HEARTBEAT_INTERVAL)
    {
        lastHeartbeat = currentMillis;
        publishDeviceState();
        publishOnlineStatus(true);
    }
}

// =============================================================================
// GPIO INITIALIZATION
// =============================================================================

void initGPIO()
{
    // LED pin
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW); // Tắt LED (Active-HIGH)

    // Pump (motor) driver pins
    pinMode(PUMP_IN1, OUTPUT);
    pinMode(PUMP_IN2, OUTPUT);
    pinMode(PUMP_ENA, OUTPUT);

    // Setup PWM for pump speed control
    ledcAttach(PUMP_ENA, PWM_FREQ, PWM_RESOLUTION);

    // Rain sensor pins
    pinMode(RAIN_DO_PIN, INPUT_PULLUP); // Dùng INPUT_PULLUP cho digital an toàn hơn
    pinMode(RAIN_AO_PIN, INPUT);

    // Initial state - everything OFF
    setLight(false);
    setPump(false);

    Serial.println("✅ GPIO pins initialized");
}

// =============================================================================
// MQTT TOPICS INITIALIZATION
// =============================================================================

void initTopics()
{
    topicSensorState = String(TOPIC_NS) + "/sensor/state";
    topicDeviceState = String(TOPIC_NS) + "/device/state";
    topicDeviceCmd = String(TOPIC_NS) + "/device/cmd";
    topicSysOnline = String(TOPIC_NS) + "/sys/online";

    Serial.println("✅ MQTT topics configured:");
    Serial.printf("   📊 Sensor: %s\n", topicSensorState.c_str());
    Serial.printf("   📡 State: %s\n", topicDeviceState.c_str());
    Serial.printf("   📥 Command: %s\n", topicDeviceCmd.c_str());
    Serial.printf("   🟢 Online: %s\n", topicSysOnline.c_str());
}

// =============================================================================
// WIFI FUNCTIONS
// =============================================================================

void initWiFi()
{
    Serial.printf("🔌 Connecting to WiFi: %s\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20)
    {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println("\n✅ WiFi connected!");
        Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("📶 RSSI: %d dBm\n", WiFi.RSSI());
    }
    else
    {
        Serial.println("\n❌ WiFi connection failed!");
    }
}

void reconnectWiFi()
{
    WiFi.disconnect();
    delay(100);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 10)
    {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println("\n✅ WiFi reconnected!");
    }
}

// =============================================================================
// MQTT FUNCTIONS
// =============================================================================

void initMQTT()
{
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setKeepAlive(60);
    mqttClient.setSocketTimeout(10);

    Serial.printf("✅ MQTT configured: %s:%d\n", MQTT_HOST, MQTT_PORT);
}

void reconnectMQTT()
{
    static unsigned long lastAttempt = 0;
    unsigned long currentMillis = millis();

    if (currentMillis - lastAttempt < MQTT_RECONNECT_INTERVAL)
    {
        return;
    }
    lastAttempt = currentMillis;

    if (WiFi.status() != WL_CONNECTED)
    {
        return;
    }

    Serial.printf("🔄 Connecting to MQTT broker: %s:%d\n", MQTT_HOST, MQTT_PORT);

    String clientId = String(DEVICE_ID) + "_" + String(random(0xffff), HEX);

    bool connected = false;
    if (strlen(MQTT_USERNAME) > 0)
    {
        connected = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
    }
    else
    {
        connected = mqttClient.connect(clientId.c_str());
    }

    if (connected)
    {
        Serial.println("✅ MQTT connected!");

        // Subscribe to command topic
        mqttClient.subscribe(topicDeviceCmd.c_str());
        Serial.printf("📥 Subscribed to: %s\n", topicDeviceCmd.c_str());

        // Publish online status and initial device state
        publishOnlineStatus(true);
        publishDeviceState();
    }
    else
    {
        Serial.printf("❌ MQTT connection failed, rc=%d\n", mqttClient.state());
    }
}

void mqttCallback(char *topic, byte *payload, unsigned int length)
{
    // Parse JSON payload
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload, length);

    if (error)
    {
        Serial.printf("❌ JSON parse error: %s\n", error.c_str());
        return;
    }

    // Log received command
    String payloadStr;
    serializeJson(doc, payloadStr);
    Serial.printf("📥 Command received [%s]: %s\n", topic, payloadStr.c_str());

    // Handle command
    handleCommand(doc);
}

void handleCommand(JsonDocument &doc)
{
    bool stateChanged = false;

    // Light control
    if (doc.containsKey("light"))
    {
        String cmd = doc["light"].as<String>();
        if (cmd == "toggle")
        {
            lightState = !lightState;
            setLight(lightState);
            Serial.printf("💡 Light: %s\n", lightState ? "ON" : "OFF");
            stateChanged = true;
        }
        else if (cmd == "on")
        {
            lightState = true;
            setLight(true);
            Serial.println("💡 Light: ON");
            stateChanged = true;
        }
        else if (cmd == "off")
        {
            lightState = false;
            setLight(false);
            Serial.println("💡 Light: OFF");
            stateChanged = true;
        }
    }

    // Pump control (thay cho "fan")
    if (doc.containsKey("pump"))
    {
        String cmd = doc["pump"].as<String>();
        if (cmd == "toggle")
        {
            pumpState = !pumpState;
            setPump(pumpState);
            Serial.printf("💧 Pump: %s\n", pumpState ? "ON" : "OFF");
            stateChanged = true;
        }
        else if (cmd == "on")
        {
            pumpState = true;
            setPump(true);
            Serial.println("💧 Pump: ON");
            stateChanged = true;
        }
        else if (cmd == "off")
        {
            pumpState = false;
            setPump(false);
            Serial.println("💧 Pump: OFF");
            stateChanged = true;
        }
    }

    // Pump speed control (0-100%) (thay cho "fanSpeed")
    if (doc.containsKey("pumpSpeed"))
    {
        int speed = doc["pumpSpeed"].as<int>();
        speed = constrain(speed, 0, 100);
        pumpSpeed = map(speed, 0, 100, 0, 255); // Chuyển % sang PWM
        if (pumpState)
        {
            setPumpSpeed(pumpSpeed);
            Serial.printf("💧 Pump speed: %d%%\n", speed);
        }
        stateChanged = true;
    }

    // Publish updated state if something changed
    if (stateChanged)
    {
        publishDeviceState();
    }
}

// =============================================================================
// DEVICE CONTROL FUNCTIONS
// =============================================================================

void setLight(bool state)
{
    //  LED ngoài nối Anode (cực dài) vào GPIO 10, Cathode (cực ngắn) qua R xuống GND
    // Đây là logic ACTIVE-HIGH (HIGH = ON, LOW = OFF)
    digitalWrite(LED_PIN, state ? HIGH : LOW);
    lightState = state;
}

void setPump(bool state) // Đổi từ setFan
{
    pumpState = state;
    if (state)
    {
        // Quay thuận (Forward direction)
        digitalWrite(PUMP_IN1, HIGH); // 
        digitalWrite(PUMP_IN2, LOW);  // 
        setPumpSpeed(pumpSpeed);
    }
    else
    {
        // Dừng bơm
        digitalWrite(PUMP_IN1, LOW);
        digitalWrite(PUMP_IN2, LOW);
        ledcWrite(PUMP_ENA, 0); // 
    }
}

void setPumpSpeed(int speed) // Đổi từ setFanSpeed
{
    speed = constrain(speed, 0, 255);
    ledcWrite(PUMP_ENA, speed); // 
}

// =============================================================================
// MQTT PUBLISH FUNCTIONS
// =============================================================================

void publishSensorData()
{
    // Đọc DHT22
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    // Kiểm tra DHT
    if (isnan(temperature) || isnan(humidity))
    {
        Serial.println("⚠️  Failed to read from DHT sensor!");
        // Không return, vẫn đọc cảm biến mưa
    }
    
    // Đọc Cảm biến mưa 
    int rainAnalog = analogRead(RAIN_AO_PIN);     // Đọc giá trị Analog (0-4095)
    int rainDigital = digitalRead(RAIN_DO_PIN);   // Đọc giá trị Digital (0 hoặc 1)
    bool isRaining = (rainDigital == 0);          //  0 = có mưa, 1 = khô

    // Lấy WiFi RSSI
    int rssi = WiFi.RSSI();

    // Tạo JSON payload
    JsonDocument doc;
    if (!isnan(temperature)) doc["temperature"] = round(temperature * 10) / 10.0;
    if (!isnan(humidity)) doc["humidity"] = round(humidity * 10) / 10.0;
    
    doc["rain_analog"] = rainAnalog;
    doc["rain_digital"] = rainDigital;
    doc["is_raining"] = isRaining;

    doc["rssi"] = rssi;
    doc["timestamp"] = millis();

    String payload;
    serializeJson(doc, payload);

    // Gửi lên MQTT
    if (mqttClient.publish(topicSensorState.c_str(), payload.c_str()))
    {
        Serial.printf("🌡️  Sensor: %.1f°C, %.1f%% | 🌧️  Rain: %s (A: %d, D: %d)\n",
                      temperature, humidity, isRaining ? "YES" : "NO", rainAnalog, rainDigital);
    }
}

void publishDeviceState()
{
    JsonDocument doc;
    doc["light"] = lightState ? "on" : "off";
    doc["pump"] = pumpState ? "on" : "off"; // Đổi từ "fan"
    doc["pumpSpeed"] = map(pumpSpeed, 0, 255, 0, 100); // Gửi tốc độ dạng %
    doc["rssi"] = WiFi.RSSI();
    doc["timestamp"] = millis();

    String payload;
    serializeJson(doc, payload);

    // Gửi (retained)
    if (mqttClient.publish(topicDeviceState.c_str(), payload.c_str(), true))
    {
        Serial.printf("📊 State: Light=%s, Pump=%s (%d%%)\n",
                      lightState ? "ON" : "OFF",
                      pumpState ? "ON" : "OFF",
                      map(pumpSpeed, 0, 255, 0, 100));
    }
}

void publishOnlineStatus(bool online)
{
    JsonDocument doc;
    doc["online"] = online;
    doc["deviceId"] = DEVICE_ID;
    doc["firmware"] = FIRMWARE_VERSION;
    doc["rssi"] = WiFi.RSSI();
    doc["timestamp"] = millis();

    String payload;
    serializeJson(doc, payload);

    // Gửi (retained)
    mqttClient.publish(topicSysOnline.c_str(), payload.c_str(), true);
    Serial.printf("🟢 Online status: %s\n", online ? "true" : "false");
}