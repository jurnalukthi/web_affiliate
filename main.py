import os
import sys
import json
import re
import mimetypes
import struct
import subprocess
import requests
import random
from google import genai
from google.genai import types

GEMINI_API_KEYS = os.environ.get("GEMINI_API_KEYS", "").split(",") if os.environ.get("GEMINI_API_KEYS") else []

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    return header + audio_data

def generate_script(detail_produk, jenis, merk):
    url = "http://localhost:20128/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ.get('PLAN_COMBO_API_KEY', '')}",
        "Content-Type": "application/json"
    }

    prompt = f"""Saya mau jual {jenis} {merk} via Shopee Affiliate.
Berikut adalah detail, spesifikasi, dan deskripsi produk dari Shopee:

{detail_produk}

Buat skrip video pendek sangat singkat (total durasi 20-25 detik, isi_suara + cta maksimal 55-60 kata) untuk konten promosi video pendek.
PENTING: Jangan sebut nama platform spesifik (seperti TikTok, Instagram, Reels, YouTube, dll) di dalam skrip.
Gaya bahasa: Santai, persuasif, bahasa gaul Indonesia (racun belanja).
Struktur:
- Hook (detik 1-3): Tarik perhatian penonton. Buat 3 alternatif hook dengan sudut pandang berbeda:
  * hook_1: Sudut pandang masalah utama kulit/kebutuhan (contoh: kulit kusam, jerawat, kering).
  * hook_2: Sudut pandang harga/promo (contoh: harga murah, diskon besar, paket lengkap hemat).
  * hook_3: Sudut pandang review/rekomendasi/spesifik keunikan produk (contoh: no whitecast, kandungan viral SymWhite, rahasia glowing cepat).
- Solusi & Benefit (detik 4-20): Bahas keunggulan spesifik produk berdasarkan detail di atas (kandungan, manfaat, aman bumil/busui, BPOM, harga coret/diskon jika ada).
- CTA (detik 21-25): Arahkan klik link di bio.

Format Output:
Berikan output dalam format JSON terstruktur persis seperti ini agar mudah diproses otomatis oleh program:
{{
  "hook_1": "Teks alternatif hook 1",
  "hook_2": "Teks alternatif hook 2",
  "hook_3": "Teks alternatif hook 3",
  "isi_suara": "Teks lengkap suara isi/benefit yang akan dibaca voiceover",
  "cta": "Teks lengkap suara CTA yang akan dibaca voiceover",
  "promo_tag": "Teks promosi singkat huruf kapital (maksimal 25 karakter. Harus menarik perhatian tapi JUJUR/TIDAK OVERCLAIM sesuai detail produk, contoh: BISA COD / SUDAH BPOM / DISKON 50% / PROMO HEBOH / GARANSI ORIGINAL)"
}}
Kembalikan HANYA format JSON di atas, tanpa teks penjelasan tambahan, tanpa markdown block ```json."""

    payload = {
        "model": "plan-combo",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "stream": False
    }

    print("Mengirim permintaan pembuatan skrip ke AI...")
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    # Dapatkan teks JSON dari respon
    content = response.json()['choices'][0]['message']['content'].strip()
    
    # Bersihkan markdown json block jika ada
    if content.startswith("```json"):
        content = content.replace("```json", "", 1)
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    return json.loads(content)

def generate_voiceover(text, output_path):
    print("Membuat Voiceover menggunakan Gemini TTS...")
    
    # Gunakan model audio yang didukung: gemini-3.1-flash-tts-preview
    model = "gemini-3.1-flash-tts-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"## Transcript:\n{text}"),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Leda"
                )
            )
        ),
    )

    audio_bytes = bytearray()
    mime_type = "audio/L16;rate=24000"
    success = False
    last_error = None

    # Rotasi/fallback key apabila terjadi error
    for idx, key in enumerate(GEMINI_API_KEYS):
        print(f"Mencoba Gemini TTS dengan API Key ke-{idx+1}...")
        try:
            client = genai.Client(api_key=key)
            audio_bytes.clear()
            
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.parts is None:
                    continue
                if chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
                    inline_data = chunk.parts[0].inline_data
                    audio_bytes.extend(inline_data.data)
                    if inline_data.mime_type:
                        mime_type = inline_data.mime_type
            
            if audio_bytes:
                success = True
                break
        except Exception as e:
            print(f"Gagal dengan API Key ke-{idx+1}: {e}")
            last_error = e

    if not success:
        if last_error:
            raise last_error
        raise Exception("Gagal membuat voiceover dengan semua API Key yang tersedia.")

    wav_data = convert_to_wav(bytes(audio_bytes), mime_type)
    
    with open(output_path, "wb") as f:
        f.write(wav_data)
    print(f"Voiceover disimpan di: {output_path}")

def make_video(indeks, jenis, merk, audio_path, duration, promo_tag):
    aset_dir = f"03_aset_produk/{indeks}"
    images = sorted([os.path.join(aset_dir, f) for f in os.listdir(aset_dir) if f.endswith(('.webp', '.jpg', '.png'))])
    if not images:
        raise Exception(f"Tidak ada gambar di folder aset: {aset_dir}")

    num_images = len(images)
    dur_per_image = duration / num_images

    input_txt_path = "images.txt"
    with open(input_txt_path, "w") as f:
        for img in images:
            abs_path = os.path.abspath(img)
            f.write(f"file '{abs_path}'\n")
            f.write(f"duration {dur_per_image}\n")
        f.write(f"file '{os.path.abspath(images[-1])}'\n")

    output_video = f"02_konten_affiliate/{indeks}/{indeks}_{jenis}_{merk}.mp4"
    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    # Indeks menjadi 3 digit (misal "01" -> "001")
    try:
        indeks_num = int(indeks)
        etalase_str = f"No. Etalase: {indeks_num:03d}"
    except ValueError:
        etalase_str = f"No. Etalase: {indeks}"

    # Path font
    font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

    # Hitung ukuran font promo_tag secara dinamis berdasarkan panjang karakter agar tidak terpotong
    tag_len = len(promo_tag)
    if tag_len <= 15:
        promo_fontsize = 80
    elif tag_len <= 20:
        promo_fontsize = 65
    elif tag_len <= 25:
        promo_fontsize = 55
    else:
        promo_fontsize = 45

    # Escape teks untuk filter drawtext FFmpeg agar aman dari karakter khusus seperti '%'
    # FFmpeg membutuhkan double escaping untuk '%' (menjadi '\\\\\\%') dalam drawtext
    promo_tag_escaped = promo_tag.replace('%', '\\\\\\%').replace("'", "").replace(':', '\\:')
    etalase_str_escaped = etalase_str.replace('%', '\\\\\\%').replace("'", "").replace(':', '\\:')

    # Filter FFmpeg: 
    # 1. Split stream gambar
    # 2. Stream 1 (background): scale ke 1080x1920 (crop/stretch), blur 30, desaturasi sedikit jika ingin gelap
    # 3. Stream 2 (foreground): scale fit ke 1080x1920 (force_original_aspect_ratio=decrease)
    # 4. Overlay foreground di atas background blur secara presisi di tengah
    # 5. Tulis promo_tag di atas
    # 6. Tulis etalase_str di bawah
    filter_complex = (
        f"[0:v]split=2[bg_src][fg_src];"
        f"[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];"
        f"[fg_src]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[tmp1];"
        f"[tmp1]drawtext=fontfile='{font_path}':text='{promo_tag_escaped}':fontcolor=white:fontsize={promo_fontsize}:"
        f"x=(w-text_w)/2:y=200:borderw=5:bordercolor=black,"
        f"drawtext=fontfile='{font_path}':text='{etalase_str_escaped}':fontcolor=yellow:fontsize=70:"
        f"x=(w-text_w)/2:y=1650:borderw=5:bordercolor=black[v]"
    )

    ffmpeg_cmd = (
        f'ffmpeg -y -f concat -safe 0 -i "{input_txt_path}" -i "{audio_path}" '
        f'-filter_complex "{filter_complex}" -map "[v]" -map 1:a '
        f'-c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "{output_video}"'
    )

    print("Memproses render video dengan FFmpeg...")
    subprocess.run(ffmpeg_cmd, shell=True, check=True)
    os.remove(input_txt_path)
    print(f"Video berhasil dibuat di: {output_video}")

def extract_metadata_from_detail(detail_produk):
    lines = [line.strip() for line in detail_produk.split("\n") if line.strip()]
    first_line = ""
    # Cari baris pertama yang bukan link/url
    for line in lines:
        if not line.startswith("http://") and not line.startswith("https://"):
            first_line = line
            break

    # Cari merk dari field "Merek" di detail
    # Cari dengan regex yang lebih sederhana untuk menghindari backtracking tak berujung
    merek_match = re.search(r"Merek\s*\n*([^\n]+)", detail_produk, re.IGNORECASE)
    # Default merk jika kosong
    merk = "brand"
    if merek_match:
        val = merek_match.group(1).strip()
        if "icon" not in val.lower() and len(val) < 30:
            # Ganti titik atau spasi dengan underscore untuk nama file
            merk = val.replace(".", "").replace(" ", "_").strip()

    # Potong kata-kata pertama untuk jenis produk
    words = [w for w in re.split(r'\s+', first_line) if len(w) > 2][:3]
    jenis = "_".join(words).lower()
    
    # Bersihkan karakter non alpha-numeric
    jenis = re.sub(r'[^a-zA-Z0-9_]', '', jenis)
    merk = re.sub(r'[^a-zA-Z0-9_]', '', merk.lower())
    if not merk:
        merk = "brand"
    
    return jenis, merk

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_file_detail>")
        sys.exit(1)

    file_detail = sys.argv[1]
    if not os.path.exists(file_detail):
        print(f"File detail tidak ditemukan: {file_detail}")
        sys.exit(1)

    # Dapatkan indeks dari nama file detail (misal "01.txt" -> "01")
    base_name = os.path.basename(file_detail)
    indeks = os.path.splitext(base_name)[0]

    with open(file_detail, "r", encoding="utf-8") as f:
        detail_produk = f.read()

    # Ekstrak metadata
    jenis, merk = extract_metadata_from_detail(detail_produk)
    print(f"Terdeteksi produk -> Jenis: {jenis}, Merk: {merk}, Indeks: {indeks}")

    # 1. Buat Skrip
    skrip = generate_script(detail_produk, jenis, merk)
    
    skrip_folder = f"02_konten_affiliate/{indeks}"
    os.makedirs(skrip_folder, exist_ok=True)
    skrip_path = f"{skrip_folder}/{indeks}_{jenis}_{merk}.txt"
    with open(skrip_path, "w", encoding="utf-8") as f:
        json.dump(skrip, f, indent=2, ensure_ascii=False)
    print(f"Skrip JSON disimpan ke: {skrip_path}")

    # 2. Buat Voiceover
    # Pilih hook secara acak dari hook_1, hook_2, atau hook_3
    pilihan_hook = random.choice(["hook_1", "hook_2", "hook_3"])
    hook_terpilih = skrip.get(pilihan_hook, skrip.get("hook_1", ""))
    print(f"Hook terpilih secara acak: {pilihan_hook} -> \"{hook_terpilih}\"")
    
    teks_suara = f"{hook_terpilih} {skrip['isi_suara']} {skrip['cta']}"
    audio_folder = "04_voice_over"
    os.makedirs(audio_folder, exist_ok=True)
    audio_path = f"{audio_folder}/{indeks}.wav"
    generate_voiceover(teks_suara, audio_path)

    # Dapatkan durasi audio
    cmd_dur = f'ffprobe -i "{audio_path}" -show_entries format=duration -v quiet -of csv="p=0"'
    duration = float(subprocess.check_output(cmd_dur, shell=True).decode('utf-8').strip())

    # 3. Buat Video
    promo_tag = skrip.get("promo_tag", "PROMO SPESIAL")
    make_video(indeks, jenis, merk, audio_path, duration, promo_tag)

    # 4. Update Halaman Web & Push ke GitHub
    print("Memperbarui halaman web etalase...")
    try:
        # Jalankan script generate_page.py
        subprocess.run("python3 generate_page.py", shell=True, check=True)
        # Git add, commit, dan push
        commit_msg = f"feat: update product {indeks} ({jenis} {merk})"
        git_cmd = f'git add docs/ && git commit -m "{commit_msg}" && git push origin main'
        print("Mengirim update ke GitHub...")
        subprocess.run(git_cmd, shell=True, check=True)
        print("Halaman web berhasil diperbarui dan dipush ke GitHub!")
    except Exception as e:
        print(f"Gagal memperbarui halaman web otomatis: {e}")

if __name__ == "__main__":
    main()
