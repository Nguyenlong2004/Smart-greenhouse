# 🌿 GreenHouse Monitor — Hệ Thống Nhà Kính Thông Minh

**Hệ thống giám sát và điều khiển nhà kính thông minh sử dụng IoT, AI và Web Real-time**

*Đồ án tốt nghiệp ngành Công nghệ Thông tin*

---

## 📋 Mục Lục

- [Giới thiệu](#-giới-thiệu)
- [Tính năng](#-tính-năng)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Công nghệ sử dụng](#-công-nghệ-sử-dụng)
- [Yêu cầu phần cứng](#-yêu-cầu-phần-cứng)
- [Cài đặt](#-cài-đặt)
- [Cấu hình](#-cấu-hình)
- [Chạy hệ thống](#-chạy-hệ-thống)
- [Giao diện web](#-giao-diện-web)
- [API Reference](#-api-reference)
- [Sơ đồ kết nối](#-sơ-đồ-kết-nối)

---

## 🌱 Giới Thiệu

GreenHouse Monitor là hệ thống IoT hoàn chỉnh giúp giám sát và điều khiển môi trường nhà kính từ xa theo thời gian thực. Hệ thống tự động điều chỉnh nhiệt độ, độ ẩm và ánh sáng thông qua các thiết bị như quạt làm mát, bơm tưới nước, đèn LED và servo điều khiển cửa thông gió.

Điểm nổi bật của hệ thống là tích hợp **Digital Twin** — bản sao kỹ thuật số của nhà kính thật, cùng với **nhận diện khuôn mặt** và **điều khiển giọng nói** để bảo mật và tiện lợi trong vận hành.

---

## ✨ Tính Năng

### Giám sát thực tế
- Đọc nhiệt độ và độ ẩm không khí từ cảm biến DHT11
- Đo cường độ ánh sáng từ module LDR
- Cập nhật dữ liệu real-time lên web dashboard
- Lưu lịch sử dữ liệu vào SQLite, hiển thị biểu đồ xu hướng

### Điều khiển tự động
- Quạt làm mát tự động bật khi nhiệt độ vượt 30°C
- Bơm tưới nước tự động bật khi độ ẩm dưới 50%
- Đèn LED tự động bật khi trời tối
- Servo mở cửa thông gió tự động khi nhiệt độ vượt 33°C

### Điều khiển thủ công
- Giao diện web toggle bật/tắt từng thiết bị
- Manual override 5 giây trước khi trả về chế độ tự động
- Lịch sử nhật ký hoạt động thiết bị

### Digital Twin
- Mô phỏng 3D nhà kính bằng Canvas 2D animation
- Hiệu ứng quạt quay, giọt nước rơi, đèn chiếu sáng, cửa mở
- Đồng bộ real-time với trạng thái phần cứng thực tế
- Thanh nhiệt độ và độ ẩm trực quan

### Bảo mật & Giọng nói
- Nhận diện khuôn mặt chủ nhân bằng OpenCV + face_recognition
- Chỉ cho phép điều khiển giọng nói sau khi xác thực khuôn mặt
- Hỗ trợ lệnh tiếng Việt: bật/tắt quạt, bơm, đèn, mở/đóng cửa
- Phản hồi âm thanh xác nhận lệnh

### AI Assistant
- Chatbot hỏi đáp về trạng thái nhà kính
- Phân tích dữ liệu cảm biến và đưa ra khuyến nghị
- Phát hiện cảnh báo bất thường tự động
- Hoạt động hoàn toàn offline, không cần API key

---

## 🏗 Kiến Trúc Hệ Thống

```
┌─────────────────┐    UART (9600)    ┌─────────────────┐
│   Arduino Uno   │ ◄───────────────► │      ESP32      │
│                 │    D6/D7 Serial   │                 │
│ • DHT11 (D2)    │                   │ • WiFi          │
│ • LDR (A1)      │                   │ • MQTT Client   │
│ • Relay Quạt(D9)│                   │ • Serial2(D16,17│
│ • Relay Bơm (D8)│                   └────────┬────────┘
│ • LED (D5)      │                            │
│ • Servo (D12)   │                            │ MQTT/TCP
└─────────────────┘                            │
                                               ▼
                                    ┌─────────────────┐
                                    │  HiveMQ Cloud   │
                                    │  MQTT Broker    │
                                    │ broker.hivemq   │
                                    │ .com:1883       │
                                    └────────┬────────┘
                                             │ MQTT Subscribe
                                             ▼
┌─────────────────┐   WebSocket    ┌─────────────────┐
│    Browser      │ ◄───────────── │  Flask Backend  │
│                 │                │                 │
│ • Dashboard     │  HTTP/REST     │ • Python 3.10   │
│ • Digital Twin  │ ─────────────► │ • Flask-SocketIO│
│ • AI Chat       │                │ • SQLite DB     │
│ • Security      │                │ • OpenCV        │
│   (Face+Voice)  │                │ • face_recog    │
└─────────────────┘                └─────────────────┘
```

---

## 🛠 Công Nghệ Sử Dụng

| Lớp | Công nghệ | Mô tả |
|---|---|---|
| Vi điều khiển | C/C++ Arduino | Đọc cảm biến, điều khiển relay |
| WiFi/Cloud | C/C++ ESP32 | Kết nối WiFi, MQTT publish/subscribe |
| Backend | Python 3.10, Flask | REST API, WebSocket server |
| Database | SQLite | Lưu lịch sử sensor và activity log |
| Frontend | HTML5, CSS3, JavaScript | Giao diện web responsive |
| Visualization | Canvas 2D API | Digital Twin animation |
| IoT Protocol | MQTT (HiveMQ) | Giao tiếp thiết bị-cloud nhẹ, real-time |
| Serial | UART SoftwareSerial | Giao tiếp Arduino ↔ ESP32 |
| AI/CV | OpenCV, face_recognition | Nhận diện khuôn mặt |
| Speech | Web Speech API (Chrome) | Điều khiển giọng nói tiếng Việt |
| Real-time | WebSocket, Socket.IO | Cập nhật web không cần reload |

---

## 📦 Yêu Cầu Phần Cứng

| Linh kiện | Số lượng | Mô tả |
|---|---|---|
| Arduino Uno | 1 | Vi điều khiển chính |
| ESP32 DevKit | 1 | Module WiFi + MQTT |
| DHT11 | 1 | Cảm biến nhiệt độ + độ ẩm |
| Module LDR | 1 | Cảm biến ánh sáng |
| Relay 4 kênh | 1 | Điều khiển quạt, bơm |
| Servo SG90 | 1 | Điều khiển cửa thông gió |
| Quạt DC 12V | 1 | Làm mát nhà kính |
| Bơm mini | 1 | Tưới nước |
| Đèn LED | 1 | Chiếu sáng nhà kính |
| Webcam USB | 1 | Nhận diện khuôn mặt |
| Nguồn 9V | 1 | Cấp nguồn quạt + bơm |

---

## 💻 Cài Đặt

### 1. Clone repository

```bash
git clone https://github.com/your-username/greenhouse-monitor.git
cd greenhouse-monitor
```

### 2. Cài đặt Python dependencies

```bash
pip install flask flask-socketio paho-mqtt
pip install opencv-python
pip install E:\dlib-19.22.99-cp310-cp310-win_amd64.whl
pip install face_recognition
```

### 3. Cài đặt Arduino Libraries

Mở Arduino IDE → Library Manager → Cài:
- `DHT sensor library` by Adafruit
- `Servo` by Arduino
- `SoftwareSerial` (có sẵn)
- `PubSubClient` by Nick O'Leary (cho ESP32)
- `ArduinoJson` by Benoit Blanchon

---

## ⚙️ Cấu Hình

### WiFi và MQTT (esp32/esp32.ino)

```cpp
const char* WIFI_SSID = "TEN_WIFI_CUA_BAN";
const char* WIFI_PASS = "MAT_KHAU_WIFI";
const char* MQTT_HOST = "broker.hivemq.com";
const int   MQTT_PORT = 1883;
```

### Ngưỡng điều khiển (adruino-uno/adruino-uno.ino)

```cpp
#define NGUONG_NHIET   30.0  // °C → bật quạt
#define NGUONG_MO_CUA  33.0  // °C → mở cửa
#define NGUONG_DO_AM   50.0  // %  → bật bơm
#define MANUAL_TIME   5000   // ms → giữ manual override
```

### Backend (app.py)

```python
USE_MOCK    = False          # True: dùng data giả, False: data thật
MQTT_BROKER = "broker.hivemq.com"
TOPIC_IN    = "greenhouse/sensors"
DB_PATH     = "data/greenhouse.db"
```

---

## 🚀 Chạy Hệ Thống

### Bước 1 — Upload code Arduino Uno

```
1. Rút dây D6, D7 khỏi Arduino
2. Mở adruino-uno/adruino-uno.ino trong Arduino IDE
3. Chọn Board: Arduino Uno | Port: COMx
4. Nhấn Upload
5. Cắm lại dây D6, D7
```

### Bước 2 — Upload code ESP32

```
1. Mở esp32/esp32.ino trong Arduino IDE
2. Chọn Board: ESP32 Dev Module | Port: COMx
3. Nhấn Upload
```

### Bước 3 — Train khuôn mặt (lần đầu)

```bash
python train_face.py
# Nhìn vào webcam → bấm SPACE chụp 20 ảnh → bấm Q
```

### Bước 4 — Chạy Flask server

```bash
cd greenhouse-system
python app.py
```

### Bước 5 — Mở trình duyệt

```
http://localhost:5000           → Dashboard
http://localhost:5000/twin      → Digital Twin
http://localhost:5000/ai        → AI Chat
http://localhost:5000/security  → Face ID + Voice Control
```

---

## 🖥 Giao Diện Web

| Trang | URL | Mô tả |
|---|---|---|
| Dashboard | `/` | Giám sát real-time, biểu đồ lịch sử, điều khiển thiết bị |
| Digital Twin | `/twin` | Mô phỏng 3D nhà kính, toggle thủ công |
| AI Chat | `/ai` | Chatbot hỏi đáp về trạng thái nhà kính |
| Security | `/security` | Nhận diện khuôn mặt + điều khiển giọng nói |

---

## 📡 API Reference

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/state` | Lấy trạng thái hiện tại toàn bộ hệ thống |
| GET | `/api/history` | Lấy lịch sử dữ liệu cảm biến |
| GET | `/api/logs` | Lấy nhật ký hoạt động thiết bị |
| POST | `/api/control` | Điều khiển thiết bị `{device, action}` |
| POST | `/api/mode` | Đổi chế độ auto/manual `{device, mode}` |
| POST | `/api/thresholds` | Cập nhật ngưỡng `{temp, hum, light}` |
| POST | `/api/ai_chat` | Gửi câu hỏi AI `{message}` |
| GET | `/face_status` | Trạng thái nhận diện khuôn mặt |
| GET | `/video_feed` | MJPEG stream camera real-time |

---

## 🔌 Sơ Đồ Kết Nối

### Arduino Uno

| Thiết bị | Chân Arduino | Ghi chú |
|---|---|---|
| DHT11 DATA | D2 | Nhiệt độ + Độ ẩm |
| LDR DO | A1 | Digital output |
| Đèn LED | D5 | Chiếu sáng |
| Relay Quạt IN | D9 | Active HIGH |
| Relay Bơm IN | D8 | Active HIGH |
| Servo SG90 | D12 | PWM signal |
| ESP32 RX ← | D7 (TX) | SoftwareSerial |
| ESP32 TX → | D6 (RX) | SoftwareSerial |

### ESP32

| Chân ESP32 | Kết nối | Ghi chú |
|---|---|---|
| GPIO16 (RX2) | Arduino D7 | Serial2 nhận |
| GPIO17 (TX2) | Arduino D6 | Serial2 gửi |
| GND | GND Arduino | Chung GND |
| 5V/VIN | 5V Arduino | Hoặc nguồn ngoài |

---

## 📊 Logic Điều Khiển Tự Động

| Cảm biến | Điều kiện | Thiết bị | Hành động |
|---|---|---|---|
| Nhiệt độ | > 30°C | Quạt | BẬT làm mát |
| Nhiệt độ | > 33°C | Cửa sổ | MỞ thông gió |
| Độ ẩm KK | < 50% | Bơm | BẬT tưới nước |
| Ánh sáng | Tối (DO=1) | Đèn LED | BẬT chiếu sáng |

---

## 👤 Tác Giả

Được phát triển bởi sinh viên năm cuối ngành Công nghệ Thông tin làm đồ án tốt nghiệp.

---

## 📄 License

Dự án này được phân phối dưới giấy phép MIT. Xem file `LICENSE` để biết thêm chi tiết.
