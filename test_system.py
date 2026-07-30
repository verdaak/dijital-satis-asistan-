import sys
from database import init_db, get_db_stats
from seed_data import seed_database
from tools import validate_sql_query, run_sql_query
from agent import SalesAnalystAgent


def test_system():
    print("=== 1. VERİTABANI KONTROLÜ VE TOHUM LAMA ===")
    init_db()
    seed_database()
    stats = get_db_stats()
    print(f"Tablo İstatistikleri: {stats}")
    assert stats["products"] > 0, "Ürünler tablosu boş!"
    assert stats["sales"] > 0, "Satışlar tablosu boş!"
    print("[OK] Veritabanı testi BASARILI\n")

    print("=== 2. GUVENLIK KONTROLU (validate_sql_query) ===")
    # Güvenli sorgular
    valid_1, msg1 = validate_sql_query("SELECT * FROM products")
    assert valid_1 is True, f"Geçerli SELECT sorgusu reddedildi: {msg1}"

    valid_2, msg2 = validate_sql_query("WITH top_sales AS (SELECT * FROM sales) SELECT * FROM top_sales")
    assert valid_2 is True, f"Geçerli CTE SELECT sorgusu reddedildi: {msg2}"

    # Yasaklı sorgular
    drop_valid, drop_msg = validate_sql_query("DROP TABLE sales")
    assert drop_valid is False, "DROP TABLE sorgusu engellenmedi!"

    delete_valid, delete_msg = validate_sql_query("DELETE FROM customers WHERE id = 1")
    assert delete_valid is False, "DELETE sorgusu engellenmedi!"

    insert_valid, insert_msg = validate_sql_query("INSERT INTO products (name) VALUES ('Test')")
    assert insert_valid is False, "INSERT sorgusu engellenmedi!"

    print("[OK] Guvenlik filtresi (SELECT-only) testi BASARILI\n")

    print("=== 3. TOOL KONTROLU (run_sql_query) ===")
    # Limit testi
    res = run_sql_query("SELECT name, brand, price FROM products")
    assert res["status"] == "success", f"Tool çalıştırma hatası: {res.get('error')}"
    assert "LIMIT 50" in res["query"], "Otomatik LIMIT 50 eklenmedi!"
    assert len(res["rows"]) > 0, "Sonuç satırı dönmedi!"
    print(f"Tool Başarılı! Dönen satır sayısı: {res['count']}")
    print("[OK] Tool calistirma ve Otomatik LIMIT testi BASARILI\n")

    print("=== 4. TEK AGENT KONTROLU (SalesAnalystAgent) ===")
    agent = SalesAnalystAgent()
    user_q = "En çok satan 3 ürün hangisidir?"
    agent_res = agent.run(user_q)
    
    assert agent_res["status"] == "success", f"Agent çalıştırma hatası: {agent_res.get('agent_response')}"
    assert agent_res["executed_sql"] is not None, "Agent SQL sorgusu üretmedi!"
    print(f"Soru: {user_q}")
    print(f"Agent Tarafından Çalıştırılan SQL:\n{agent_res['executed_sql']}")
    safe_resp = agent_res['agent_response'][:200].encode('ascii', errors='ignore').decode('ascii')
    print(f"Agent Yanit Ozeti:\n{safe_resp}...")
    print("[OK] Agent calistirma testi BASARILI\n")

    print("=== TUM SISTEM TESTLERI BASARIYLA GECTI! ===")


if __name__ == "__main__":
    test_system()
