# Wormdemon — Groq Model Migration (Llama 3.3 70B → Qwen 3.6 27B)

## Problem
Groq, `llama-3.3-70b-versatile` modelini kullanımdan kaldırıyor (16 Ağustos 2026 itibarıyla hizmet dışı). Kullanıcı son birkaç gündür kötü/kesintili cevaplar alıyor. Groq'un resmi önerisi: `Qwen3.6 27B` veya `GPT OSS 120B`.

## Repo
- GitHub: https://github.com/LenstedReal/Wormdemon
- Lokal clone (geçici): /tmp/Wormdemon
- /app boş skeleton — proje Vercel'e GitHub repo'sundan deploy ediliyor

## User Strict Constraints
- Hiçbir emergent entegrasyonu eklenmeyecek
- Sorun dışında dosya ekleme/silme/tasarım değişikliği/kod düzenleme YAPILMAYACAK
- API anahtarları AYNI bırakılacak (GROQ_API_KEY mevcut)

## Done (Jan 2026)
- ✅ `api/index.py:597` — tek satır model değişikliği: `"llama-3.3-70b-versatile"` → `"qwen/qwen3.6-27b"`
- Hiçbir başka dosya/değer/yapı dokunulmadı

## Next Action Items (kullanıcı tarafı)
- Değişikliği GitHub repo'suna apply et (GitHub UI direkt edit veya local push)
- Vercel otomatik redeploy yapacak — env değişkenleri zaten doğru
- README.md (satır 9) ve memory/PRD.md (satır 13)'teki "Llama-3.3-70b" referansları opsiyonel olarak güncellenebilir (sadece dökümantasyon — kullanıcı talimatına göre opsiyonel)

## Future / Backlog
- Yedek seçenek: Qwen kalite tatmin etmezse `openai/gpt-oss-120b` modeline geçilebilir (aynı endpoint, sadece model string'i değişir)
- Multi-model fallback cascade (Qwen → GPT OSS → Gemini) — istenirse genişletilebilir
