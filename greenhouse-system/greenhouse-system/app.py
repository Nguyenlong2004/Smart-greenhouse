"""
GREENHOUSE MONITOR - FLASK BACKEND
ESP32 + MQTT + SQLite + WebSocket
Chay: python app.py
URL : http://localhost:5000
URL : http://localhost:5000/twin (Digital Twin)
"""

import os, json, random, sqlite3, threading, pickle
from datetime import datetime
from flask import Flask, jsonify, request, render_template, Response
from flask_socketio import SocketIO, emit

# Face recognition (cài: pip install face_recognition opencv-python)
try:
    import cv2
    import face_recognition
    import numpy as np
    FACE_OK = True
    print("OK Face Recognition san sang!")
except ImportError:
    FACE_OK = False
    print("WARN: Chua cai face_recognition! Chay: pip install face_recognition opencv-python")

# ── CAU HINH ─────────────────────────
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883
TOPIC_IN    = "greenhouse/sensors"
TOPIC_FAN   = "greenhouse/control/fan"
TOPIC_PUMP  = "greenhouse/control/pump"
TOPIC_LED   = "greenhouse/control/led"
TOPIC_DOOR  = "greenhouse/control/door"
DB_PATH     = "data/greenhouse.db"
USE_MOCK    = False  # False = nhan data that tu ESP32

# ── KHOI TAO ─────────────────────────
app      = Flask(__name__)
app.config["SECRET_KEY"] = "greenhouse2024"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

state = {
    "temp"      : 28.0,
    "hum"       : 62.0,
    "light"     : 1500,
    "soil"      : 500,
    "relays"    : {"fan": False, "pump": False, "led": False, "door": False},
    "modes"     : {"fan": "auto", "pump": "auto", "led": "auto"},
    "thresholds": {"temp": 30.0, "hum": 50.0, "light": 2000},
    "runtime"   : {"fan": 0.0, "pump": 0.0, "led": 0.0},
    "mqtt_ok"   : False,
    "updated"   : "--:--:--",
}
DEVICE_NAME = {"fan": "Quat", "pump": "Bom tuoi", "led": "Den LED"}

# ── FACE RECOGNITION STATE ────────────────
face_state = {"is_owner": False, "name": ""}
owner_encodings = []

def load_face_model():
    global owner_encodings
    model_path = "faces/model/owner_encodings.pkl"
    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            owner_encodings = pickle.load(f)
        print(f"OK Load {len(owner_encodings)} face encodings!")
    else:
        print("WARN: Chua co model khuon mat! Chay train_face.py truoc!")

def gen_frames():
    """Generator stream camera + face recognition"""
    if not FACE_OK:
        return
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Resize nho lai cho nhanh
        small = cv2.resize(frame, (0,0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        # Detect faces
        locations = face_recognition.face_locations(rgb_small)
        encodings = face_recognition.face_encodings(rgb_small, locations)
        found_owner = False
        for enc, loc in zip(encodings, locations):
            matches = []
            if owner_encodings:
                matches = face_recognition.compare_faces(owner_encodings, enc, tolerance=0.5)
            is_owner = any(matches)
            found_owner = found_owner or is_owner
            # Ve khung len frame goc
            top, right, bottom, left = [v*4 for v in loc]
            color = (0,255,100) if is_owner else (0,0,255)
            label = "CHU NHAN" if is_owner else "KHONG RO"
            cv2.rectangle(frame, (left,top), (right,bottom), color, 2)
            cv2.rectangle(frame, (left,bottom-30), (right,bottom), color, -1)
            cv2.putText(frame, label, (left+4, bottom-8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
        # Cap nhat trang thai
        face_state["is_owner"] = found_owner
        face_state["name"] = "Chu Nhan" if found_owner else ""
        # Them thong tin
        status = "DA NHAN DIEN" if found_owner else "DANG QUET..."
        color  = (0,255,100) if found_owner else (0,200,255)
        cv2.putText(frame, status, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, "GreenHouse Security", (10, frame.shape[0]-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100,100,100), 1)
        # Encode JPEG
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
               buf.tobytes() + b'\r\n')
    cap.release()

# ── DATABASE ─────────────────────────
def init_db():
    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS sensor_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, temp REAL, hum REAL,
        light INTEGER, soil INTEGER)""")
    con.execute("""CREATE TABLE IF NOT EXISTS activity_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, device TEXT, action TEXT,
        source TEXT, reason TEXT)""")
    con.commit(); con.close()
    print("OK Database san sang")

def db_save_sensor(t, h, l, s=0):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO sensor_log(ts,temp,hum,light,soil) VALUES(?,?,?,?,?)",
        (datetime.now().strftime("%H:%M:%S %d/%m/%Y"), t, h, l, s))
    con.commit(); con.close()

def db_save_log(device, action, source, reason=""):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO activity_log(ts,device,action,source,reason) VALUES(?,?,?,?,?)",
        (datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
         device, action, source, reason))
    con.commit(); con.close()

def db_get_history(n=60):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM sensor_log ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    con.close()
    return [dict(r) for r in reversed(rows)]

def db_get_logs(n=30):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]

# ── RUNTIME TRACKER ──────────────────
def runtime_loop():
    import time
    while True:
        time.sleep(60)
        for d in ["fan","pump","led"]:
            if state["relays"][d]:
                state["runtime"][d] = round(state["runtime"][d] + 1, 1)

# ── MQTT ─────────────────────────────
mqtt_client = None

def mqtt_send(device, value):
    topics = {"fan": TOPIC_FAN, "pump": TOPIC_PUMP, "led": TOPIC_LED}
    if mqtt_client and state["mqtt_ok"] and device in topics:
        mqtt_client.publish(topics[device], value)

def start_mqtt():
    global mqtt_client
    try:
        import paho.mqtt.client as mqtt

        def on_connect(c, u, f, rc):
            if rc == 0:
                state["mqtt_ok"] = True
                c.subscribe(TOPIC_IN)
                print(f"OK MQTT ket noi: {MQTT_BROKER}")
            else:
                print(f"MQTT loi code: {rc}")

        def on_message(c, u, msg):
            try:
                d = json.loads(msg.payload.decode())
                # Nhan tu ESP32
                # Format: {"t":30.5,"h":48.0,"l":300,"soil":500,"fan":1,"pump":0,"led":0}
                if "t"    in d: state["temp"]  = float(d["t"])
                if "h"    in d: state["hum"]   = float(d["h"])
                if "l"    in d: state["light"] = int(d["l"])
                if "soil" in d: state["soil"]  = int(d["soil"])
                if "fan"  in d: state["relays"]["fan"]  = bool(int(d["fan"]))
                if "pump" in d: state["relays"]["pump"] = bool(int(d["pump"]))
                if "led"  in d: state["relays"]["led"]  = bool(int(d["led"]))
                if "door" in d: state["relays"]["door"] = bool(int(d["door"]))
                state["updated"] = datetime.now().strftime("%H:%M:%S")

                db_save_sensor(state["temp"], state["hum"],
                               state["light"], state["soil"])
                socketio.emit("update", state)
                print(f"[ESP32] T={state['temp']} H={state['hum']} "
                      f"L={state['light']} S={state['soil']}")
            except Exception as e:
                print(f"MQTT loi: {e}")

        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Khong ket noi MQTT: {e}")

# ── MOCK DATA ────────────────────────
def mock_loop():
    import time
    print("Mock data dang chay...")
    while True:
        time.sleep(5)
        if state["mqtt_ok"]: continue
        state["temp"]  = round(max(20, min(40, state["temp"]  + random.uniform(-0.5,0.8))), 1)
        state["hum"]   = round(max(30, min(90, state["hum"]   + random.uniform(-1.5,1.5))), 1)
        state["light"] = int(max(0, min(4095, state["light"]  + random.uniform(-150,150))))
        state["soil"]  = int(max(0, min(1023, state["soil"]   + random.uniform(-30,30))))
        state["updated"] = datetime.now().strftime("%H:%M:%S")
        for d in ["fan","pump","led"]:
            if state["relays"][d]:
                state["runtime"][d] = round(state["runtime"][d] + 5/60, 1)
        db_save_sensor(state["temp"], state["hum"], state["light"], state["soil"])
        socketio.emit("update", state)

# ── REST API ─────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ── DIGITAL TWIN ─────────────────────
@app.route("/twin")
def twin():
    return render_template("digital-twin.html")

@app.route("/ai")
def ai_page():
    return render_template("chatbot.html")

@app.route("/api/state")
def api_state():
    return jsonify(state)

@app.route("/api/history")
def api_history():
    return jsonify(db_get_history(60))

@app.route("/api/logs")
def api_logs():
    return jsonify(db_get_logs(30))

@app.route("/api/control", methods=["POST"])
def api_control():
    body   = request.json or {}
    device = body.get("device", "")
    action = body.get("action", "")
    if device not in DEVICE_NAME:
        return jsonify({"error": "device sai"}), 400
    is_on = (action == "on")
    state["relays"][device] = is_on
    state["modes"][device]  = "manual"
    db_save_log(DEVICE_NAME[device],
                "ON" if is_on else "OFF",
                "Web", "Dieu khien thu cong")
    mqtt_send(device, "1" if is_on else "0")
    socketio.emit("update", state)
    return jsonify({"ok": True})

@app.route("/api/mode", methods=["POST"])
def api_mode():
    body   = request.json or {}
    device = body.get("device")
    mode   = body.get("mode")
    if device in state["modes"] and mode in ("auto","manual"):
        state["modes"][device] = mode
        socketio.emit("update", state)
        return jsonify({"ok": True})
    return jsonify({"error": "sai"}), 400

@app.route("/api/thresholds", methods=["POST"])
def api_thresholds():
    body = request.json or {}
    for k in ("temp","hum","light"):
        if k in body:
            state["thresholds"][k] = float(body[k])
    db_save_log("He thong", "UPDATE", "Web",
                f"Nguong moi: {state['thresholds']}")
    socketio.emit("update", state)
    return jsonify({"ok": True})

# -- AI CHAT ROUTE ------------------------------------------
@app.route("/api/ai_chat", methods=["POST"])
def ai_chat():
    body = request.json or {}
    msg  = body.get("message","").lower()
    t    = round(state["temp"], 1)
    h    = round(state["hum"], 1)
    l    = state["light"]
    fan  = state["relays"]["fan"]
    pump = state["relays"]["pump"]
    led  = state["relays"]["led"]
    door = state["relays"].get("door", False)

    # Pre-compute strings to avoid f-string issues
    fan_s  = "DANG BAT" if fan  else "DANG TAT"
    pump_s = "DANG BAT" if pump else "DANG TAT"
    led_s  = "DANG BAT" if led  else "DANG TAT"
    door_s = "DANG MO"  if door else "DANG DONG"
    reply  = ""

    # Trang thai chung
    if any(w in msg for w in ["the nao","trang thai","hien tai","bao cao","tong quan","suc khoe"]):
        issues = []
        if t > 30:  issues.append("nhiet do cao (" + str(t) + "C)")
        if h < 50:  issues.append("do am thap (" + str(h) + "%)")
        if l > 800: issues.append("thieu anh sang (" + str(l) + " raw)")
        if issues:
            reply = "CANH BAO: " + ", ".join(issues) + "\n"
        else:
            reply = "Nha kinh hoat dong tot!\n"
        reply += "Nhiet do: " + str(t) + "C | Do am: " + str(h) + "% | Anh sang: " + str(l) + "\n"
        devs = []
        if fan:  devs.append("Quat dang chay")
        if pump: devs.append("Bom dang tuoi")
        if led:  devs.append("Den dang sang")
        if door: devs.append("Cua dang mo")
        reply += ", ".join(devs) if devs else "Tat ca thiet bi dang tat."

    # Nhiet do
    elif any(w in msg for w in ["nhiet","nong","lanh","nhiet do","temperature"]):
        if t > 33:
            reply = "Nhiet do " + str(t) + "C rat cao!\n"
            reply += "Quat: " + fan_s + "\n"
            reply += "Cua: " + door_s + "\n"
            reply += "Khuyen nghi: Kiem tra thong gio ngay!"
        elif t > 30:
            reply = "Nhiet do " + str(t) + "C hoi cao.\n"
            reply += "Quat " + fan_s + ".\n"
            reply += "Cay co the bi stress nhiet neu keo dai."
        elif t < 20:
            reply = "Nhiet do " + str(t) + "C hoi thap.\n"
            reply += "Cay nhiet doi can > 20C de sinh truong tot."
        else:
            reply = "Nhiet do " + str(t) + "C rat ly tuong (20-30C)!"

    # Do am / tuoi nuoc
    elif any(w in msg for w in ["do am","am","tuoi","nuoc","bom","kho","moisture"]):
        if h < 40:
            reply = "Do am " + str(h) + "% rat thap! Cay dang thieu nuoc.\n"
            reply += "Bom: " + pump_s
        elif h < 50:
            reply = "Do am " + str(h) + "% thap hon nguong 50%.\n"
            reply += "Bom " + pump_s + ".\n"
            reply += "Nen tuoi them nuoc."
        elif h > 80:
            reply = "Do am " + str(h) + "% kha cao.\n"
            reply += "Co the gay nam benh neu keo dai.\n"
            reply += "Khuyen nghi: Mo cua thong gio."
        else:
            reply = "Do am " + str(h) + "% ly tuong!\n"
            reply += "Bom " + pump_s + " (du am)."

    # Anh sang
    elif any(w in msg for w in ["anh sang","sang","toi","den","ldr","light"]):
        if l > 800:
            reply = "Anh sang yeu (" + str(l) + " raw) - troi toi.\n"
            reply += "Den LED: " + led_s + ".\n"
            reply += "Cay can 8-12 gio sang moi ngay."
        elif l > 400:
            reply = "Anh sang " + str(l) + " raw - muc trung binh.\n"
            reply += "Den: " + led_s + "."
        else:
            reply = "Anh sang tot (" + str(l) + " raw).\n"
            reply += "Cay dang nhan du anh sang tu nhien."

    # Quat
    elif any(w in msg for w in ["quat","fan","lam mat"]):
        reply = "Quat: " + fan_s + "\n"
        reply += "Nhiet do: " + str(t) + "C (nguong bat: 30C)\n"
        if (fan and t > 30) or (not fan and t <= 30):
            reply += "Hoat dong dung!"
        else:
            reply += "Kiem tra lai logic!"

    # Bom
    elif any(w in msg for w in ["bom","pump"]):
        reply = "Bom: " + pump_s + "\n"
        reply += "Do am: " + str(h) + "% (nguong bat: <50%)\n"
        if (pump and h < 50) or (not pump and h >= 50):
            reply += "Hoat dong dung!"
        else:
            reply += "Kiem tra lai logic!"

    # Cua
    elif any(w in msg for w in ["cua","servo","thong gio","door"]):
        reply = "Cua thong gio: " + door_s + "\n"
        reply += "Nhiet do: " + str(t) + "C (mo khi >33C)\n"
        if (door and t > 33) or (not door and t <= 33):
            reply += "Hoat dong dung!"
        else:
            reply += "Kiem tra lai!"

    # Canh bao bat thuong
    elif any(w in msg for w in ["bat thuong","canh bao","nguy hiem","alert","warn"]):
        warns = []
        if t > 35:  warns.append("Nhiet do cuc cao: " + str(t) + "C")
        if t < 15:  warns.append("Nhiet do cuc thap: " + str(t) + "C")
        if h < 30:  warns.append("Do am nguy hiem: " + str(h) + "%")
        if h > 90:  warns.append("Do am qua cao: " + str(h) + "% - nguy co nam benh")
        if warns:
            reply = "CANH BAO:\n" + "\n".join(warns)
        else:
            reply = "Khong co canh bao bat thuong.\nTat ca thong so trong gioi han an toan!"

    # Khuyen nghi
    elif any(w in msg for w in ["khuyen nghi","de xuat","nen lam","tu van","recommend"]):
        recs = []
        if t > 30: recs.append("Tang toc do quat hoac mo cua them")
        if h < 50: recs.append("Tuoi nuoc them, tan suat 2-3 lan/ngay")
        if l > 800: recs.append("Bo sung den LED 12-16 gio/ngay")
        if t < 20: recs.append("Giu am nha kinh, dong cua lai")
        if recs:
            reply = "Khuyen nghi:\n" + "\n".join(["- " + r for r in recs])
        else:
            reply = "Nha kinh dang hoat dong tot!\nDuy tri nhiet do 20-30C, do am 50-80%."

    # Xin chao
    elif any(w in msg for w in ["xin chao","hello","hi","chao"]):
        reply = "Xin chao! Toi la AI cua nha kinh thong minh.\n"
        reply += "Nhiet do: " + str(t) + "C | Do am: " + str(h) + "% | Anh sang: " + str(l) + "\n"
        reply += "Hoi toi bat cu dieu gi ve nha kinh!"

    # Mac dinh
    else:
        reply  = "Du lieu hien tai:\n"
        reply += "Nhiet do: " + str(t) + "C\n"
        reply += "Do am: " + str(h) + "%\n"
        reply += "Anh sang: " + str(l) + " raw\n\n"
        reply += "Hay hoi cu the hon nhu:\n"
        reply += "- Nhiet do co on khong?\n"
        reply += "- Can tuoi nuoc khong?\n"
        reply += "- Nha kinh dang the nao?"

    return jsonify({"reply": reply})

# ── SECURITY ROUTES ─────────────────────
@app.route("/security")
def security():
    return render_template("security.html")

@app.route("/video_feed")
def video_feed():
    if not FACE_OK:
        return "Face recognition not installed", 503
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/face_status")
def face_status():
    return jsonify(face_state)

# ── WEBSOCKET ────────────────────────
@socketio.on("connect")
def ws_connect():
    print("[WS] Browser ket noi")
    emit("update", state)

@socketio.on("disconnect")
def ws_disconnect():
    print("[WS] Browser ngat ket noi")

# ── MAIN ─────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*45)
    print("  GREENHOUSE MONITOR - Server")
    print("="*45)
    init_db()
    start_mqtt()
    threading.Thread(target=runtime_loop, daemon=True).start()
    if USE_MOCK:
        threading.Thread(target=mock_loop, daemon=True).start()
    load_face_model()
    print(f"\n Dashboard : http://localhost:5000")
    print(f" Digital Twin: http://localhost:5000/twin\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)