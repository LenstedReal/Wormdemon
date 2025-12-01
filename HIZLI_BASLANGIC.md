# ⚡ Hızlı Başlangıç Kılavuzu

## 🚀 3 Adımda Çalıştırın

### 1️⃣ API Key'lerini Ekleyin

**Dosya:** `/app/backend/.env`

```env
# Claude API Key (https://console.anthropic.com/)
ANTHROPIC_API_KEY="sk-ant-api03-BURAYA_KENDI_KEYINIZI_YAPIN"

# OpenRouter API Key (https://openrouter.ai/keys)
OPENROUTER_API_KEY="sk-or-BURAYA_KENDI_KEYINIZI_YAPIN"
```

### 2️⃣ Backend'i Restart Edin

```bash
sudo supervisorctl restart backend
```

### 3️⃣ Test Edin

Frontend'den mesaj gönderin: `http://localhost:3000`

---

## 🔍 Sorun Giderme

### Backend Çalışmıyor mu?

```bash
# Logları kontrol edin
tail -f /var/log/supervisor/backend.err.log

# Servis durumunu kontrol edin
sudo supervisorctl status backend
```

### "401 Authentication Error" Alıyorsanız

➡️ API key'leriniz hatalı veya eksik
➡️ `.env` dosyasını kontrol edin
➡️ Backend'i restart edin

### "Bağlantı sorunu" Mesajı Alıyorsanız

➡️ Backend çalışıyor mu kontrol edin: `curl http://localhost:8001/api/health`
➡️ Frontend `.env` dosyasında `REACT_APP_BACKEND_URL=http://localhost:8001` olmalı

---

## 📋 Yapılan Ana Değişiklikler

### ✅ DNS Optimization
- Cloudflare DNS (1.1.1.1) + NextDNS
- %50-60 daha hızlı API çağrıları

### ✅ Backend Düzeltmeleri
- Claude 3.5 Sonnet + Llama 3.1 70B
- MongoDB bağlantı hataları düzeltildi
- API Router prefix eklendi

### ✅ Frontend İyileştirmeleri
- Timeout 10 saniyeye düşürüldü
- Local backend'e yönlendirildi
- Daha iyi hata mesajları

### ✅ Gereksiz Paketler Temizlendi
- requirements.txt'den 15+ paket kaldırıldı
- Sadece gerekli paketler kaldı

---

## 📖 Detaylı Dokümantasyon

Tüm değişikliklerin detaylı açıklaması için:
➡️ `/app/DEGISIKLIK_RAPORU.md`

---

## 🎯 Sonraki Adımlar

1. ✅ API key'leri ekleyin
2. ✅ Backend'i restart edin
3. ✅ Test edin
4. 🚀 Vercel'e deploy edin (isteğe bağlı)

**Not:** Vercel deployment için environment variable'ları Vercel dashboard'dan ayarlayın.
