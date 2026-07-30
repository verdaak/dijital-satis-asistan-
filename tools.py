import re
import sqlite3
from typing import Any, Dict, List, Tuple
from database import get_db_connection

# Güvenlik için engellenen SQL komut anahtar kelimeleri
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", 
    "TRUNCATE", "CREATE", "REPLACE", "ATTACH", "DETACH",
    "GRANT", "REVOKE", "PRAGMA", "EXEC", "EXECUTE"
]


def validate_sql_query(query: str) -> Tuple[bool, str]:
    """
    SQL Sorgusu Güvenlik Kontrolü.
    Sadece SELECT sorgularına izin verir. Veri veya tablo değiştirmeye çalışan
    tüm komutları (INSERT, UPDATE, DELETE, DROP vb.) ve tehlikeli karakterleri engeller.
    
    Bu fonksiyon sunumda bağımsız ve net bir şekilde gösterilebilir.
    """
    clean_query = query.strip()
    
    # 1. Boş sorgu kontrolü
    if not clean_query:
        return False, "HATA: SQL sorgusu boş olamaz."

    # 2. Birden fazla SQL deyimini engelle (SQL Injection koruması: ';')
    # Tırnak içindeki noktalı virgülleri yok saymak için regex veya basit ayrıştırma yapılabilir
    statements = [s for s in clean_query.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "GÜVENLİK UYARISI: Tek seferde birden fazla SQL sorgusu çalıştırılamaz."

    # 3. Yorum satırlarını temizle (-- ve /* */)
    query_without_comments = re.sub(r'--.*$', '', clean_query, flags=re.MULTILINE)
    query_without_comments = re.sub(r'/\*.*?\*/', '', query_without_comments, flags=re.DOTALL)

    # 4. Sorgunun SELECT ile başlayıp başlamadığını kontrol et
    normalized_query = query_without_comments.strip().upper()
    if not (normalized_query.startswith("SELECT") or normalized_query.startswith("WITH")):
        return False, "GÜVENLİK İHLALİ: Yalnızca okuma amaçlı 'SELECT' sorguları çalıştırılabilir."

    # 5. Yasaklı anahtar kelime taraması (Word Boundary kontrolü ile)
    for kw in FORBIDDEN_KEYWORDS:
        pattern = r'\b' + kw + r'\b'
        if re.search(pattern, normalized_query):
            return False, f"GÜVENLİK İHLALİ: '{kw}' komutunun kullanılması kesinlikle yasaktır."

    return True, "OK"


def run_sql_query(query: str) -> Dict[str, Any]:
    """
    Agent'ın çağırdığı TEK TOOL.
    
    İşlevleri:
    1. Güvenlik kontrolü yapar (validate_sql_query).
    2. Sorguda LIMIT yoksa otomatik LIMIT 50 ekler.
    3. SQLite veritabanına bağlanıp sorguyu çalıştırır.
    4. Başarılıysa: Sonuç satırlarını JSON uyumlu dict listesi olarak döndürür.
    5. Hata durumunda: Hata metnini aynen döndürür ki Agent görüp sorguyu düzeltebilsin.
    """
    # 1. Güvenlik doğrulaması
    is_valid, error_msg = validate_sql_query(query)
    if not is_valid:
        return {
            "status": "error",
            "error": error_msg,
            "query": query
        }

    # 2. Otomatik LIMIT 50 ekleme (Eğer LIMIT zaten yoksa)
    processed_query = query.strip()
    # Noktalı virgülü sondan temizle
    if processed_query.endswith(";"):
        processed_query = processed_query[:-1].strip()

    if not re.search(r'\bLIMIT\b', processed_query, re.IGNORECASE):
        processed_query += " LIMIT 50"

    # 3. SQLite Veritabanında Çalıştırma
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(processed_query)

        # Sütun isimlerini al
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        
        # Row objelerini standart dict'e çevir
        result_rows = [dict(row) for row in rows]
        conn.close()

        return {
            "status": "success",
            "query": processed_query,
            "columns": columns,
            "rows": result_rows,
            "count": len(result_rows)
        }

    except sqlite3.Error as e:
        # SQLite Syntax hatası, yanlış sütun adı vb. hatayı Agent'a geri bildir
        return {
            "status": "error",
            "error": f"SQLite Hətası: {str(e)}",
            "query": processed_query
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Beklenmeyen Sistem Hatası: {str(e)}",
            "query": processed_query
        }
