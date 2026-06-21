# app/utils_face.py
import json
import cv2
import numpy as np

# Load model deteksi wajah bawaan OpenCV (Sangat aman, tanpa library luar)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def get_face_embedding(image_path: str):
    """
    Mengambil potongan wajah (matriks piksel) dan merubahnya menjadi representasi data array.
    Murni menggunakan OpenCV yang 100% jalan stabil di Python 3.14 Windows.
    """
    try:
        # 1. Baca gambar
        img = cv2.imread(image_path)
        if img is None:
            print("🚨 [FACE AI] Gambar tidak terbaca!")
            return None
            
        # 2. Ubah ke Grayscale (Abu-abu) biar prosesnya cepat dan ringan
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 3. Deteksi kotak lokasi wajah
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) == 0:
            print("🚨 [FACE AI] Wajah tidak terdeteksi di foto!")
            return None
            
        # Ambil wajah pertama yang terdeteksi (x, y, width, height)
        (x, y, w, h) = faces[0]
        
        # Crop bagian wajahnya saja, lalu resize ke ukuran standar (100x100 piksel)
        face_roi = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, (100, 100))
        
        # Normalisasi matriks gambar menjadi list 1D angka rahasia
        flat_face_list = face_resized.flatten().tolist()
        
        return json.dumps(flat_face_list)
    except Exception as e:
        print(f"🚨 [FACE ERROR] Gagal ekstraksi wajah: {str(e)}")
        return None

def compare_faces(stored_embedding_json: str, new_image_path: str, threshold: float = 0.25) -> bool:
    """
    Membandingkan kesamaan matriks piksel wajah lama vs wajah baru menggunakan algoritma korelasi histogram.
    """
    try:
        # 1. Ambil data wajah baru
        new_face_string = get_face_embedding(new_image_path)
        if not new_face_string:
            return False
            
        # 2. Decode string JSON kembali ke array numpy
        old_face_data = np.array(json.loads(stored_embedding_json), dtype=np.uint8).reshape(100, 100)
        
        # Ambil gambar wajah baru, decode lagi
        new_face_data = np.array(json.loads(new_face_string), dtype=np.uint8).reshape(100, 100)
        
        # 3. Hitung kecocokan menggunakan metode Template Matching (Korelasi Normalisasi)
        res = cv2.matchTemplate(old_face_data, new_face_data, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        print(f"📐 [FACE MATCHING] Nilai akurasi kemiripan wajah: {max_val:.4f}")
        
        # max_val berkisar antara -1 sampai 1. Makin mendekati 1 artinya makin mirip (klop!).
        # Kita set threshold 0.25 atau sesuaikan nanti setelah test di HP Realme lu.
        return max_val > threshold
    except Exception as e:
        print(f"🚨 [FACE COMPARING ERROR] Gagal membandingkan wajah: {str(e)}")
        return False