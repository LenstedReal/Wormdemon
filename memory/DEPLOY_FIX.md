# Vercel Deploy Bozulması — Kök Sebep & Çözüm (Temmuz 2026)

## Kök Sebep
Emergent "Save to Github" özelliği `/app` klasörünü GitHub repo'suna (LenstedReal/Wormdemon) push ediyor.
`/app`'te Vercel için ZORUNLU dosyalar YOKTU → push edilince GitHub origin/main'den SİLİNDİLER:
- `vercel.json`  (yarn install + craco build + api/index.py python serverless + rewrites)
- `.node-version` (18)
- kök `requirements.txt` (fastapi, motor, slowapi, httpx, python-dotenv, google-search-results, dnspython)
- `.vercelignore`

Bu dosyalar olmadan Vercel:
- Paket yöneticisi olarak yarn yerine npm kullanıyor → react-scripts 5 `ajv/ajv-keywords` çakışması → build FAIL
- api/index.py'yi Python serverless olarak deploy etmiyor → backend yok

NOT: Bu, api/index.py'ye eklenen 4-katman prompt değişikliğiyle ALAKASIZ. Prompt değişikliği sorunsuz gitti (origin blob 623b21f).

## npm neden çalışmıyor (kanıtlandı)
react-scripts 5 ağacı `schema-utils@2 (ajv6/ajv-keywords3)` + `schema-utils@4 (ajv8/ajv-keywords5)` sürümlerini
AYNI ANDA gerektiriyor. npm düz kurulumda tek sürüm hoist edebildiği için her override başka bir plugin'i kırıyor.
yarn iç içe (nested) çözümle ikisini de tutabiliyor → `yarn build` sorunsuz (yerelde doğrulandı, build/static/js üretildi).

## Çözüm (uygulandı)
`/app`'e geri eklendi: `vercel.json` (+ `"framework": null` → Vercel'in CRA/npm preset'ini ezmesini engeller),
`.node-version`, kök `requirements.txt`, `.vercelignore`.
frontend/package.json ORİJİNAL bırakıldı (override YOK, hash origin ile aynı: 2355fcd).

## Kullanıcı Aksiyonları
1. Emergent "Save to Github" → /app push edilir → 4 dosya GitHub'a geri gider.
2. Vercel: Root Directory = `./`, Redeploy.
   -> vercel.json devrede: `cd frontend && yarn install --frozen-lockfile` + `npx craco build` (yarn = ajv hatası yok)
   -> api/index.py Python serverless olarak deploy olur.
3. Vercel Environment Variables (Production): MONGO_URL, DB_NAME, GROQ_API_KEY, GEMINI_API_KEY, SERPAPI_KEY, FREE_MESSAGE_LIMIT, ALLOWED_ORIGINS.
