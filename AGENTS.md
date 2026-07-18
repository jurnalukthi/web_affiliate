# Shopee Affiliate Content Generator Workflow

Workflow otomatisasi pembuatan konten promosi video pendek Shopee Affiliate menggunakan AI dan FFmpeg.

## Panduan Linting & Typecheck
- Script utama: Python 3.x
- Ketergantungan: `requests`, `google-genai`
- Validasi video: `ffmpeg`, `ffprobe`

## Langkah Kerja (Walkthrough)

### 1. Siapkan Deskripsi Produk
Tulis/salin spesifikasi produk dari Shopee ke dalam file teks di folder `01_detail_produk/`.
Contoh: `01_detail_produk/01.txt`

### 2. Siapkan Aset Gambar
Simpan file foto produk di folder `03_aset_produk/01/` (Format: webp/jpg/png).

### 3. Generate Video Affiliate Secara Otomatis
Jalankan script `main.py` dengan memberikan path file detail produk.
```bash
python main.py "01_detail_produk/001.txt"
```
Proses ini akan otomatis:
1. Membaca deskripsi produk dan mengekstrak meta-data secara otomatis.
2. Menggunakan API `plan-combo` untuk membuat skrip promosi pendek format JSON (termasuk tag promosi bebas overclaim yang informatif seperti "SUDAH BPOM & AMAN BUMIL").
3. Menggunakan API Gemini TTS (`gemini-3.1-flash-tts-preview`) dengan dukungan rotasi ganda API Key untuk membuat file voiceover berkualitas tinggi (`04_voice_over/001.wav`).
4. Menggabungkan file gambar produk dengan audio voiceover menggunakan FFmpeg menjadi format video potret 9:16 dengan background blur adaptif, teks promosi dinamis di atas, serta label etalase 3 digit di bawah.

*Video siap diunggah tersimpan di `02_konten_affiliate/001/001_<jenis_produk>_<merk_produk>.mp4`.*

