import re
from datetime import datetime
import asyncio
import shutil
import os
import json
import io
import base64
from gtts import gTTS

from fastapi import FastAPI, UploadFile, File, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.templating import Jinja2Templates
import ollama
import mysql.connector
from faster_whisper import WhisperModel

from voice_input_procesing import proses_suara

model = WhisperModel("base", device="cpu", compute_type="int8")

app = FastAPI(title="Sistem Triage Darurat 112 API")
templates = Jinja2Templates(directory="templates")


def teks_ke_base64_audio(teks: str) -> str:
    """Mengubah teks menjadi audio MP3 dalam bentuk format Base64 string."""
    tts = gTTS(text=teks, lang='id', slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    audio_bytes = fp.read()
    return base64.b64encode(audio_bytes).decode('utf-8')


@app.post("/proses-laporan/")
async def proses_laporan(file: UploadFile = File(...)):
    file_location = f"temp_audio/temp_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try: 
        print(f"Memproses file: {file.filename}")
        teks_hasil_stt = proses_suara(file_location)

        instruction_system = """ 
        Kamu adalah asisten triage darurat 112.
        Tugas kamu hanya mengekstrak informasi dari teks laporan ke dalam format JSON yang valid.
        Gunakan format kunci berikut:
        - "emergency_type": (Kategorikan ke: Kebakaran, Medis, Kecelakaan, Kriminal, Bencana Alam)
        - "lokasi": (Ekstrak nama tempat atau daerah yang dibutuhkan)
        - "skala_bahaya": (Tentukan: Tinggi, Sedang, Rendah)
        Hanya berikan output JSON mentah, tanpa awalan atau akhiran teks apa pun.
        """

        response = ollama.chat(
            model='llama3',
            format='json',
            messages=[
                {'role': 'system', 'content': instruction_system},
                {'role': 'user', 'content': teks_hasil_stt}, 
            ]
        )

        output_json = response['message']['content']
        data_ai = json.loads(output_json)

        jenis_darurat = data_ai.get("emergency_type")
        lokasi_kejadian = data_ai.get("lokasi")

        print("\n" + "="*50)
        print(" # MENGIRIM NOTIFIKASI KE INSTANSI TERKAIT #")

        if jenis_darurat == "Kebakaran":
            print(f"[TERKIRIM KEDAMKAR] -> Pesan: telah terjadi kebakaran di {lokasi_kejadian}. segera luncurkan armada!")
        elif jenis_darurat == "Medis":
            print(f"[TERKIRIM KE RSUD/AMBULANS] -> Pesan: Dibutuhkan penanganan medis darurat di {lokasi_kejadian}.")
        elif jenis_darurat == "Kriminal":
            print(f"[TERKIRIM KE POLRESTA] -> Pesan: Tindak kriminal dilaporkan di {lokasi_kejadian}. Mohon segera kirimkan unit patroli.")
        elif jenis_darurat == "Kecelakaan":
            print(f"[TERKIRIM KE DISHUB/POLANTAS] -> Pesan: Terjadi kecelakaan lalu lintas di {lokasi_kejadian}.")
        else:
            print(f"[TERKIRIM KE TIM SAR/BPBD] -> Pesan: Terdapat laporan insiden ({jenis_darurat}) di {lokasi_kejadian}.")

        print("="*50 + "\n")

        db = mysql.connector.connect(
            host="localhost", user="root", password="", database="db_darurat_112"
        )
        cursor = db.cursor()
        sql = """ INSERT INTO laporan_darurat (path_file_audio, teks_transkrip, kategori_darurat, lokasi, skala_bahaya) VALUES (%s, %s, %s, %s, %s)"""

        val = (
            file.filename,
            teks_hasil_stt,
            data_ai.get("emergency_type"),
            data_ai.get("lokasi"),
            data_ai.get("skala_bahaya")
        )

        cursor.execute(sql, val)
        db.commit()
        id_laporan = cursor.lastrowid

        cursor.close()
        db.close()

        os.remove(file_location)

        pesan_respon = f"Laporan {jenis_darurat} di {lokasi_kejadian} berhasil diterima."
        audio_b64 = teks_ke_base64_audio(pesan_respon)

        return {
            "status": "success",
            "pesan": "Laporan berhasil diproses dan disimpan.",
            "id_laporan": id_laporan,
            "transkrip_asli": teks_hasil_stt,
            "data_ai": data_ai,
            "audio_response": audio_b64
        }

    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Telah terjadi kesalahan internal: {str(e)}")


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
    
    file_sementara = "streaming_sementara.webm"
    teks_pelapor = ""
    
    try:
        while True:
            data = await websocket.receive()
            
            # Jika menerima data suara berupa bytes
            if "bytes" in data and data["bytes"]:
                data_suara = data["bytes"]
                with open(file_sementara, "wb") as f:
                    f.write(data_suara)
                
                # Validasi ukuran file > 1KB agar tidak crash pada file kosong/corrupt
                if os.path.exists(file_sementara) and os.path.getsize(file_sementara) > 1024:
                    try:
                        segments, info = await asyncio.to_thread(
                            model.transcribe, file_sementara, beam_size=5, language="id"
                        )
                        teks_pelapor = " ".join([segment.text for segment in segments]).strip()
                        
                        if teks_pelapor:
                            await websocket.send_json({
                                "tipe": "transkrip",
                                "pesan": f"Pusat mendengar: {teks_pelapor}"
                            })
                    except Exception as e:
                        print(f"[DEBUG STT]: Menunggu audio lengkap... ({e})")

            # Jika menerima sinyal teks dari frontend (misal: Selesai Bicara)
            elif "text" in data and data["text"]:
                pesan_klien = data["text"]
                if pesan_klien == "SELESAI_LAPORAN":
                    break

    except WebSocketDisconnect:
        print("\n[INFO] Panggilan DITUTUP oleh pelapor.")
        
    # Proses ekstraksi & TTS setelah panggilan selesai/dihentikan
    if teks_pelapor:
        print(f"[INFO] Sedang memproses AI untuk laporan: '{teks_pelapor}'...")
        try:
            prompt = f"""
            Ekstrak informasi dari teks berikut ke dalam format JSON saja. Jangan tambahkan kata-kata lain.
            Teks laporan: '{teks_pelapor}'
            Format wajib:
            {{
                "kategori_darurat": "Kebakaran/Medis/Kecelakaan/Kriminal/Lainnya",
                "lokasi": "Nama lokasi",
                "skala_bahaya": "Tinggi/Sedang/Rendah"
            }}
            """
            
            response = await asyncio.to_thread(
                ollama.chat, 
                model='llama3',
                messages=[{'role': 'user', 'content': prompt}],
                format='json'
            )
            hasil_teks = response['message']['content'].strip()

            try:
                data_json = json.loads(hasil_teks)
            except json.JSONDecodeError:
                data_json = {
                    "kategori_darurat": "Lainnya",
                    "lokasi": "Tidak diketahui",
                    "skala_bahaya": "Sedang"
                }

            # Simpan ke Database
            db = mysql.connector.connect(
                host="localhost", user="root", password="", database="db_darurat_112"
            )
            cursor = db.cursor()
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            sql = """INSERT INTO laporan_darurat 
                     (waktu_panggilan, teks_transkrip, kategori_darurat, lokasi, skala_bahaya, status_penanganan, path_file_audio) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            
            val = (
                waktu_sekarang, 
                teks_pelapor, 
                data_json.get("kategori_darurat", "Lainnya"), 
                data_json.get("lokasi", "Tidak diketahui"), 
                data_json.get("skala_bahaya", "Sedang"), 
                "Menunggu",
                file_sementara
            )
            
            cursor.execute(sql, val)
            db.commit()
            cursor.close()
            db.close()
            print("[INFO] BERHASIL! Data telah disimpan ke Database.")

            # Buat teks konfirmasi & ubah ke audio TTS
            kat = data_json.get("kategori_darurat", "laporan")
            lok = data_json.get("lokasi", "lokasi Anda")
            pesan_tts = f"Laporan {kat} di {lok} telah diterima. Petugas sedang diproses ke lokasi."
            
            audio_b64 = teks_ke_base64_audio(pesan_tts)

            # Kirim respons suara balik ke WebSocket
            await websocket.send_json({
                "tipe": "respon_suara",
                "teks": pesan_tts,
                "audio": audio_b64
            })

        except Exception as e:
            print(f"[ERROR SYSTEM] Gagal di tahap akhir: {e}")


if __name__ == "__main__": 
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)