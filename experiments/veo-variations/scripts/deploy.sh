#!/bin/bash

# Configuration
PROJECT_ID="your-project-id" # CHANGE THIS TO YOUR PROJECT ID
REGION="us-central1"
SERVICE_NAME="veo-variations-studio"
SERVICE_ACCOUNT="veo-variations-sa@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
BUCKET="your-gcs-bucket" # CHANGE THIS TO YOUR GCS BUCKET
#EAP_GROUP="aaie-musicbox@google.com"

echo "===================================================================="
echo " Deploying Veo Variations Studio to Cloud Run"
echo "===================================================================="

# 1. Ensure Service Account exists and has correct roles
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create veo-variations-sa \
        --display-name="Veo Variations Studio SA" \
        --project="${PROJECT_ID}"
fi

# AI Platform User
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --condition=None --quiet >/dev/null

# Storage Admin (Mandatory for FUSE and SDK downloads)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectAdmin" \
    --condition=None --quiet >/dev/null

# 2. Build and Push via Cloud Build
echo "Building and Pushing Image via Cloud Build..."
# Run from variations/ directory
cd "$(dirname "$0")/.."
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID .

# 3. Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud beta run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --timeout 3600 \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars="VEO_PROJECT_ID=$PROJECT_ID,VEO_LOCATION=$REGION,VEO_BUCKET=gs://$BUCKET,VIDEO_DIR=/videos,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global" \
  --add-volume=name=video-storage,type=cloud-storage,bucket=$BUCKET \
  --add-volume-mount=volume=video-storage,mount-path=/videos \
  --no-allow-unauthenticated \
  --service-account="${SERVICE_ACCOUNT}" \
  --iap

# 4. Configure IAP Access
if [ -n "${EAP_GROUP}" ]; then
    echo "🔐 Configuring IAP Access for ${EAP_GROUP}..."
    gcloud beta iap web add-iam-policy-binding \
        --member="group:${EAP_GROUP}" \
        --role="roles/iap.httpsResourceAccessor" \
        --resource-type="cloud-run" \
        --region="$REGION" \
        --service="$SERVICE_NAME" \
        --project="$PROJECT_ID" \
        --condition=None \
        --quiet
fi

echo "Deployment Complete!"
