import re
from datetime import datetime
import asyncio
import os
import json
import io
import base64
import urllib.request
from gtts import gTTS

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.templating import Jinja2Templates
import mysql.connector

# Coba muat library SpeechRecognition jika sudah di-install (pip install SpeechRecognition)
try:
    import speech_recognition as sr
    SR_TERSEDIA = True
except ImportError:
    SR_TERSEDIA = False

app = FastAPI(title="Sistem Triage Darurat 112 API - Llama 3 Edition")
templates = Jinja2Templates(directory="templates")

# Nama model Llama 3 di Ollama Anda (bisa "llama3", "llama3.1", atau "llama3.2")
OLLAMA_MODEL = "llama3"
OLLAMA_URL = "http://localhost:11434/api/generate"


def teks_ke_base64_audio(teks: str) -> str:
    """Mengubah teks menjadi audio MP3 dalam format Base64 string."""
    try:
        tts = gTTS(text=teks, lang='id', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return base64.b64encode(fp.read()).decode('utf-8')
    except Exception as e:
        print(f"[WARNING TTS] Gagal membuat MP3 gTTS: {e}")
        return ""


def baca_suara_wav(file_path: str) -> str:
    """Membaca teks bahasa Indonesia dari file WAV jika transkrip browser kosong."""
    if not SR_TERSEDIA:
        print("[WARNING] Library SpeechRecognition belum diinstall (jalankan: pip install SpeechRecognition)")
        return ""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(file_path) as source:
            audio_data = recognizer.record(source)
        teks = recognizer.recognize_google(audio_data, language="id-ID")
        return teks
    except Exception as e:
        print(f"[WARNING STT] Gagal membaca suara dari WAV: {e}")
        return ""


def panggil_llama3_lokal(teks_laporan: str) -> dict:
    """
    Mengirim teks laporan ke Llama 3 Lokal (Ollama) untuk diekstrak menjadi JSON.
    """
    prompt = f"""Kamu adalah sistem triage darurat 112 Indonesia.
Analisis kalimat laporan darurat berikut:
"{teks_laporan}"

Balas HANYA dalam format JSON valid dengan kunci berikut:
{{
  "transkrip": "{teks_laporan}",
  "kategori_darurat": "Pilih satu: Kebakaran / Medis / Kecelakaan / Kriminal / Bencana Alam / Lainnya",
  "lokasi": "Nama tempat atau jalan yang disebutkan (jika tidak ada tulis Tidak diketahui)",
  "skala_bahaya": "Pilih satu: Tinggi / Sedang / Rendah"
}}"""

    # Coba panggil model llama3 / llama3.1 / llama3.2 yang ada di Ollama lokal
    for model_name in [OLLAMA_MODEL, "llama3.2", "llama3.1", "llama3:latest"]:
        try:
            payload = json.dumps({
                "model": model_name,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.0}
            }).encode("utf-8")

            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                hasil_ollama = json.loads(resp.read().decode("utf-8"))
                teks_json = hasil_ollama.get("response", "{}")
                print(f"[DEBUG] Llama 3 ({model_name}) berhasil merespons!")
                data = json.loads(teks_json)
                data["transkrip"] = teks_laporan
                return data
        except urllib.error.HTTPError as he:
            # Jika nama model tidak cocok (404), coba nama berikutnya
            if he.code == 404:
                continue
            print(f"[WARNING OLLAMA] HTTP Error: {he}")
        except Exception as e:
            print(f"[WARNING OLLAMA] Gagal menghubungi Ollama di {OLLAMA_URL}: {e}")
            break

    # Fallback cerdas jika aplikasi Ollama belum dinyalakan
    teks_lower = teks_laporan.lower()
    kat = "Lainnya"
    if any(k in teks_lower for k in ["bakar", "api", "asap", "meledak", "kebakaran"]):
        kat = "Kebakaran"
    elif any(k in teks_lower for k in ["pingsan", "sakit", "darah", "jantung", "ambulans", "medis", "luka", "korban"]):
        kat = "Medis"
    elif any(k in teks_lower for k in ["tabrak", "kecelakaan", "jatuh", "mobil", "motor", "laka"]):
        kat = "Kecelakaan"
    elif any(k in teks_lower for k in ["maling", "rampok", "curian", "begal", "bunuh", "senjata", "pencuri"]):
        kat = "Kriminal"
    elif any(k in teks_lower for k in ["banjir", "gempa", "longsor", "pohon tumbang"]):
        kat = "Bencana Alam"

    match_lok = re.search(
        r'\b(?:di|ke|jalan|jl|daerah|dekat|pasar|kampus|gedung|desa|kelurahan|kecamatan|simpang)\s+([a-zA-Z0-9\s]{3,35})',
        teks_laporan,
        re.IGNORECASE
    )
    lok = match_lok.group(1).strip() if match_lok else "Lokasi Pelapor"

    return {
        "transkrip": teks_laporan,
        "kategori_darurat": kat,
        "lokasi": lok,
        "skala_bahaya": "Tinggi"
    }


def proses_laporan_darurat(file_path: str, transkrip_awal: str = "") -> dict:
    teks_laporan = transkrip_awal.strip()

    if not teks_laporan:
        print("[DEBUG] 1. Mengekstrak ucapan dari file WAV...")
        teks_laporan = baca_suara_wav(file_path)

    if not teks_laporan:
        teks_laporan = "Laporan darurat suara (suara kurang jelas)"

    print(f"[DEBUG] 2. Teks ucapan: '{teks_laporan}'. Mengirim ke Llama 3 Lokal...")
    return panggil_llama3_lokal(teks_laporan)


@app.get("/dashboard/")
async def tampilkam_dashboard(request: Request):
    try:
        db = mysql.connector.connect(
            host="localhost", user="root", password="", database="db_darurat_112"
        )
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM laporan_darurat ORDER BY waktu_panggilan DESC")
        hasil_data = cursor.fetchall()

        cursor.close()
        db.close()

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"data_laporan": hasil_data}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat database: {str(e)}")


@app.get("/pelapor/")
async def halaman_pelapor(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pelapor.html",
        context={}
    )


@app.websocket("/ws/darurat")
async def jalur_telepon_darurat(websocket: WebSocket):
    await websocket.accept()
    print("\n[INFO] Saluran telepon darurat DIBUKA.")
    
    file_sementara = "streaming_sementara.wav"
    transkrip_browser = ""
    
    with open(file_sementara, "wb") as f:
        pass
    
    try:
        while True:
            data = await websocket.receive()
            
            if "bytes" in data and data["bytes"]:
                with open(file_sementara, "ab") as f:
                    f.write(data["bytes"])

            elif "text" in data and data["text"]:
                pesan_teks = data["text"]
                if pesan_teks == "SELESAI_LAPORAN":
                    break
                try:
                    obj = json.loads(pesan_teks)
                    if obj.get("aksi") == "SELESAI_LAPORAN":
                        transkrip_browser = obj.get("transkrip_browser", "")
                        break
                except Exception:
                    pass

    except WebSocketDisconnect:
        print("\n[INFO] Panggilan DITUTUP oleh pelapor.")
        
    if os.path.exists(file_sementara) and os.path.getsize(file_sementara) > 1024:
        ukuran = os.path.getsize(file_sementara)
        print(f"[INFO] Sedang memproses analisis laporan ({ukuran} bytes) dengan Llama 3...")
        try:
            data_json = await asyncio.to_thread(
                proses_laporan_darurat, file_sementara, transkrip_browser
            )

            teks_pelapor = data_json.get("transkrip", "Tidak terdeteksi")
            kat = data_json.get("kategori_darurat", "Lainnya")
            lok = data_json.get("lokasi", "Tidak diketahui")
            skala = data_json.get("skala_bahaya", "Sedang")

            print(f"[RESULT LLAMA 3] Transkrip: {teks_pelapor} | Kategori: {kat} | Lokasi: {lok}")

            # Simpan data ke Database MySQL Laragon
            try:
                db = mysql.connector.connect(
                    host="localhost", user="root", password="", database="db_darurat_112",
                    connection_timeout=5
                )
                cursor = db.cursor()
                waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                sql = """INSERT INTO laporan_darurat 
                         (waktu_panggilan, teks_transkrip, kategori_darurat, lokasi, skala_bahaya, status_penanganan, path_file_audio) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                
                val = (waktu_sekarang, teks_pelapor, kat, lok, skala, "Menunggu", file_sementara)
                
                cursor.execute(sql, val)
                db.commit()
                cursor.close()
                db.close()
                print("[INFO] BERHASIL! Data hasil analisis telah disimpan ke Database.")
            except Exception as db_err:
                print(f"[WARNING DB] Gagal simpan ke MySQL: {db_err}")

            # Buat teks respons konfirmasi & ubah ke audio TTS
            pesan_tts = f"Laporan {kat} di {lok} telah diterima. Petugas segera menuju ke lokasi."
            print("[DEBUG] 3. Membuat suara balasan (gTTS)...")
            audio_b64 = await asyncio.to_thread(teks_ke_base64_audio, pesan_tts)

            # Kirim teks, transkrip, & audio ke WebSocket
            await websocket.send_json({
                "tipe": "respon_suara",
                "teks": pesan_tts,
                "transkrip": teks_pelapor,
                "audio": audio_b64
            })
            print("[INFO] Respon suara berhasil dikirim ke pelapor!")

        except Exception as e:
            print(f"[ERROR SYSTEM] Gagal memproses laporan: {e}")


if __name__ == "__main__": 
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)