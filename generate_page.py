import os
import re
import json
import shutil
import glob

def format_promo_tag(tag):
    # Bersihkan spasi berlebih
    tag = tag.strip()
    words = tag.split()
    formatted_words = []
    for word in words:
        # Jika kata adalah ampersand (&), biarkan
        if word == "&":
            formatted_words.append(word)
            continue
        
        # Bersihkan dari tanda baca untuk deteksi kapitalisasi
        clean_word = re.sub(r'[^\w\d%]', '', word)
        
        # Jika mengandung angka (misal 36%), biarkan
        if re.search(r'\d', clean_word):
            formatted_words.append(word.upper())
        # Jika BPOM atau COD, buat kapital penuh
        elif clean_word.upper() in ["BPOM", "COD"]:
            # Pertahankan jika ada tanda baca nempel
            formatted_words.append(word.upper())
        else:
            # Ubah jadi Camel Case/Title Case (contoh: "Sudah", "Diskon")
            # Kita format hanya karakter alfabetnya saja agar tanda baca aman
            parts = re.split(r'(\W+)', word)
            formatted_parts = []
            for part in parts:
                if part.isalnum():
                    formatted_parts.append(part.capitalize())
                else:
                    formatted_parts.append(part)
            formatted_words.append("".join(formatted_parts))
            
    return " ".join(formatted_words)

def get_product_data():
    products = []
    # Cari semua file txt di 01_detail_produk
    detail_files = glob.glob("01_detail_produk/*.txt")
    detail_files.sort()

    for file_path in detail_files:
        base_name = os.path.basename(file_path)
        indeks = os.path.splitext(base_name)[0]
        
        # Ekstrak data dari file detail
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
        
        if not lines:
            continue
            
        link_affiliate = lines[0]
        
        # Cari nama produk di baris non-kosong ke-2 dst yang bukan url
        nama_produk = "Produk Affiliate"
        for line in lines[1:]:
            if line and not line.startswith("http://") and not line.startswith("https://"):
                nama_produk = line
                break
        
        # Baca JSON dari folder konten affiliate
        promo_tag = "PROMO SPESIAL"
        konten_dir = f"02_konten_affiliate/{indeks}"
        if os.path.exists(konten_dir):
            json_files = glob.glob(f"{konten_dir}/*.txt")
            if json_files:
                try:
                    with open(json_files[0], "r", encoding="utf-8") as jf:
                        data_json = json.load(jf)
                        promo_tag = data_json.get("promo_tag", "PROMO SPESIAL")
                except Exception:
                    pass

        # Cari gambar pertama di aset_produk
        thumbnail_src = ""
        aset_dir = f"03_aset_produk/{indeks}"
        if os.path.exists(aset_dir):
            images = sorted([f for f in os.listdir(aset_dir) if f.endswith(('.webp', '.jpg', '.png', '.jpeg'))])
            if images:
                thumbnail_src = os.path.join(aset_dir, images[0])

        products.append({
            "indeks": indeks,
            "nama": nama_produk,
            "link": link_affiliate,
            "promo_tag": format_promo_tag(promo_tag),
            "thumbnail_src": thumbnail_src
        })
        
    return products

def generate_html(products, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    img_dir = os.path.join(output_dir, "img")
    os.makedirs(img_dir, exist_ok=True)

    # Copy thumbnails
    for p in products:
        if p["thumbnail_src"] and os.path.exists(p["thumbnail_src"]):
            ext = os.path.splitext(p["thumbnail_src"])[1]
            dest_name = f"{p['indeks']}{ext}"
            shutil.copy(p["thumbnail_src"], os.path.join(img_dir, dest_name))
            p["thumbnail_path"] = f"img/{dest_name}"
        else:
            p["thumbnail_path"] = "https://via.placeholder.com/150?text=No+Image"

    # HTML Template dengan Tailwind CSS + Tema Lavender
    cards_html = ""
    for p in products:
        cards_html += f"""
        <!-- Card {p['indeks']} -->
        <div class="bg-[#1e1a2e] rounded-2xl shadow-xl overflow-hidden border border-violet-900/30 flex p-4 gap-4 hover:border-violet-500/50 transition-all duration-300">
            <div class="w-24 h-24 sm:w-28 sm:h-28 flex-shrink-0">
                <img src="{p['thumbnail_path']}" alt="{p['nama']}" class="w-full h-full object-cover rounded-xl shadow-inner border border-violet-800/20">
            </div>
            <div class="flex flex-col justify-between flex-grow">
                <div>
                    <h2 class="text-white text-sm font-semibold line-clamp-2 leading-snug">{p['nama']}</h2>
                    <div class="mt-1.5 flex flex-wrap items-center gap-2">
                        <span class="bg-amber-400 text-gray-950 text-[10px] font-extrabold px-2.5 py-0.5 rounded shadow-sm">
                            No. {p['indeks']}
                        </span>
                        <span class="bg-violet-600/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-full tracking-wider shadow-sm">
                            {p['promo_tag']}
                        </span>
                    </div>
                </div>
                <a href="{p['link']}" target="_blank" rel="noopener noreferrer" class="mt-2 w-full text-center bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold py-2 px-4 rounded-lg shadow-lg shadow-emerald-500/20 hover:shadow-emerald-600/30 transition-all duration-200 flex items-center justify-center gap-1">
                    Beli Sekarang
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                </a>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="id" class="bg-[#0f0d1a]">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diari Ukhti Shop - Rekomendasi Shopee Affiliate</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #0f0d1a;
            background-image: radial-gradient(circle at top, rgba(139, 92, 246, 0.15), transparent 60%);
        }}
    </style>
</head>
<body class="text-gray-100 min-h-screen flex flex-col items-center justify-between pb-8">
    <!-- Header -->
    <header class="w-full max-w-md px-6 pt-10 pb-6 text-center flex flex-col items-center">
        <img src="https://pbs.twimg.com/profile_images/2074326913972305920/zd7NKjMP_400x400.jpg" alt="Logo" class="w-20 h-20 rounded-full border-2 border-violet-400 shadow-lg shadow-violet-500/10 mb-3 object-cover">
        <h1 class="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-violet-300 via-violet-200 to-purple-300 bg-clip-text text-transparent">
            Diari Ukhti Shop
        </h1>
        <p class="text-violet-300/80 text-xs mt-1 font-medium">
            Rekomendasi Produk Pilihan Terpercaya
        </p>
    </header>

    <!-- Main Content -->
    <main class="w-full max-w-md px-4 flex-grow flex flex-col gap-4">
        {cards_html}
    </main>

    <!-- Footer -->
    <footer class="w-full max-w-md text-center py-8 text-[11px] text-violet-400/50">
        <p>© 2026 Diari Ukhti Shop. All rights reserved.</p>
    </footer>
</body>
</html>
"""

    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    products_list = get_product_data()
    generate_html(products_list, "docs")
    print(f"Halaman web berhasil dibuat di docs/index.html dengan {len(products_list)} produk.")
