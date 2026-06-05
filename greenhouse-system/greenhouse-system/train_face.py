"""
TRAIN KHUON MAT CHU NHAN
Chay: python train_face.py
Huong dan:
- Nhin thang vao camera
- Bam SPACE de chup anh (can 20 anh)
- Bam Q de thoat va luu
"""

import cv2
import os
import pickle
import face_recognition

# Tao thu muc luu anh
os.makedirs("faces/owner", exist_ok=True)
os.makedirs("faces/model", exist_ok=True)

print("="*45)
print("  TRAIN KHUON MAT CHU NHAN")
print("="*45)
print("- Nhin thang vao camera")
print("- Bam SPACE de chup anh (can 30 anh)")
print("- Bam Q de luu va thoat")
print("="*45)

cap = cv2.VideoCapture(0)
count = 0
MAX_PHOTOS = 30

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detect khuon mat
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)

    # Ve khung xanh quanh mat
    for (top, right, bottom, left) in locations:
        color = (0, 255, 100) if count < MAX_PHOTOS else (100, 100, 100)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, f"Phat hien mat!", (left, top-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Hien thi so anh da chup
    cv2.putText(frame, f"Anh: {count}/{MAX_PHOTOS}",
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,100), 2)

    if count >= MAX_PHOTOS:
        cv2.putText(frame, "Du anh! Bam Q de luu",
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
    else:
        cv2.putText(frame, "Bam SPACE de chup",
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 2)

    cv2.imshow("Train Khuon Mat - GreenHouse", frame)

    key = cv2.waitKey(1) & 0xFF

    # Chup anh
    if key == ord(' ') and locations and count < MAX_PHOTOS:
        path = f"faces/owner/photo_{count:03d}.jpg"
        cv2.imwrite(path, frame)
        count += 1
        print(f"Da chup anh {count}/{MAX_PHOTOS}: {path}")

    # Thoat
    if key == ord('q') or count >= MAX_PHOTOS:
        break

cap.release()
cv2.destroyAllWindows()

# ── ENCODE KHUON MAT ──────────────────────
print(f"\nDa chup {count} anh. Dang encode khuon mat...")

encodings = []
for img_file in os.listdir("faces/owner"):
    if not img_file.endswith('.jpg'):
        continue
    path = f"faces/owner/{img_file}"
    img = face_recognition.load_image_file(path)
    enc = face_recognition.face_encodings(img)
    if enc:
        encodings.append(enc[0])
        print(f"  OK: {img_file}")
    else:
        print(f"  Skip (khong tim thay mat): {img_file}")

if not encodings:
    print("KHONG TIM THAY KHUON MAT! Chay lai va chup ro hon.")
else:
    # Luu model
    with open("faces/model/owner_encodings.pkl", "wb") as f:
        pickle.dump(encodings, f)
    print(f"\nLuu thanh cong! {len(encodings)} anh encode.")
    print("File: faces/model/owner_encodings.pkl")
    print("\nChay 'python app.py' de bat dau he thong!")