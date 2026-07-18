import os
import glob
import json
import re
import requests
from main import extract_metadata_from_detail, generate_script

def main():
    detail_files = sorted(glob.glob("01_detail_produk/*.txt"))
    for file_detail in detail_files:
        base_name = os.path.basename(file_detail)
        indeks = os.path.splitext(base_name)[0]
        
        print(f"\n--- Memproses caption untuk produk {indeks} ---")
        
        with open(file_detail, "r", encoding="utf-8") as f:
            detail_produk = f.read()
            
        jenis, merk = extract_metadata_from_detail(detail_produk)
        print(f"Metadata: Jenis={jenis}, Merk={merk}")
        
        skrip_folder = f"02_konten_affiliate/{indeks}"
        os.makedirs(skrip_folder, exist_ok=True)
        skrip_path = f"{skrip_folder}/{indeks}_{jenis}_{merk}.txt"
        
        try:
            # Generate ulang script lengkap dengan caption baru dari AI
            skrip = generate_script(detail_produk, jenis, merk)
            
            # Update file JSON skrip
            with open(skrip_path, "w", encoding="utf-8") as f:
                json.dump(skrip, f, indent=2, ensure_ascii=False)
            print(f"Skrip JSON diperbarui: {skrip_path}")
            
            # Simpan file caption terpisah
            caption_path = f"{skrip_folder}/{indeks}_caption.txt"
            with open(caption_path, "w", encoding="utf-8") as f:
                f.write("=== CAPTION INSTAGRAM ===\n")
                f.write(skrip.get("caption_ig", "") + "\n\n")
                f.write("=== CAPTION TIKTOK ===\n")
                f.write(skrip.get("caption_tiktok", "") + "\n")
            print(f"Caption disimpan ke: {caption_path}")
        except Exception as e:
            print(f"Gagal generate untuk produk {indeks}: {e}")

if __name__ == "__main__":
    main()
