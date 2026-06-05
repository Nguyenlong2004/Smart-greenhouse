/*
 * GREENHOUSE - ESP32 HOÀN CHỈNH
 * WiFi + MQTT + Web Server + Log thời gian
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <WebServer.h>

// ── WIFI ──────────────────────────────
const char* WIFI_SSID = "WIFI GIANG VIEN";      
const char* WIFI_PASS = "GV#dainam@5577";  

// ── MQTT ──────────────────────────────
const char* MQTT_SERVER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;
const char* TOPIC_DATA  = "greenhouse/sensors";
const char* TOPIC_FAN   = "greenhouse/control/fan";
const char* TOPIC_PUMP  = "greenhouse/control/pump";
const char* TOPIC_LED   = "greenhouse/control/led";

// ── SERIAL2 ───────────────────────────
#define UNO_RX 16
#define UNO_TX 17

// ── KHỞI TẠO ─────────────────────────
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
WebServer    server(80);

// Dữ liệu cảm biến
float temp=0, hum=0;
int   light=0, soil=0;
bool  fan=false, pump=false, led=false;

// Log thời gian hoạt động
struct LogEntry {
    String time;
    String device;
    String action;
    String reason;
};
LogEntry logs[20];
int logCount = 0;

// Thời gian chạy thiết bị (giây)
unsigned long fanRunTime  = 0;
unsigned long pumpRunTime = 0;
unsigned long ledRunTime  = 0;
unsigned long lastTick    = 0;

// Trạng thái trước để detect thay đổi
bool prevFan=false, prevPump=false, prevLed=false;

// Đếm giờ phút giây từ khi bật
String getTime() {
    unsigned long ms = millis();
    int h = ms / 3600000;
    int m = (ms % 3600000) / 60000;
    int s = (ms % 60000) / 1000;
    char buf[12];
    sprintf(buf, "%02d:%02d:%02d", h, m, s);
    return String(buf);
}

void addLog(String device, String action, String reason) {
    if (logCount >= 20) {
        // Xóa log cũ nhất
        for (int i = 0; i < 19; i++) logs[i] = logs[i+1];
        logCount = 19;
    }
    logs[logCount].time   = getTime();
    logs[logCount].device = device;
    logs[logCount].action = action;
    logs[logCount].reason = reason;
    logCount++;
    Serial.println("[LOG] " + device + " " + action + " - " + reason);
}

// ── SETUP ─────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial2.begin(9600, SERIAL_8N1, UNO_RX, UNO_TX);

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Ket noi WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500); Serial.print(".");
    }
    Serial.println("\nWiFi OK! IP: " + WiFi.localIP().toString());

    mqtt.setServer(MQTT_SERVER, MQTT_PORT);
    mqtt.setCallback(mqttCallback);
    connectMQTT();

    setupWeb();
    server.begin();
    Serial.println("Web: http://" + WiFi.localIP().toString());
    lastTick = millis();
}

// ── LOOP ──────────────────────────────
void loop() {
    if (!mqtt.connected()) connectMQTT();
    mqtt.loop();
    server.handleClient();

    // Đếm thời gian chạy mỗi giây
    if (millis() - lastTick >= 1000) {
        lastTick = millis();
        if (fan)  fanRunTime++;
        if (pump) pumpRunTime++;
        if (led)  ledRunTime++;
    }

    // Nhận data từ Uno
    if (Serial2.available()) {
        String json = Serial2.readStringUntil('\n');
        json.trim();
        if (json.startsWith("{")) xuLyData(json);
    }
}

// ── XỬ LÝ DATA TỪ UNO ─────────────────
void xuLyData(String jsonStr) {
    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, jsonStr)) return;

    temp  = doc["t"]    | 0.0f;
    hum   = doc["h"]    | 0.0f;
    light = doc["l"]    | 0;
    soil  = doc["soil"] | 0;
    fan   = doc["fan"]  | 0;
    pump  = doc["pump"] | 0;
    led   = doc["led"]  | 0;

    // Ghi log khi trạng thái thay đổi
    if (fan != prevFan) {
        addLog("Quat", fan ? "BAT" : "TAT",
               fan ? "Nhiet do > 30C" : "Nhiet do thuong");
        prevFan = fan;
    }
    if (pump != prevPump) {
        addLog("Bom", pump ? "BAT" : "TAT",
               pump ? "Do am thap" : "Du am");
        prevPump = pump;
    }
    if (led != prevLed) {
        addLog("Den", led ? "BAT" : "TAT",
               led ? "Troi toi" : "Du sang");
        prevLed = led;
    }

    Serial.printf("[UNO] T=%.1f H=%.1f L=%d S=%d\n",
                  temp, hum, light, soil);
    mqtt.publish(TOPIC_DATA, jsonStr.c_str());
}

// ── MQTT ──────────────────────────────
void connectMQTT() {
    while (!mqtt.connected()) {
        String id = "ESP32-GH-" + String(random(9999));
        if (mqtt.connect(id.c_str())) {
            Serial.println("MQTT OK!");
            mqtt.subscribe(TOPIC_FAN);
            mqtt.subscribe(TOPIC_PUMP);
            mqtt.subscribe(TOPIC_LED);
        } else delay(3000);
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int len) {
    String val = "";
    for (int i = 0; i < len; i++) val += (char)payload[i];
    String t = String(topic);
    if      (t == TOPIC_FAN)  { Serial2.println("FAN:"  + val); addLog("Quat", val=="1"?"BAT":"TAT", "Web/App"); }
    else if (t == TOPIC_PUMP) { Serial2.println("PUMP:" + val); addLog("Bom",  val=="1"?"BAT":"TAT", "Web/App"); }
    else if (t == TOPIC_LED)  { Serial2.println("LED:"  + val); addLog("Den",  val=="1"?"BAT":"TAT", "Web/App"); }
}

// Chuyển giây → giờ:phút:giây
String formatRunTime(unsigned long seconds) {
    int h = seconds / 3600;
    int m = (seconds % 3600) / 60;
    int s = seconds % 60;
    char buf[12];
    sprintf(buf, "%02d:%02d:%02d", h, m, s);
    return String(buf);
}

// ── WEB SERVER ────────────────────────
void setupWeb() {

    // Trang chủ dashboard
    server.on("/", []() {
        String html = R"(
<!DOCTYPE html><html lang='vi'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Nha Kinh Monitor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:sans-serif;background:#0a150a;color:#e0f0e0;padding:16px}
h1{color:#4ade80;text-align:center;margin:16px 0;font-size:22px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:500px;margin:0 auto 20px}
.card{background:#1a2e1a;border-radius:12px;padding:16px;text-align:center;border:1px solid #2d4a2d}
.val{font-size:30px;font-weight:700;color:#4ade80;margin:8px 0}
.lbl{font-size:12px;color:#6b8f6b}
.sub{font-size:11px;color:#4ade80;margin-top:4px}
.wrap{max-width:500px;margin:0 auto}
h3{color:#fbbf24;margin:16px 0 10px;text-align:center}
.btn{width:100%;padding:13px;margin:6px 0;border:none;border-radius:10px;
     font-size:15px;cursor:pointer;font-weight:700;text-decoration:none;
     display:block;text-align:center;transition:0.2s}
.on{background:#4ade80;color:#000}
.off{background:#1a2e1a;color:#6b8f6b;border:1px solid #2d4a2d}
.log-table{width:100%;border-collapse:collapse;margin-top:10px;font-size:12px}
.log-table th{background:#1a2e1a;color:#6b8f6b;padding:8px;text-align:left;border-bottom:1px solid #2d4a2d}
.log-table td{padding:8px;border-bottom:1px solid #1a2e1a;color:#e0f0e0}
.log-table tr:hover td{background:#1a2e1a}
.badge-on{color:#4ade80;font-weight:700}
.badge-off{color:#6b8f6b}
.runtime{background:#1a2e1a;border-radius:10px;padding:12px;margin:6px 0;
          display:flex;justify-content:space-between;align-items:center;
          border:1px solid #2d4a2d}
.runtime-lbl{color:#6b8f6b;font-size:13px}
.runtime-val{color:#4ade80;font-weight:700;font-size:15px}
</style>
</head>
<body>
<h1>🌿 Nha Kinh Monitor</h1>

<div class='grid' id='sensors'>
  <div class='card'>
    <div class='lbl'>🌡️ Nhiet do</div>
    <div class='val' id='temp'>--°C</div>
    <div class='sub' id='temp-status'></div>
  </div>
  <div class='card'>
    <div class='lbl'>💧 Do am KK</div>
    <div class='val' id='hum'>--%</div>
    <div class='sub' id='hum-status'></div>
  </div>
  <div class='card'>
    <div class='lbl'>☀️ Anh sang</div>
    <div class='val' id='light'>--</div>
  </div>
  <div class='card'>
    <div class='lbl'>🌱 Am dat</div>
    <div class='val' id='soil'>--</div>
  </div>
</div>

<div class='wrap'>
  <h3>⏱️ Thoi gian hoat dong</h3>
  <div class='runtime'>
    <span class='runtime-lbl'>🌀 Quat</span>
    <span class='runtime-val' id='rt-fan'>00:00:00</span>
  </div>
  <div class='runtime'>
    <span class='runtime-lbl'>💧 Bom</span>
    <span class='runtime-val' id='rt-pump'>00:00:00</span>
  </div>
  <div class='runtime'>
    <span class='runtime-lbl'>💡 Den</span>
    <span class='runtime-val' id='rt-led'>00:00:00</span>
  </div>

  <h3>🎛️ Dieu khien thiet bi</h3>
  <div id='btn-fan'></div>
  <div id='btn-pump'></div>
  <div id='btn-led'></div>

  <h3>📋 Nhat ky hoat dong</h3>
  <table class='log-table'>
    <thead><tr><th>Gio</th><th>Thiet bi</th><th>Trang thai</th><th>Ly do</th></tr></thead>
    <tbody id='log-body'></tbody>
  </table>
</div>

<script>
function fetchData() {
    fetch('/api').then(r=>r.json()).then(d => {
        document.getElementById('temp').textContent  = d.temp.toFixed(1)+'°C';
        document.getElementById('hum').textContent   = d.hum.toFixed(0)+'%';
        document.getElementById('light').textContent = d.light;
        document.getElementById('soil').textContent  = d.soil;

        document.getElementById('temp-status').textContent =
            d.temp > 30 ? '⚠ Vuot nguong!' : '✓ Binh thuong';
        document.getElementById('hum-status').textContent =
            d.hum < 50 ? '⚠ Thap!' : '✓ Binh thuong';

        document.getElementById('rt-fan').textContent  = d.fanRunTime;
        document.getElementById('rt-pump').textContent = d.pumpRunTime;
        document.getElementById('rt-led').textContent  = d.ledRunTime;

        document.getElementById('btn-fan').innerHTML =
            `<a href='/ctrl?d=fan&v=${d.fan?0:1}' class='btn ${d.fan?"on":"off"}'>
             🌀 QUAT: ${d.fan?"BAT":"TAT"}</a>`;
        document.getElementById('btn-pump').innerHTML =
            `<a href='/ctrl?d=pump&v=${d.pump?0:1}' class='btn ${d.pump?"on":"off"}'>
             💧 BOM: ${d.pump?"BAT":"TAT"}</a>`;
        document.getElementById('btn-led').innerHTML =
            `<a href='/ctrl?d=led&v=${d.led?0:1}' class='btn ${d.led?"on":"off"}'>
             💡 DEN: ${d.led?"BAT":"TAT"}</a>`;

        // Log table
        let html = '';
        d.logs.forEach(l => {
            html += `<tr>
                <td>${l.time}</td>
                <td>${l.device}</td>
                <td class='${l.action=="BAT"?"badge-on":"badge-off"}'>${l.action}</td>
                <td style='color:#6b8f6b'>${l.reason}</td>
            </tr>`;
        });
        document.getElementById('log-body').innerHTML = html;
    }).catch(()=>{});
}
setInterval(fetchData, 3000);
fetchData();
</script>
</body></html>
)";
        server.send(200, "text/html", html);
    });

    // API JSON
    server.on("/api", []() {
        String logsJson = "[";
        for (int i = logCount-1; i >= 0; i--) {
            if (i < logCount-1) logsJson += ",";
            logsJson += "{\"time\":\"" + logs[i].time + "\"," +
                       "\"device\":\"" + logs[i].device + "\"," +
                       "\"action\":\"" + logs[i].action + "\"," +
                       "\"reason\":\"" + logs[i].reason + "\"}";
        }
        logsJson += "]";

        String json = "{";
        json += "\"temp\":"       + String(temp,1)  + ",";
        json += "\"hum\":"        + String(hum,0)   + ",";
        json += "\"light\":"      + String(light)   + ",";
        json += "\"soil\":"       + String(soil)    + ",";
        json += "\"fan\":"        + String(fan?1:0)    + ",";
        json += "\"pump\":"       + String(pump?1:0)   + ",";
        json += "\"led\":"        + String(led?1:0)    + ",";
        json += "\"fanRunTime\":\"" + formatRunTime(fanRunTime)  + "\",";
        json += "\"pumpRunTime\":\"" + formatRunTime(pumpRunTime) + "\",";
        json += "\"ledRunTime\":\"" + formatRunTime(ledRunTime)  + "\",";
        json += "\"logs\":"       + logsJson;
        json += "}";
        server.send(200, "application/json", json);
    });

    // Điều khiển
    server.on("/ctrl", []() {
        String d = server.arg("d");
        String v = server.arg("v");
        if      (d=="fan")  { fan  =(v=="1"); Serial2.println("FAN:"  +v); addLog("Quat", v=="1"?"BAT":"TAT","Web"); }
        else if (d=="pump") { pump =(v=="1"); Serial2.println("PUMP:" +v); addLog("Bom",  v=="1"?"BAT":"TAT","Web"); }
        else if (d=="led")  { led  =(v=="1"); Serial2.println("LED:"  +v); addLog("Den",  v=="1"?"BAT":"TAT","Web"); }
        server.sendHeader("Location", "/");
        server.send(302);
    });
}