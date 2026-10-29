from faster_whisper import WhisperModel
import time

def proses_suara(file_path):
    print("Mesin Sedang Mendengarkan (STT)..")
    model = WhisperModel("small", device="cpu", compute_type="int8")

    print(f"Memproses file audio: {file_path}")
    time_start = time.time()


    #transkripsi
    segments, info = model.transcribe(file_path, beam_size=5, language="id")

    # menggabungkan hasil teks 
    full_text = ""
    for segment in segments:
        full_text += segment.text + " "
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

    time_up = time.time()
    print(f"\n[STT selesai dalamn {time_up - time_start:.2f} detik]")

    #kembali ke teks penuh untuk digunakan LLM
    return full_text.strip()


