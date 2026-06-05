#include <DHT.h>
#include <SoftwareSerial.h>
#include <Servo.h>

#define PIN_DHT    2
#define PIN_LDR    A1
#define PIN_LED    5
#define RELAY_QUAT 9
#define RELAY_BOM  8
#define PIN_SERVO  12

#define NGUONG_NHIET   30.0
#define NGUONG_MO_CUA  31.0
#define NGUONG_DO_AM   50.0
#define GOS_MO        120    // ← tăng từ 90 lên 120
#define GOS_DONG        0
#define MANUAL_TIME  60000   // 10 giây manual override

SoftwareSerial espSerial(6, 7);
DHT dht(PIN_DHT, DHT11);
Servo servo;

bool quatBat=false, bomBat=false, denBat=false, cuaMo=false;
unsigned long lastSend = 0;

// Timer manual override cho từng thiết bị
unsigned long manualFan  = 0;
unsigned long manualPump = 0;
unsigned long manualLed  = 0;
unsigned long manualDoor = 0;

void setup() {
    Serial.begin(9600);
    espSerial.begin(9600);
    pinMode(PIN_LED,    OUTPUT); digitalWrite(PIN_LED,    LOW);
    pinMode(RELAY_QUAT, OUTPUT); digitalWrite(RELAY_QUAT, LOW);
    pinMode(RELAY_BOM,  OUTPUT); digitalWrite(RELAY_BOM,  LOW);
    pinMode(PIN_LDR,    INPUT);
    servo.attach(PIN_SERVO);
    servo.write(GOS_DONG);
    dht.begin();
    Serial.println("=== NHA KINH KHOI DONG ===");
    delay(3000);
}

void loop() {
    float t      = dht.readTemperature();
    float h      = dht.readHumidity();
    int   ldrDO  = digitalRead(PIN_LDR);
    int   ldrRaw = analogRead(PIN_LDR);

    if (isnan(t) || isnan(h) || t < 1.0) {
        Serial.println("LOI DHT11!");
        delay(2000);
        return;
    }

    unsigned long now = millis();

    // ── ĐIỀU KIỆN AUTO (chỉ khi hết manual override) ──
    if (now > manualFan)  quatBat = (t > NGUONG_NHIET);
    if (now > manualPump) bomBat  = (h < NGUONG_DO_AM);
    if (now > manualLed)  denBat  = (ldrDO == 1);
    if (now > manualDoor) cuaMo   = (t > NGUONG_MO_CUA);

    // ── ĐIỀU KHIỂN ──────────────────
    digitalWrite(RELAY_QUAT, quatBat ? HIGH : LOW);
    digitalWrite(RELAY_BOM,  bomBat  ? HIGH : LOW);
    digitalWrite(PIN_LED,    denBat  ? HIGH : LOW);
    servo.write(cuaMo ? GOS_MO : GOS_DONG);

    // ── IN KẾT QUẢ ──────────────────
    Serial.println("================================");
    Serial.print("Nhiet do  : "); Serial.print(t);
    Serial.print(" C → Quat: "); Serial.print(quatBat ? "BAT" : "TAT");
    if (now < manualFan) Serial.print(" [MANUAL]");
    Serial.print(" | Cua: "); Serial.print(cuaMo ? "MO" : "DONG");
    if (now < manualDoor) Serial.print(" [MANUAL]");
    Serial.println();

    Serial.print("Do am KK  : "); Serial.print(h);
    Serial.print(" % → Bom : "); Serial.print(bomBat ? "BAT" : "TAT");
    if (now < manualPump) Serial.print(" [MANUAL " + String((manualPump-now)/1000) + "s]");
    Serial.println();

    Serial.print("Anh sang  : DO="); Serial.print(ldrDO);
    Serial.print(" → Den : "); Serial.print(denBat ? "BAT" : "TAT");
    if (now < manualLed) Serial.print(" [MANUAL]");
    Serial.println();

    // ── GỬI JSON LÊN ESP32 ──────────
    if (millis() - lastSend >= 5000) {
        lastSend = millis();
        String json = "{\"t\":"    + String(t,1) +
                     ",\"h\":"    + String(h,1) +
                     ",\"l\":"    + String(ldrRaw) +
                     ",\"soil\":0" +
                     ",\"fan\":"  + String(quatBat?1:0) +
                     ",\"pump\":" + String(bomBat?1:0) +
                     ",\"led\":"  + String(denBat?1:0) +
                     ",\"door\":" + String(cuaMo?1:0) + "}";
        espSerial.println(json);
        Serial.println(">>> Gui ESP32: " + json);
    }

    // ── NHẬN LỆNH TỪ ESP32 ──────────
    if (espSerial.available()) {
        String cmd = espSerial.readStringUntil('\n');
        cmd.trim();
        Serial.println("<<< Nhan lenh: " + cmd);

        if (cmd=="FAN:1")  {
            quatBat=true;  digitalWrite(RELAY_QUAT, HIGH);
            manualFan = millis() + MANUAL_TIME;   // Giữ 10s
        }
        else if (cmd=="FAN:0")  {
            quatBat=false; digitalWrite(RELAY_QUAT, LOW);
            manualFan = millis() + MANUAL_TIME;
        }
        else if (cmd=="PUMP:1") {
            bomBat=true;   digitalWrite(RELAY_BOM, HIGH);
            manualPump = millis() + MANUAL_TIME;  // Giữ 10s
        }
        else if (cmd=="PUMP:0") {
            bomBat=false;  digitalWrite(RELAY_BOM, LOW);
            manualPump = millis() + MANUAL_TIME;
        }
        else if (cmd=="LED:1")  {
            denBat=true;   digitalWrite(PIN_LED, HIGH);
            manualLed = millis() + MANUAL_TIME;
        }
        else if (cmd=="LED:0")  {
            denBat=false;  digitalWrite(PIN_LED, LOW);
            manualLed = millis() + MANUAL_TIME;
        }
        else if (cmd=="DOOR:1") {
            cuaMo=true;    servo.write(GOS_MO);
            manualDoor = millis() + MANUAL_TIME;
        }
        else if (cmd=="DOOR:0") {
            cuaMo=false;   servo.write(GOS_DONG);
            manualDoor = millis() + MANUAL_TIME;
        }
    }

    delay(2000);
}