import os
import json
import re
from typing import Any, Dict, List, Optional
from database import get_schema_description
from tools import run_sql_query

GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

ANTHROPIC_AVAILABLE = False
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


SYSTEM_PROMPT_TEMPLATE = """
Sen deneyimli bir kozmetik sektörü dijital satış asistanısın. Gerçek bir insan iş danışmanı gibi konuş. Robotik değil, samimi ve doğal ol.

GÖREVİN:
Kullanıcının doğal dilde sorduğu soruları veritabanı şemasını ve geçmiş konuşma bağlamını kullanarak SQLite uyumlu SQL sorgularına dönüştürmek, 'run_sql_query' tool'unu çalıştırmak, sonuçları analiz edip kullanıcıya net, anlaşılır ve İŞ DEĞERİ YÜKSEK bir yanıt vermektir.

VERİTABANI ŞEMASI:
{schema_description}

KESİN VE ESNETİLEMEZ KURALLAR:
1. YALNIZCA 'SELECT' sorguları üretebilirsin. INSERT, UPDATE, DELETE, DROP KESİNLİKLE YASAKTIR.
2. Sorgularında JOIN işlemleri yaparken tablo ilişkilerini dikkate al:
   - sales.product_id = products.id
   - sales.customer_id = customers.id
3. KESİN GERÇEK SAYI VE VERİ KURALI:
   - 'run_sql_query' tool'undan dönen sayısal verileri KESİNLİKLE BİREBİR KULLAN! Asla uydurma sayılar yazma!
4. BİLMİYORUM VE ŞEMADA YOK KURALI:
   - Eğer kullanıcının sorduğu konu veritabanı şemasında yoksa, "Üzgünüm, bu bilgi veritabanımızda bulunmuyor." de.
5. KONUŞMA HAFIZASI: Kullanıcı önceki mesajlara atıf yapıyorsa bağlamı koru.
6. Eğer tool bir SQLite hatası dönerse, sorguyu düzelterek tekrar çağır (En fazla 2 düzeltme hakkın).
7. KULLANICI SELAMLAMA MESAJI ATTIĞINDA: VERİTABANI SORGUSU ÇALIŞTIRMA! Kısa ve doğal bir selamlama ver.

YANLIŞ ANLAMA DURUMU (ÇOK ÖNEMLİ):
Eğer kullanıcı "hayır", "anlamadın", "yanlış", "öyle değil", "hayır ben bunu sordum", "onu demek istemedim" gibi bir ifade kullanırsa:
1. ÖNCE özür dile: "Kusura bakma, yanlış anlamışım."
2. SONRA ne anladığını açıkla: "Ben sorunuzu şöyle anladım: [önceki anlayışını kısaca yaz]"
3. SONRA doğrusunu sor: "Siz tam olarak ne demek istediniz?" veya "Sorunuzu biraz daha açar mısınız?"
4. KESİNLİKLE yeni bir sorgu çalıştırma, önce kullanıcının ne istediğini anla.
Kullanıcı açıklama yaptıktan sonra doğru sorguyu çalıştır.

VERİYE DAYALI AKILLI İŞ ÖNERİSİ KURALLARI (ÇOK ÖNEMLİ):
Sorgu sonuçlarını analiz ederken gerçek bir iş danışmanı gibi VERİYE DAYALI, SOMUT öneriler ver. Genel geçer klişe öneriler YASAKTIR. Şu kurallara göre öneri üret:

1. ÇOK SATAN ÜRÜN/MARKA TESPİT EDİLDİĞİNDE:
   - Stok seviyesini kontrol et, düşükse "Bu ürünün stoğu kritik seviyede, acil tedarik planlanmalı" de
   - "Bu üründen toplu alım yaparak birim maliyeti düşürmeyi değerlendirin" öner
   - "Bu ürünü vitrin ve ana sayfa öne çıkarmasına alın" de
   - Çapraz satış önerisi ver: "Bu ürünü alan müşterilere tamamlayıcı ürünler önerin"

2. AZ SATAN ÜRÜN/MARKA TESPİT EDİLDİĞİNDE:
   - "Bu ürün için indirimli kampanya veya 'al 2 öde 1' promosyonu düzenleyin" öner
   - "Sosyal medyada influencer iş birliği ile bu ürünün tanıtımını artırın" de
   - "Bu ürünü çok satan ürünlerle bundle (paket) satışa sunun" öner
   - Stok fazlası varsa "Stok eritme kampanyası başlatın" de

3. STOK ANALİZİ YAPILDIĞINDA:
   - Stok 30'un altındaysa: "KRİTİK! Bu ürünün stoğu tükenmek üzere, acil tedarik edilmeli"
   - Stok 30-70 arasındaysa: "Stok seviyesi orta, önümüzdeki ay için tedarik planı yapılmalı"
   - Stok 100'ün üzerindeyse ve satış düşükse: "Stok fazlası riski var, kampanya ile eritilmeli"

4. MÜŞTERİ ANALİZİ YAPILDIĞINDA:
   - Yaş grubuna göre ürün önerisi yap
   - Şehir bazlı satış farkları varsa "Bu şehirde yerel kampanya düzenleyin" de
   - Cinsiyet dağılımına göre hedefli pazarlama öner

5. CİRO ANALİZİ YAPILDIĞINDA:
   - En yüksek ciro yapan kategoriye "Bu kategori ana gelir kaynağınız, çeşitliliği artırın" de
   - En düşük cirolu kategoriye "Bu kategoride fiyat-performans ürünleri ekleyin" öner

YANIT TARZI:
- Gerçek bir insan gibi konuş, robot gibi değil
- Samimi ama profesyonel ol
- Teknik jargondan kaçın, anlaşılır ol
- Önerilerini somut ve uygulanabilir ver
- Kullanıcıyla diyalog kur, tek taraflı konuşma yapma

ARAÇ KULLANIMI:
- Sorgu çalıştırmak gerekiyorsa her zaman `run_sql_query` aracını (tool) kullanmalısın.
"""

TOOL_DEFINITION_ANTHROPIC = {
    "name": "run_sql_query",
    "description": "SQLite veritabanında tek bir SELECT sorgusu çalıştırır. Sonuçları JSON formatında döner.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Çalıştırılacak SQLite SELECT sorgusu."
            }
        },
        "required": ["query"]
    }
}


def is_greeting(text: str) -> tuple[bool, str]:
    t = text.lower().strip()
    words = re.findall(r'\w+', t)

    analysis_keywords = ["ruj", "satış", "satılan", "satan", "tercih", "ciro", "marka", "ürün", "kategori", "yaş", "müşteri", "şehir", "en çok", "en az", "en fazla", "kaç", "toplam", "ortalama", "nedir", "hangisi", "liste", "stok", "depo", "adet"]
    if any(ak in t for ak in analysis_keywords):
        return False, ""

    greetings_phrases = {
        "iyi akşamlar": "İyi akşamlar! Size nasıl yardımcı olabilirim? Satış verileri, stok durumu veya müşteri analizleri hakkında merak ettiğiniz her şeyi sorabilirsiniz.",
        "günaydın": "Günaydın! Harika bir gün olsun. Bugün sizin için hangi analizleri yapmamı istersiniz?",
        "iyi günler": "İyi günler! Buyurun, sizin için ne yapabilirim?",
        "selamlar": "Selamlar! Buyurun, nasıl yardımcı olabilirim?",
        "merhabalar": "Merhabalar! Sizin için ne yapabilirim?",
        "nasılsın": "Teşekkür ederim, gayet iyiyim! Siz nasılsınız? Bir şey sormak isterseniz buradayım.",
        "naber": "İyilik, teşekkürler! Sizden de iyi haberler olsun. Bir konuda yardımcı olabilir miyim?"
    }

    greetings_exact_words = {
        "merhaba": "Merhaba! Hoş geldiniz, size nasıl yardımcı olabilirim?",
        "selam": "Selam! Buyurun, nasıl yardımcı olabilirim?",
        "hey": "Hey! Hoş geldiniz, buyurun.",
        "sa": "Aleykümselam! Hoş geldiniz, buyurun.",
        "as": "Aleykümselam! Hoş geldiniz, buyurun."
    }

    for phrase, resp in greetings_phrases.items():
        if phrase in t:
            return True, resp

    for w in words:
        if w in greetings_exact_words:
            return True, greetings_exact_words[w]

    return False, ""


class SalesAnalystAgent:
    """Konuşma Hafızalı ve Gerçek Sayı Korumalı Tek Agent Mimari sınıfı."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        self.engine = "demo"
        
        if self.api_key and self.api_key.strip():
            key_clean = self.api_key.strip()
            if key_clean.startswith("AIzaSy") or GEMINI_AVAILABLE:
                try:
                    self.gemini_client = genai.Client(api_key=key_clean)
                    self.engine = "gemini"
                except Exception as e:
                    self.engine = "demo"

            if self.engine == "demo" and ANTHROPIC_AVAILABLE:
                try:
                    self.anthropic_client = anthropic.Anthropic(api_key=key_clean)
                    self.engine = "anthropic"
                except Exception as e:
                    self.engine = "demo"

    def run(self, user_question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        is_greet, greet_response = is_greeting(user_question)
        if is_greet:
            return {
                "status": "success",
                "user_question": user_question,
                "agent_response": greet_response,
                "executed_sql": None,
                "data": None,
                "trace": [{"step": "Doğal Karşılama", "status": "info"}],
                "attempts": 1,
                "mode": "live" if self.engine != "demo" else "demo",
                "triggered_code": "agent.py: Doğal Karşılama Bloğu (Satır 171-182)"
            }

        # Yanlış anlama tespiti
        q_lower = user_question.lower().strip()
        misunderstand_keywords = ["hayır", "anlamadın", "yanlış", "öyle değil", "onu demek istemedim", "hayır ben", "anlamadın ki", "yanlış anladın"]
        is_misunderstanding = any(mk in q_lower for mk in misunderstand_keywords)

        if is_misunderstanding and self.engine == "demo":
            # Önceki konuşmadan bağlam al
            prev_context = ""
            if history:
                last_assistant = [h.get("content", "") for h in history if h.get("role") == "assistant"]
                last_user = [h.get("content", "") for h in history if h.get("role") == "user"]
                if last_assistant:
                    # Önceki yanıttan kısa bir özet çıkar
                    prev_text = last_assistant[-1][:150]
                    prev_context = f"Bir önceki yanıtımda şunu söylemiştim: \"{prev_text}...\"\n\n"
                if last_user and len(last_user) >= 2:
                    prev_question = last_user[-2] if len(last_user) >= 2 else last_user[-1]
                    prev_context += f"Siz de \"{prev_question}\" diye sormuştunuz.\n\n"

            response = f"""Kusura bakın, yanlış anlamışım. {prev_context}Sorunuzu tam olarak anlayabilmem için biraz daha açar mısınız? Ne öğrenmek istediğinizi detaylı yazarsanız, size doğru analizi sunabilirim."""

            return {
                "status": "success",
                "user_question": user_question,
                "agent_response": response,
                "executed_sql": None,
                "data": None,
                "trace": [{"step": "Yanlış Anlama Tespiti - Kullanıcıdan Açıklama Bekleniyor", "status": "info"}],
                "attempts": 1,
                "mode": "demo",
                "triggered_code": "agent.py: Yanlış Anlama Tespit Bloğu (Satır 184-219)"
            }

        trace = []

        if self.engine == "gemini":
            res = self._run_gemini_agent(user_question, history, trace)
            res["triggered_code"] = "agent.py: Gemini AI Modeli (gemini-2.5-flash) (Canlı AI - Satır 233-339)"
            return res
        elif self.engine == "anthropic":
            res = self._run_anthropic_agent(user_question, history, trace)
            res["triggered_code"] = "agent.py: Anthropic Claude Modeli (claude-3-5-sonnet) (Canlı AI - Satır 341-413)"
            return res
        else:
            return self._run_mock_agent(user_question, history, trace)

    def _run_gemini_agent(self, user_question: str, history: Optional[List[Dict[str, str]]], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        schema_text = get_schema_description()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema_description=schema_text)
        trace.append({"step": "Gemini AI Çağrılıyor (gemini-2.5-flash)", "status": "pending"})

        try:
            # Temperature = 0.0 (Sıfır hayal gücü, %100 kesin sayısal doğruluk)
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[run_sql_query],
                temperature=0.0
            )

            gemini_contents = []
            if history:
                for h in history[-10:]:
                    role = "user" if h.get("role") == "user" else "model"
                    content_text = h.get("content", "")
                    if content_text:
                        gemini_contents.append({"role": role, "parts": [{"text": content_text}]})

            gemini_contents.append({"role": "user", "parts": [{"text": user_question}]})

            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gemini_contents,
                config=config
            )

            if response.function_calls:
                for fn in response.function_calls:
                    if fn.name == "run_sql_query":
                        sql_query = fn.args.get("query", "")
                        trace.append({"step": "Gemini Tool Çağrısı (run_sql_query)", "sql": sql_query})

                        sql_result = run_sql_query(sql_query)
                        
                        if sql_result["status"] == "success":
                            trace.append({"step": "Tool Başarılı", "row_count": sql_result["count"]})

                            rows_str = json.dumps(sql_result['rows'], ensure_ascii=False)
                            followup_content = gemini_contents + [
                                f"VERİTABANI BİREBİR GERÇEK SONUÇLARI:\n- SQL Sorgusu: {sql_result['query']}\n- Satır Sayısı: {sql_result['count']}\n- Dönen JSON Verisi: {rows_str}\n\nÖNEMLİ KURAL: Yanıtındaki TÜM sayıları (toplam satılan adet, müşteri sayısı, ciro vb.) KESİNLİKLE yukarıdaki JSON verisinden al! Asla 2,327 veya 500 gibi JSON'da olmayan uydurma sayılar yazma."
                            ]

                            final_resp = self.gemini_client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=followup_content,
                                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.0)
                            )

                            return {
                                "status": "success",
                                "user_question": user_question,
                                "agent_response": final_resp.text,
                                "executed_sql": sql_result["query"],
                                "data": sql_result,
                                "trace": trace,
                                "attempts": 1,
                                "mode": "live"
                            }
                        else:
                            error_msg = sql_result["error"]
                            trace.append({"step": "Auto-Healing (Hata Düzeltme)", "error": error_msg})
                            
                            fix_content = gemini_contents + [
                                f"SQL Sorgusu: '{sql_query}' çalıştırıldığında şu hata alındı: {error_msg}. Lütfen SQL'i düzelterek geçerli bir SELECT sorgusu üret."
                            ]
                            
                            fix_resp = self.gemini_client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=fix_content,
                                config=config
                            )
                            
                            if fix_resp.function_calls:
                                retry_fn = fix_resp.function_calls[0]
                                retry_sql = retry_fn.args.get("query", "")
                                retry_res = run_sql_query(retry_sql)
                                return {
                                    "status": "success",
                                    "user_question": user_question,
                                    "agent_response": f"Düzeltilmiş SQL Sorgusu Analizi:\n\n{fix_resp.text}",
                                    "executed_sql": retry_res.get("query"),
                                    "data": retry_res,
                                    "trace": trace,
                                    "attempts": 2,
                                    "mode": "live"
                                }

            return {
                "status": "success",
                "user_question": user_question,
                "agent_response": response.text,
                "executed_sql": None,
                "data": None,
                "trace": trace,
                "attempts": 1,
                "mode": "live"
            }

        except Exception as e:
            trace.append({"step": "Gemini API Hatası (Demo Moduna Geçiliyor)", "error": str(e)})
            mock_res = self._run_mock_agent(user_question, history, trace)
            mock_res["agent_response"] = f"⚠️ **Gemini API Uyarısı**: {str(e)}\n\nAnaliz **Offline Modda** tamamlanmıştır:\n\n" + mock_res["agent_response"]
            return mock_res

    def _run_anthropic_agent(self, user_question: str, history: Optional[List[Dict[str, str]]], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        schema_text = get_schema_description()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema_description=schema_text)
        trace.append({"step": "Anthropic Claude Çağrılıyor", "status": "pending"})

        formatted_messages = []
        if history:
            for h in history[-10:]:
                formatted_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

        formatted_messages.append({"role": "user", "content": user_question})

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                messages=formatted_messages,
                tools=[TOOL_DEFINITION_ANTHROPIC],
                temperature=0.0
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "run_sql_query":
                    sql_query = block.input.get("query", "")
                    trace.append({"step": "Tool Çağrısı (run_sql_query)", "sql": sql_query})
                    sql_result = run_sql_query(sql_query)

                    if sql_result["status"] == "success":
                        followup = formatted_messages + [
                            {"role": "assistant", "content": response.content},
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(sql_result, ensure_ascii=False)
                                    }
                                ]
                            }
                        ]
                        final_response = self.anthropic_client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=1000,
                            system=system_prompt,
                            messages=followup,
                            temperature=0.0
                        )
                        final_text = "".join([t.text for t in final_response.content if t.type == "text"])
                        return {
                            "status": "success",
                            "user_question": user_question,
                            "agent_response": final_text,
                            "executed_sql": sql_result["query"],
                            "data": sql_result,
                            "trace": trace,
                            "attempts": 1,
                            "mode": "live"
                        }

            return {
                "status": "success",
                "user_question": user_question,
                "agent_response": "".join([b.text for b in response.content if b.type == "text"]),
                "executed_sql": None,
                "data": None,
                "trace": trace,
                "attempts": 1,
                "mode": "live"
            }
        except Exception as e:
            return self._run_mock_agent(user_question, history, trace)

    def _run_mock_agent(self, user_question: str, history: Optional[List[Dict[str, str]]], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Veriye dayalı akıllı iş önerileri üreten çevrimdışı analiz modu.
        """
        full_context_q = user_question
        if history and len(history) > 0:
            last_user_msgs = [h.get("content", "") for h in history if h.get("role") == "user"]
            if last_user_msgs:
                full_context_q = " ".join(last_user_msgs[-2:]) + " " + user_question

        q = full_context_q.lower().strip()
        trace.append({"step": "Analiz Modu", "status": "info"})

        # Şemada olmayan konular için uydurma engeli
        unsupported_keywords = ["personel", "çalışan", "mağaza adresi", "kâr marjı", "maliyet", "şifre", "tedarikçi telefon"]
        if any(uk in q for uk in unsupported_keywords):
            return {
                "status": "success",
                "user_question": user_question,
                "agent_response": "Üzgünüm, bu bilgi veritabanımızda bulunmuyor. Şu anda ürünler, müşteriler ve satış işlemleri hakkında analiz yapabiliyorum. Başka bir konuda yardımcı olabilir miyim?",
                "executed_sql": None,
                "data": None,
                "trace": [{"step": "Şemada Olmayan Bilgi", "status": "info"}],
                "attempts": 1,
                "mode": "demo",
                "triggered_code": "agent.py: Şemada Olmayan Bilgi Engeli (Satır 425-440)"
            }

        # Stok soruları
        if "stok" in q or "depo" in q or "tüken" in q or "kalan" in q:
            if "az" in q or "düşük" in q or "kritik" in q or "en az" in q:
                sql = "SELECT name, brand, category, stock_quantity, price FROM products ORDER BY stock_quantity ASC LIMIT 10;"
            else:
                sql = "SELECT name, brand, category, stock_quantity, price FROM products ORDER BY stock_quantity ASC;"
            sql_result = run_sql_query(sql)
            rows = sql_result.get("rows", [])

            advice_lines = []
            for r in rows:
                stk = r.get("stock_quantity", 0)
                name = r.get("name", "")
                if stk < 30:
                    advice_lines.append(f"- **{name}** ({stk} adet): Stok kritik seviyede! 1-2 hafta içinde acil tedarik planlanmalı.")
                elif stk < 70:
                    advice_lines.append(f"- **{name}** ({stk} adet): Stok orta seviyede, önümüzdeki ay için sipariş verilmeli.")
                else:
                    advice_lines.append(f"- **{name}** ({stk} adet): Stok yeterli seviyede.")

            full_response = f"""Stok durumunu inceledim. İşte detaylar:

{chr(10).join(advice_lines[:10])}

**Önerilerim:**
- Stoğu 30'un altında olan ürünler için tedarikçinizle acil iletişime geçin.
- Bu ürünlerin satış hızına bakarak otomatik sipariş eşiği belirlemenizi tavsiye ederim.
- Kritik stoktaki ürünleri web sitesinde "sınırlı stok" etiketi ile göstermek aciliyet hissi yaratır ve satışı hızlandırır."""

            return {
                "status": "success", "user_question": user_question,
                "agent_response": full_response, "executed_sql": sql,
                "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
                "triggered_code": "agent.py: Stok Analiz Bloğu (Satır 444-482)"
            }

        # Toplam satış sorusu
        if "toplam satılan" in q or "toplam satış" in q or ("kaç adet" in q and "satıldı" in q):
            sql = "SELECT SUM(quantity) AS toplam_satilan_urun_adedi FROM sales;"
            sql_result = run_sql_query(sql)
            total_qty = sql_result["rows"][0]["toplam_satilan_urun_adedi"] if sql_result.get("rows") else 0

            full_response = f"""Toplam satış rakamlarına baktım: Bugüne kadar **{total_qty} adet** ürün satılmış.

**Önerilerim:**
- Günlük ortalama satışı hesaplayarak stok planlama takvimi oluşturun.
- Satış adedini artırmak için "sepete 2. ürünü ekle %20 indirim kazan" gibi kampanyalar etkili olabilir.
- Hafta sonu ve hafta içi satış dağılımını analiz ederek personel planlamanızı optimize edebilirsiniz."""

            return {
                "status": "success", "user_question": user_question,
                "agent_response": full_response, "executed_sql": sql,
                "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
                "triggered_code": "agent.py: Toplam Satış Analiz Bloğu (Satır 484-508)"
            }

        # Yaş analizi
        if "yaş" in q or "20" in q:
            sql = """SELECT c.city AS Sehir, ROUND(AVG(c.age),1) AS Ort_Yas, COUNT(DISTINCT c.id) AS Musteri_Sayisi, SUM(s.quantity) AS Satin_Alinan_Urun
FROM customers c
JOIN sales s ON c.id = s.customer_id
GROUP BY c.city
ORDER BY Satin_Alinan_Urun DESC;"""
            sql_result = run_sql_query(sql)
            rows = sql_result.get("rows", [])

            city_insights = []
            for r in rows:
                city = r.get("Sehir", "")
                avg_age = r.get("Ort_Yas", 0)
                count = r.get("Musteri_Sayisi", 0)
                qty = r.get("Satin_Alinan_Urun", 0)
                if avg_age < 25:
                    city_insights.append(f"- **{city}**: Ortalama yaş {avg_age}, {count} müşteri, {qty} ürün satışı. Genç kitleye yönelik trendy ve uygun fiyatlı ürünlere ağırlık verin.")
                elif avg_age < 35:
                    city_insights.append(f"- **{city}**: Ortalama yaş {avg_age}, {count} müşteri, {qty} ürün satışı. Bu yaş grubu kaliteye önem verir, premium ürün çeşitliliğini artırın.")
                else:
                    city_insights.append(f"- **{city}**: Ortalama yaş {avg_age}, {count} müşteri, {qty} ürün satışı. Anti-aging ve cilt bakım ürünlerini ön plana çıkarın.")

            full_response = f"""Şehirlere göre müşteri yaş profilini ve satın alma davranışlarını analiz ettim:

{chr(10).join(city_insights)}

**Önerilerim:**
- Her şehrin yaş profiline göre farklı ürün portföyü sunun.
- Genç müşteri yoğun şehirlerde sosyal medya kampanyaları, olgun müşteri yoğun şehirlerde sadakat programları daha etkili olacaktır."""

            return {
                "status": "success", "user_question": user_question,
                "agent_response": full_response, "executed_sql": sql,
                "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
                "triggered_code": "agent.py: Müşteri Yaş Analiz Bloğu (Satır 504-539)"
            }

        # Marka analizi
        if "marka" in q:
            order = "ASC" if ("en az" in q or "düşük" in q) else "DESC"
            sql = f"""SELECT p.brand AS Marka, SUM(s.quantity) AS Toplam_Satis_Adedi, ROUND(SUM(s.quantity * p.price), 2) AS Toplam_Ciro_TL
FROM sales s
JOIN products p ON s.product_id = p.id
GROUP BY p.brand
ORDER BY Toplam_Satis_Adedi {order};"""
            sql_result = run_sql_query(sql)
            rows = sql_result.get("rows", [])

            if rows:
                best = rows[0] if order == "DESC" else rows[-1]
                worst = rows[-1] if order == "DESC" else rows[0]

                best_name = best.get("Marka", "")
                best_qty = best.get("Toplam_Satis_Adedi", 0)
                best_ciro = best.get("Toplam_Ciro_TL", 0)
                worst_name = worst.get("Marka", "")
                worst_qty = worst.get("Toplam_Satis_Adedi", 0)

                brand_list = "\n".join([f"- **{r.get('Marka', '')}**: {r.get('Toplam_Satis_Adedi', 0)} adet satış, {r.get('Toplam_Ciro_TL', 0):,.2f} TL ciro" for r in rows])

                full_response = f"""Marka bazlı satış performansını analiz ettim:

{brand_list}

**Önerilerim:**
- **{best_name}** açık ara lider ({best_qty} adet, {best_ciro:,.2f} TL ciro). Bu markanın stok sürekliliğini garanti altına alın ve tedarikçiyle toplu alım indirimi müzakere edin.
- **{worst_name}** en düşük satışa sahip ({worst_qty} adet). Bu marka için şu aksiyonları değerlendirin:
  - Sosyal medyada ürün deneyim videoları paylaşın
  - Çok satan markalarla bundle paket oluşturun (örn: "{best_name} + {worst_name} seti")
  - Mağaza içi deneme/test noktası oluşturarak müşterilerin ürünü tanımasını sağlayın"""
            else:
                full_response = "Marka verisi bulunamadı."

            return {
                "status": "success", "user_question": user_question,
                "agent_response": full_response, "executed_sql": sql,
                "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
                "triggered_code": "agent.py: Marka Satış Analiz Bloğu (Satır 541-580)"
            }

        # Kategori / Ciro analizi
        if "kategori" in q or "ciro" in q:
            sql = """SELECT p.category AS Kategori, SUM(s.quantity) AS Toplam_Adet, ROUND(SUM(s.quantity * p.price), 2) AS Toplam_Ciro_TL
FROM sales s
JOIN products p ON s.product_id = p.id
GROUP BY p.category
ORDER BY Toplam_Ciro_TL DESC;"""
            sql_result = run_sql_query(sql)
            rows = sql_result.get("rows", [])

            if rows:
                top_cat = rows[0]
                low_cat = rows[-1]
                cat_list = "\n".join([f"- **{r.get('Kategori', '')}**: {r.get('Toplam_Adet', 0)} adet satış, {r.get('Toplam_Ciro_TL', 0):,.2f} TL ciro" for r in rows])

                full_response = f"""Kategori bazlı ciro dağılımını inceledim:

{cat_list}

**Önerilerim:**
- **{top_cat.get('Kategori', '')}** kategorisi ana gelir kaynağınız ({top_cat.get('Toplam_Ciro_TL', 0):,.2f} TL). Bu kategoride ürün çeşitliliğini artırın ve premium seçenekler ekleyin.
- **{low_cat.get('Kategori', '')}** kategorisi en düşük ciroya sahip ({low_cat.get('Toplam_Ciro_TL', 0):,.2f} TL). Şu aksiyonları deneyin:
  - Bu kategoride fiyat-performans ürünleri ekleyin
  - "Haftanın kategorisi" kampanyasıyla bu alana dikkat çekin
  - Çok satan kategorilerle çapraz kampanya yapın (örn: "{top_cat.get('Kategori', '')} alana {low_cat.get('Kategori', '')} hediye")\""""
            else:
                full_response = "Kategori verisi bulunamadı."

            return {
                "status": "success", "user_question": user_question,
                "agent_response": full_response, "executed_sql": sql,
                "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
                "triggered_code": "agent.py: Kategori ve Ciro Analiz Bloğu (Satır 589-623)"
            }

        # En çok satan 5 ürün sorusu
        if "en çok satan 5" in q or "en çok satan beş" in q:
            sql = """SELECT p.name AS Urun_Adi, p.brand AS Marka, p.category AS Kategori, SUM(s.quantity) AS Satis_Adedi, p.stock_quantity AS Stok
FROM sales s
JOIN products p ON s.product_id = p.id
GROUP BY p.id
ORDER BY Satis_Adedi DESC
LIMIT 5;"""
            sql_result = run_sql_query(sql)
            rows = sql_result.get("rows", [])

            if rows:
                top_list = "\n".join([f"{i+1}. **{r.get('Urun_Adi', '')}** ({r.get('Marka', '')}): {r.get('Satis_Adedi', 0)} adet satış, güncel stok {r.get('Stok', 0)} adet" for i, r in enumerate(rows)])
                
                # Kritik stok kontrolü
                critical_stock_alerts = []
                for r in rows:
                    if r.get("Stok", 100) < 30:
                        critical_stock_alerts.append(r.get("Urun_Adi", ""))

                stock_warning = ""
                if critical_stock_alerts:
                    stock_warning = f"\n⚠️ **Acil Stok Uyarısı:** En çok satanlarımızdan olan *{', '.join(critical_stock_alerts)}* ürününün stoğu 30'un altına inmiş durumda! Satış kaybetmemek için acilen sipariş geçilmeli.\n"

                full_response = f"""En çok satan ilk 5 ürünümüzün performans verileri şu şekilde:

{top_list}
{stock_warning}
**Tavsiyelerim:**
- Bu 5 ürün mağazamızın lokomotifi durumunda. Ürünlerin raf ve vitrin görünürlüğünü en üst düzeyde tutalım.
- Stoğu azalan popüler ürünlerin tedariğini önceliklendirelim.
- Web sitesinde bu ürünleri "En Çok Satanlar" kategorisinde ilk sıralarda listeleyelim."""
            else:
                full_response = "Satış verisi bulunamadı."

            return {
                "status": "success", "user_question": user_question,
                "agent_response": full_response, "executed_sql": sql,
                "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
                "triggered_code": "agent.py: En Çok Satan 5 Ürün Bloğu (Satır 625-666)"
            }

        # Ödeme yöntemi soruları
        if "ödeme" in q or "kart" in q or "nakit" in q or "qr" in q:
            sql = """SELECT payment_method AS Odeme_Yontemi, COUNT(id) AS Islem_Adedi, SUM(quantity) AS Satilan_Urun_Adedi
FROM sales
GROUP BY payment_method
ORDER BY Islem_Adedi DESC;"""
            sql_result = run_sql_query(sql)
            rows = sql_result.get("rows", [])

            payment_insights = []
            for r in rows:
                method = r.get("Odeme_Yontemi", "")
                tx_count = r.get("Islem_Adedi", 0)
                qty = r.get("Satilan_Urun_Adedi", 0)
                payment_insights.append(f"- **{method}**: {tx_count} işlem, {qty} adet ürün satışı.")

            full_response = f"""Mağazadaki ödeme yöntemlerinin kullanım oranlarını analiz ettim:

{chr(10).join(payment_insights)}

**Önerilerim:**
- Kartla ödemelerin oranına göre bankalarla komisyon oranlarını yeniden müzakere edebilirsiniz.
- QR/Mobil ödemeler genç kitle arasında popülerdir, bu alandaki entegrasyonları kolaylaştırmak sepet tamamlama hızını artırır.
- Nakit işlemler için kasa mutabakat süreçlerini dijitalleştirebilirsiniz."""

            return {
                "status": "success", "user_question": user_question,
                "agent_response": full_response, "executed_sql": sql,
                "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
                "triggered_code": "agent.py: Ödeme Yöntemleri Analiz Bloğu (Satır 670-692)"
            }

        # Genel ürün listesi (fallback)
        sql = """SELECT p.name AS Urun_Adi, p.brand AS Marka, p.category AS Kategori, SUM(s.quantity) AS Satis_Adedi, p.stock_quantity AS Stok
FROM sales s
JOIN products p ON s.product_id = p.id
GROUP BY p.id
ORDER BY Satis_Adedi DESC;"""
        sql_result = run_sql_query(sql)
        rows = sql_result.get("rows", [])

        if rows:
            top3 = rows[:3]
            bottom3 = rows[-3:] if len(rows) >= 3 else rows

            top_list = "\n".join([f"- **{r.get('Urun_Adi', '')}** ({r.get('Marka', '')}): {r.get('Satis_Adedi', 0)} adet satış, stokta {r.get('Stok', 0)} adet" for r in top3])
            bottom_list = "\n".join([f"- **{r.get('Urun_Adi', '')}** ({r.get('Marka', '')}): {r.get('Satis_Adedi', 0)} adet satış, stokta {r.get('Stok', 0)} adet" for r in bottom3])

            # Stok uyarıları
            low_stock_items = [r for r in rows if r.get("Stok", 100) < 30]
            stock_warning = ""
            if low_stock_items:
                stock_names = ", ".join([r.get("Urun_Adi", "") for r in low_stock_items[:3]])
                stock_warning = f"\n⚠️ **Acil Stok Uyarısı:** {stock_names} ürünlerinin stoğu kritik seviyede, tedarik sürecini hemen başlatın.\n"

            full_response = f"""Ürün satış performansını analiz ettim. İşte genel tablo:

**En Çok Satanlar:**
{top_list}

**En Az Satanlar:**
{bottom_list}
{stock_warning}
**Önerilerim:**
- En çok satan ürünleri mağaza girişi ve vitrine yerleştirin, online'da ana sayfada öne çıkarın.
- En az satan ürünler için "1 alana 1 bedava" veya deneme boyu hediye kampanyası başlatın.
- Çok satan ürünlerle az satanları paketleyerek bundle satış yapın, bu hem stok eritir hem de müşteriye değer sunar."""

        else:
            full_response = "Henüz satış verisi bulunamadı."

        return {
            "status": "success", "user_question": user_question,
            "agent_response": full_response, "executed_sql": sql,
            "data": sql_result, "trace": trace, "attempts": 1, "mode": "demo",
            "triggered_code": "agent.py: Genel Ürün Performans Analiz Bloğu (Satır 694-738)"
        }

