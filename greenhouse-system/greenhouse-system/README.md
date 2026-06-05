# 🌿 GreenHouse Monitor - Flask Backend

## Cấu trúc thư mục
```
greenhouse-final/
├── app.py              ← Backend Flask
├── requirements.txt    ← Thư viện Python
├── templates/
│   └── index.html      ← Web Dashboard
├── data/
│   └── greenhouse.db   ← SQLite (tự tạo)
└── README.md
```

## Cách chạy

### Bước 1: Cài thư viện
```bash
pip install -r requirements.txt
```

### Bước 2: Chạy server
```bash
python app.py
```

### Bước 3: Mở trình duyệt
```
http://localhost:5000
```

## Kết nối ESP32

ESP32 gửi MQTT lên topic: `greenhouse/sensors`
Format JSON:
```json
{"t":30.5,"h":48.0,"l":300,"soil":500,"fan":1,"pump":0,"led":0}
```

Flask tự động nhận và hiển thị real-time!

## Điều khiển từ Web

- Bật/tắt thiết bị thủ công
- Chuyển chế độ AUTO/THỦ CÔNG
- Cài đặt ngưỡng nhiệt độ, độ ẩm, ánh sáng
- Xem biểu đồ lịch sử
- Xem nhật ký hoạt động
