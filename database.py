import sqlite3
import os
from typing import Any, Dict, List

# SQLite veritabanı dosya adı
DB_FILE = "sales_data.db"


def get_db_connection() -> sqlite3.Connection:
    """Veritabanı bağlantısı oluşturur ve Row factory ayarlar."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Sütun isimleriyle erişim imkanı sağlar
    return conn


def init_db() -> None:
    """Veritabanı tablolarını (products, customers, sales) oluşturur."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Ürünler tablosu (stok bilgisi 'stock_quantity' dahil)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL DEFAULT 100,
        target_age_min INTEGER NOT NULL,
        target_age_max INTEGER NOT NULL,
        launch_date TEXT NOT NULL
    );
    """)

    # 2. Müşteriler tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        city TEXT NOT NULL
    );
    """)

    # 3. Satışlar tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        sale_date TEXT NOT NULL,
        store_id INTEGER NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    );
    """)

    conn.commit()
    conn.close()


def get_schema_description() -> str:
    """Agent'ın sistem promptuna verilecek veritabanı şema açıklamasını döndürür."""
    return """
VERİTABANI ŞEMASI (SQLite):

1. products (Ürünler ve Stok Bilgisi):
   - id: INTEGER (Birincil Anahtar)
   - name: TEXT (Ürün adı, örn: 'Mat Ruj #101', 'Likit Fondöten Sand')
   - brand: TEXT (Marka adı: 'L'Oréal', 'Maybelline', 'MAC', 'NARS', 'Estée Lauder', 'Sephora Collection', 'Clinique', 'Fenty Beauty', 'Lancôme')
   - category: TEXT (Kategori: 'Ruj', 'Fondöten', 'Parfüm', 'Cilt Bakımı')
   - price: REAL (Birim fiyat TL)
   - stock_quantity: INTEGER (Depodaki/Mağazadaki Mevcut Stok Adedi, örn: 35, 80, 150)
   - target_age_min: INTEGER (Hedef minimum yaş)
   - target_age_max: INTEGER (Hedef maksimum yaş)
   - launch_date: TEXT (Çıkış tarihi, YYYY-MM-DD)

2. customers (Müşteriler):
   - id: INTEGER (Birincil Anahtar)
   - age: INTEGER (Müşteri yaşı, 18-68 arası)
   - gender: TEXT (Cinsiyet: 'Kadın', 'Erkek', 'Diğer')
   - city: TEXT (Şehir: 'İstanbul', 'Ankara', 'İzmir', 'Bursa', 'Antalya')

3. sales (Satış İşlemleri):
   - id: INTEGER (Birincil Anahtar)
   - product_id: INTEGER (products.id yabancı anahtar)
   - customer_id: INTEGER (customers.id yabancı anahtar)
   - quantity: INTEGER (Satılan adet)
   - sale_date: TEXT (Satış tarihi, YYYY-MM-DD)
   - store_id: INTEGER (Mağaza numarası: 101, 102, 103, 104)

İlişkiler:
- sales.product_id -> products.id
- sales.customer_id -> customers.id
"""


def get_db_stats() -> Dict[str, Any]:
    """Veritabanındaki tablo ve satır sayılarını özetler (Debug / UI amaçlı)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}
    for table in ["products", "customers", "sales"]:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
        row = cursor.fetchone()
        stats[table] = row["cnt"] if row else 0

    conn.close()
    return stats
