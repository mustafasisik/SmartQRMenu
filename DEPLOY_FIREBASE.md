# Firebase Hosting + Cloud Run Deploy

SmartQRMenu bir **Flask (SSR)** uygulamasıdır. Firebase Hosting yalnızca statik dosya sunar; bu yüzden:

- **Cloud Run** → Flask API + sayfalar (gunicorn)
- **Firebase Hosting** → CDN + tüm istekleri Cloud Run'a yönlendirme

Canlı adresler:
- https://smartmenuqr1.web.app
- https://smartmenuqr1.firebaseapp.com

## Ön koşullar

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
2. [Firebase CLI](https://firebase.google.com/docs/cli): `npm install -g firebase-tools`
3. **Blaze (Pay as you go) planı** — Cloud Run için zorunlu (aşağıya bakın)
4. APIs etkin: Cloud Run, Cloud Build, Artifact Registry

### Faturalandırma (zorunlu)

`UREQ_PROJECT_BILLING_NOT_OPEN` veya `Billing account is not open` hatası alıyorsanız proje henüz ödeme hesabına bağlı değildir.

1. [Firebase Console → smartmenuqr1 → Usage and billing](https://console.firebase.google.com/project/smartmenuqr1/usage/details)
2. **Upgrade to Blaze** (veya mevcutsa **Manage billing account**)
3. Google Cloud [Billing](https://console.cloud.google.com/billing) üzerinden geçerli bir ödeme yöntemi ekleyin
4. Projeyi bu billing account’a bağlayın: [Project billing](https://console.cloud.google.com/billing/linkedaccount?project=smartmenuqr1)

Ardından API’leri tekrar açın:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=smartmenuqr1
```

**Maliyet notu:** Düşük trafikte Cloud Run genelde aylık ücretsiz kotada kalır; yine de kart tanımlanır. Sadece Hosting (statik) istiyorsanız Blaze gerekmez ama **Flask SSR bu projede Cloud Run olmadan çalışmaz**.

```bash
gcloud auth login
gcloud config set project smartmenuqr1
firebase login
```

## 1. Cloud Run ortam dosyası

```bash
cp cloud-run.env.example cloud-run.env
# cloud-run.env içini .env ile aynı değerlerle doldurun
```

`FIREBASE_PRIVATE_KEY` Cloud Run'da tek satır olmalı; `\n` kaçışlı kalabilir.

## 2. Deploy

```bash
chmod +x scripts/*.sh
./scripts/deploy-firebase.sh
```

Script sırası:
1. `gcloud run deploy smartqrmenu` (Docker build + deploy)
2. `firebase deploy --only hosting`

## 3. Firebase Auth ayarı

[Firebase Console](https://console.firebase.google.com/) → Authentication → Settings → **Authorized domains**

Şunların listede olduğundan emin olun:
- `smartmenuqr1.web.app`
- `smartmenuqr1.firebaseapp.com`
- `localhost` (geliştirme için)

## Manuel deploy (adım adım)

```bash
# Statik dosyaları public/ altına kopyala
bash scripts/prepare-hosting.sh

# Cloud Run
gcloud run deploy smartqrmenu \
  --source . \
  --region europe-west3 \
  --allow-unauthenticated \
  --env-vars-file cloud-run.env

# Hosting
firebase deploy --only hosting
```

## Sadece Hosting (Cloud Run zaten deploy edildiyse)

```bash
firebase deploy --only hosting
```

## Sorun giderme

| Sorun | Çözüm |
|--------|--------|
| `gcloud: Operation not permitted` (Desktop SDK) | macOS, Desktop’taki SDK’yı engeller. Homebrew kullanın: `brew install --cask gcloud-cli` ve `~/.zshrc` içinde Desktop yolunu kaldırın; `/opt/homebrew/share/google-cloud-sdk/path.zsh.inc` kullanın. Yeni terminal: `source ~/.zshrc` |
| `virtualenv: command not found` (brew install) | `brew install virtualenv` sonra tekrar deneyin; veya `/opt/homebrew/bin/gcloud` symlink ile SDK zaten çalışıyorsa atlayın |
| 403 / 502 Hosting | Cloud Run servis adı `smartqrmenu` ve bölge `europe-west3` olmalı (`firebase.json`) |
| Oturum çalışmıyor | `SECRET_KEY` Cloud Run'da ayarlı mı; Authorized domains doğru mu |
| Statik görseller yok | `bash scripts/prepare-hosting.sh` sonra hosting deploy |
| Build hatası | `gcloud services enable run.googleapis.com cloudbuild.googleapis.com` |

## Maliyet

- Cloud Run: istek başına, min-instance 0 (soğuk başlangıç olabilir)
- Firebase Hosting: genelde düşük trafikte ücretsiz kotada
