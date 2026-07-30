# 🛍️ Dijital Satış Asistanı - Kozmetik Mağazası Analiz Platformu

Doğal dilde sorulan kozmetik satış sorularını SQLite veritabanı üzerinden analiz eden, grafikler çizen ve gerçek bir insan iş danışmanı gibi **veriye dayalı akıllı iş önerileri** sunan Yapay Zeka destekli bir Text-to-SQL asistanıdır.

---

## ✨ Özellikler

* **Doğal Dilden SQL'e (Text-to-SQL):** Yapay zeka entegrasyonu sayesinde teknik bilgi gerektirmeden veritabanınızdan veri çekebilirsiniz.
* **Veriye Dayalı Akıllı İş Önerileri:** 
  - Çok satan ürünler tespit edildiğinde tedarik ve vitrin önerileri sunar.
  - Az satan ürünler tespit edildiğinde promosyon ve influencer pazarlama fikirleri üretir.
  - Stok seviyeleri kritik olduğunda acil uyarı verir.
* **Görsel Raporlama:** Gelen verileri otomatik olarak grafiklere (Chart.js) veya tablolara dönüştürür.
* **İnsansı ve Samimi İletişim:** Robotik yanıtlar yerine, yanlış anlaşılmalarda özür dileyip diyalog kurabilen samimi bir asistan deneyimi sağlar.
* **Güvenlik Filtresi:** Sadece `SELECT` sorgularına izin vererek veritabanını silme veya değiştirme risklerini engeller.

---

## 🛠️ Teknolojiler

* **Backend:** FastAPI, Uvicorn, Python, SQLite
* **Frontend:** Vanilla HTML5, CSS3 (Modern Glassmorphism & Pembe/Lacivert Gece Teması), Javascript
* **Yapay Zeka:** Google Gemini API (Canlı mod) & Çevrimdışı Analiz (Demo mod)

---

## 🚀 Kurulum ve Çalıştırma

### 1. Bağımlılıkları Yükleyin
Proje dizininde terminali açıp şu komutu çalıştırın:
```bash
pip install -r requirements.txt
```

### 2. Uygulamayı Başlatın
Uygulamayı yerel sunucuda çalıştırmak için:
```bash
python main.py
```

### 3. Tarayıcıda Açın
Uygulama başladıktan sonra tarayıcınızdan aşağıdaki adrese gidin:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 💡 Örnek Kullanım Senaryoları
* *"En çok tercih edilen marka nedir?"*
* *"Stoktaki en az ürünleri listeler misin?"*
* *"Şehirlere göre müşteri yaş ortalamaları ve satış adetleri"*
* *"Kategorilere göre ciro dağılımını göster"*
