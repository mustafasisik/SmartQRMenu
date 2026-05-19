# Render.com Deploy Rehberi

SmartQRMenu (Flask + Groq + Pinecone + Firebase) **Firebase Hosting yerine Render** üzerinde çalışır.  
Firebase yalnızca **Auth** ve **Firestore** için kullanılmaya devam eder.

## Ön koşullar

- GitHub/GitLab’da repo
- [Render](https://render.com) hesabı (ücretsiz plan yeterli)
- `.env` / `render.env.example` içindeki API anahtarları hazır
- **GCP Blaze / Cloud Run gerekmez**

## Hızlı deploy (Blueprint)

1. Kodu GitHub’a push edin
2. [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
3. Repo’yu seçin → `render.yaml` otomatik okunur
4. İlk deploy sırasında **sync: false** olan değişkenleri girin:
   - `GROQ_API_KEY`, `PINECONE_API_KEY`
   - Tüm `FIREBASE_*` (özellikle `FIREBASE_PRIVATE_KEY` tek satır, `\n` ile)
5. **Apply** → deploy bitene kadar bekleyin

Canlı URL örneği: `https://smart-qrmenu.onrender.com`

## Manuel Web Service

Blueprint kullanmıyorsanız:

| Ayar | Değer |
|------|--------|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 app:app` |
| **Health Check** | `/api/health` |
| **Region** | Frankfurt (veya size yakın) |

Environment değişkenleri: `render.env.example` dosyasına bakın.

## Firebase Auth ayarı (önemli)

Render URL’nizi Firebase’e ekleyin:

1. [Firebase Console → Authentication → Settings → Authorized domains](https://console.firebase.google.com/project/smartmenuqr1/authentication/settings)
2. **Add domain** → `smart-qrmenu.onrender.com` (kendi Render subdomain’iniz)
3. İsteğe bağlı özel domain ekleyin

Aksi halde Google / e-posta girişi production’da çalışmaz.

## Deploy sonrası kontrol

```bash
curl https://YOUR-SERVICE.onrender.com/api/health
curl https://YOUR-SERVICE.onrender.com/api/ai-status
```

## Ücretsiz plan notları

- **Cold start:** ~30–60 sn ilk istek yavaş olabilir
- **Spin down:** 15 dk hareketsizlikten sonra uyku
- **Timeout:** Uzun AI istekleri için `--timeout 120` ayarlı

## Güncelleme

`main` branch’e push → Render otomatik yeniden deploy eder (Auto-Deploy açıksa).

## Sorun giderme

| Sorun | Çözüm |
|--------|--------|
| Build fail | `runtime.txt` → Python 3.12; log’da eksik paket var mı bakın |
| 502 / crash | Environment’da `FIREBASE_PRIVATE_KEY` formatı (`\n` kaçışlı tek satır) |
| Auth çalışmıyor | Authorized domains’e Render URL eklendi mi |
| AI yok | `GROQ_API_KEY`, `PINECONE_API_KEY` Render env’de tanımlı mı |

## Firebase Hosting ile fark

| | Render | Firebase Hosting + Cloud Run |
|--|--------|------------------------------|
| Faturalandırma | Render free tier | GCP Blaze (kart) |
| Flask SSR | Evet | Cloud Run gerekir |
| Kurulum | `render.yaml` + env | gcloud + firebase deploy |
