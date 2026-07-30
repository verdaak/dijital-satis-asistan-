import random
from datetime import datetime, timedelta
from database import get_db_connection, init_db

random.seed(42)

CATEGORIES = ["Ruj", "Fondöten", "Parfüm", "Cilt Bakımı"]

BRANDS = [
    "MAC", "NARS", "L'Oréal", "Maybelline", 
    "Estée Lauder", "Sephora Collection", "Clinique", 
    "Fenty Beauty", "Lancôme"
]

PRODUCT_TEMPLATES = [
    # Rujlar
    ("Velvet Matte Ruj #101 (Kırmızı)", "Ruj", "MAC", 750.0, 140, 18, 55),
    ("Retro Matte Lip Ruby", "Ruj", "MAC", 820.0, 95, 20, 60),
    ("Air Matte Liquid Nude", "Ruj", "NARS", 950.0, 60, 22, 50),
    ("Color Riche Satin #204", "Ruj", "L'Oréal", 340.0, 250, 18, 65),
    ("SuperStay Vinyl Ink Lip", "Ruj", "Maybelline", 290.0, 180, 18, 45),
    ("Gloss Bomb Universal", "Ruj", "Fenty Beauty", 890.0, 45, 18, 40),
    ("L'Absolu Rouge Drama Matte", "Ruj", "Lancôme", 1150.0, 30, 25, 60),

    # Fondötenler
    ("Studio Fix Fluid SPF 15", "Fondöten", "MAC", 1250.0, 110, 20, 50),
    ("Light Reflecting Foundation", "Fondöten", "NARS", 1650.0, 75, 22, 55),
    ("Infaillible 24H Fresh Wear", "Fondöten", "L'Oréal", 450.0, 210, 18, 60),
    ("Fit Me Matte + Poreless", "Fondöten", "Maybelline", 320.0, 190, 16, 40),
    ("Double Wear Stay-in-Place", "Fondöten", "Estée Lauder", 1850.0, 40, 25, 65),
    ("Pro Filt'r Soft Matte", "Fondöten", "Fenty Beauty", 1450.0, 55, 18, 45),

    # Cilt Bakımı
    ("Advanced Night Repair Serum 50ml", "Cilt Bakımı", "Estée Lauder", 2950.0, 35, 28, 65),
    ("Moisture Surge 100H Krem 50ml", "Cilt Bakımı", "Clinique", 1350.0, 85, 20, 60),
    ("Take The Day Off Temizleme Yağı", "Cilt Bakımı", "Clinique", 980.0, 120, 18, 60),
    ("Génifique Youth Activating Serum", "Cilt Bakımı", "Lancôme", 310.0, 50, 30, 65),
    ("Vitamin C Brightening Serum", "Cilt Bakımı", "Sephora Collection", 580.0, 160, 20, 45),
    ("Hyaluronic Acid Booster", "Cilt Bakımı", "L'Oréal", 420.0, 230, 22, 55),

    # Parfümler
    ("La Vie Est Belle EDP 50ml", "Parfüm", "Lancôme", 3450.0, 65, 22, 60),
    ("Black Opium Style Eau De Parfum", "Parfüm", "Estée Lauder", 3850.0, 28, 20, 55),
    ("Fenty Eau De Parfum 75ml", "Parfüm", "Fenty Beauty", 4200.0, 20, 22, 45),
    ("Do Not Drink Vanilla EDP", "Parfüm", "Sephora Collection", 890.0, 130, 18, 35),
]

CITIES = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"]
GENDERS = ["Kadın", "Kadın", "Kadın", "Erkek", "Diğer"]


def seed_database():
    """Veritabanını hazırlar ve stok miktarlarını (stock_quantity) da içeren 23 ürün, 50 müşteri, 200 satış ekler."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS sales")
    cursor.execute("DROP TABLE IF EXISTS customers")
    cursor.execute("DROP TABLE IF EXISTS products")
    conn.commit()
    conn.close()

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Ürünleri ekle (stock_quantity ile)
    product_ids = []
    base_date = datetime(2023, 1, 1)

    for template in PRODUCT_TEMPLATES:
        name, category, brand, price, stock_qty, min_age, max_age = template
        launch_date = (base_date + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
        cursor.execute(
            """
            INSERT INTO products (name, brand, category, price, stock_quantity, target_age_min, target_age_max, launch_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, brand, category, price, stock_qty, min_age, max_age, launch_date)
        )
        product_ids.append(cursor.lastrowid)

    # 2. Müşterileri ekle (50 müşteri)
    customer_ids = []
    for _ in range(50):
        age = random.randint(18, 65)
        gender = random.choice(GENDERS)
        city = random.choice(CITIES)
        cursor.execute(
            """
            INSERT INTO customers (age, gender, city)
            VALUES (?, ?, ?)
            """,
            (age, gender, city)
        )
        customer_ids.append(cursor.lastrowid)

    # 3. Satışları ekle (200 satış)
    start_date = datetime(2024, 1, 1)
    
    for _ in range(200):
        prod_id = random.choice(product_ids)
        cust_id = random.choice(customer_ids)
        quantity = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
        sale_date = (start_date + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d")
        store_id = random.choice([101, 102, 103, 104])

        cursor.execute(
            """
            INSERT INTO sales (product_id, customer_id, quantity, sale_date, store_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (prod_id, cust_id, quantity, sale_date, store_id)
        )

    conn.commit()
    conn.close()
    print("Veritabanı stok bilgileri ile yeniden tohumlandı: 23 Ürün (Stoklu), 50 Müşteri, 200 Satış kaydı.")


if __name__ == "__main__":
    seed_database()
