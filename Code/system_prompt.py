import ollama
import json
import mysql.connector
from voice_input_procesing import proses_suara


nama_file_audio = "rekaman_darurat.mp3"
teks_hasil_stt = proses_suara(nama_file_audio)

print("\n HASIL TRANSKRIPSI")
print(teks_hasil_stt)
print("----------------------")

input_report = teks_hasil_stt

#instruksi ai atau system prompt
intruction_system = """ 
kamu adalah asisten triage darurat 112.
Tugas kamu hanya mengekstrak informasi dari teks laporan ke dalam format JSON yang valid
Gunakan format kunci berikut :
- "emergency_type" : (kategorikan ke : Kebakaran, Medis, Kecelakaan, Kriminal, Bencana Alam)
- "lokasi" : (Ekstrak nama tempat atau daerah yang dibutuhkan)
- "skala_bahaya": (Tentukan: Tinggi, Sedang, Rendah)

Hanya berikan output JSON mentah, tanpa awalan atau akhiran teks apa pun.
"""

print("Laporan darurat sedang diproses... \n")

#mengirim data ke Ollama 
response = ollama.chat(
    model='llama3',
    format='json',
    messages=[
        {'role': 'system', 'content': intruction_system},
        {'role': 'user', 'content': input_report},
    ]
)

output_json = response['message']['content']
data_ia = json.loads(output_json)
print("HASIL EKSTRAKSI JSON:", data_ia)


print("\nMenyimpan data ke database...")
try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="db_darurat_112"
    )

    cursor = db.cursor()

    sql = """ INSERT INTO laporan_darurat (path_file_audio, teks_transkrip, kategori_darurat, lokasi, skala_bahaya) VALUES (%s, %s, %s, %s, %s)"""

    val = (
        nama_file_audio,
        teks_hasil_stt,
        data_ia.get("emergency_type"),
        data_ia.get("lokasi"),
        data_ia.get("skala_bahaya")
    
    )

    cursor.execute(sql, val)
    db.commit()

    print(f"Data Telah Berhasil disimpan dengan ID Laporan: {cursor.lastrowid}")


except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    if 'db' in locals() and db.is_connected():
        cursor.close()
        db.close()
