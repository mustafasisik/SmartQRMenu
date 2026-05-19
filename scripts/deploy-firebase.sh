#!/usr/bin/env bash
# Deploy SmartQRMenu: Cloud Run (Flask) + Firebase Hosting
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="${FIREBASE_PROJECT_ID:-smartmenuqr1}"
REGION="${CLOUD_RUN_REGION:-europe-west3}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-smartqrmenu}"
ENV_FILE="${CLOUD_RUN_ENV_FILE:-cloud-run.env}"

echo "📦 Project: $PROJECT_ID | Region: $REGION | Service: $SERVICE_NAME"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ gcloud CLI gerekli: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

if ! command -v firebase >/dev/null 2>&1; then
  echo "❌ firebase CLI gerekli: npm install -g firebase-tools"
  exit 1
fi

gcloud config set project "$PROJECT_ID"

DEPLOY_ARGS=(
  run deploy "$SERVICE_NAME"
  --source .
  --region "$REGION"
  --allow-unauthenticated
  --memory 512Mi
  --cpu 1
  --min-instances 0
  --max-instances 10
  --port 8080
)

if [ -f "$ENV_FILE" ]; then
  echo "🔐 Env file kullanılıyor: $ENV_FILE"
  DEPLOY_ARGS+=(--env-vars-file "$ENV_FILE")
else
  echo "⚠️ $ENV_FILE bulunamadı. cloud-run.env.example dosyasını kopyalayıp doldurun."
  echo "   Örnek: cp cloud-run.env.example cloud-run.env"
  exit 1
fi

echo "🚀 Cloud Run deploy başlıyor..."
gcloud "${DEPLOY_ARGS[@]}"

echo "🌐 Firebase Hosting deploy..."
firebase deploy --only hosting --project "$PROJECT_ID"

echo ""
echo "✅ Deploy tamamlandı!"
echo "   https://${PROJECT_ID}.web.app"
echo "   https://${PROJECT_ID}.firebaseapp.com"
echo ""
echo "Firebase Console → Authentication → Settings → Authorized domains"
echo "listesine bu domainleri eklediğinizden emin olun."
