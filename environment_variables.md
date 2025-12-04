# Application Environment Variables Explainer

This document details the environment variables used in the application, as defined in `config/default.py`. These variables control infrastructure settings, model versions, storage locations, and feature configurations.

## 🌍 Core Infrastructure & Environment
These variables define the fundamental operating context of the application.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`PROJECT_ID`** | *None* (Required) | The Google Cloud Project ID where resources (Vertex AI, Firestore, Storage) are located. |
| **`LOCATION`** | `us-central1` | The default GCP region for most services (Vertex AI, etc.). |
| **`APP_ENV`** | `""` (Empty) | Defines the environment (e.g., `dev`, `prod`). Used to load environment-specific content files like `config/about_content.{env}.json`. |
| **`API_BASE_URL`** | `http://localhost:{PORT}` | The base URL for the application's backend APIs. |
| **`PORT`** | `8080` | The port the application server listens on. |
| **`SERVICE_ACCOUNT_EMAIL`** | *None* | The email of the service account used for authentication, if applicable. |
| **`GA_MEASUREMENT_ID`** | *None* | Google Analytics Measurement ID for tracking user interactions. |

## 🧠 Gemini Models (Text & Multimodal)
Controls which versions of the Gemini models are used for various tasks.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`MODEL_ID`** | `gemini-2.5-flash` | The primary Gemini model used for general text and reasoning tasks throughout the app. |
| **`GEMINI_IMAGE_GEN_MODEL`** | `gemini-2.5-flash-image` | The specific model used for image generation features. |
| **`GEMINI_IMAGE_GEN_LOCATION`** | `global` | The region for the Gemini Image Generation API. |
| **`GEMINI_AUDIO_ANALYSIS_MODEL_ID`** | `gemini-2.5-flash` | The model used specifically for analyzing audio content. |

## 🎥 Veo (Video Generation)
Configuration for the Veo video generation models.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`VEO_MODEL_ID`** | `veo-2.0-generate-001` | The standard Veo model version. |
| **`VEO_PROJECT_ID`** | `PROJECT_ID` | Allows using a different project for Veo quota if needed. |
| **`VEO_EXP_MODEL_ID`** | `veo-3.0-generate-001` | The experimental/newer Veo model version. |
| **`VEO_EXP_FAST_MODEL_ID`** | `veo-3.0-fast-generate-001` | The faster, lower-latency experimental Veo model. |
| **`VEO_EXP_PROJECT_ID`** | `PROJECT_ID` | Project ID for experimental Veo models. |

## 🎨 Imagen (Image Generation & Editing)
Settings for Imagen models, including specialized versions for editing and product shots.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`MODEL_IMAGEN_PRODUCT_RECONTEXT`** | `imagen-product-recontext-preview-06-30` | Model used for "Product Recontextualization" features. |
| **`IMAGEN_GENERATED_SUBFOLDER`** | `generated_images` | Subfolder in the GCS bucket where generated images are saved. |
| **`IMAGEN_EDITED_SUBFOLDER`** | `edited_images` | Subfolder for images resulting from editing operations. |

## 🛍️ Virtual Try-On (VTO)
Specific configuration for the Virtual Try-On feature.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`VTO_LOCATION`** | `us-central1` | Region for the VTO API. |
| **`VTO_MODEL_ID`** | `virtual-try-on-preview-08-04` | The specific VTO model version. |
| **`GENMEDIA_VTO_MODEL_COLLECTION_NAME`** | `genmedia-vto-model` | Firestore collection for VTO model data. |
| **`GENMEDIA_VTO_CATALOG_COLLECTION_NAME`** | `genmedia-vto-catalog` | Firestore collection for VTO product catalog data. |

## 🎵 Lyria (Music Generation)
Configuration for the Lyria music generation model.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`LYRIA_LOCATION`** | `us-central1` | Region for Lyria API calls. |
| **`LYRIA_MODEL_VERSION`** | `lyria-002` | The version of the Lyria model to use. |
| **`LYRIA_PROJECT_ID`** | `PROJECT_ID` | Project ID for Lyria quota. |

## 💾 Storage & Database (Firebase/GCS)
Defines where data and media assets are stored.

| Variable | Default | Description |
| :--- | :--- | :--- |
| **`GENMEDIA_FIREBASE_DB`** | `(default)` | The Firestore database ID. |
| **`GENMEDIA_COLLECTION_NAME`** | `genmedia` | The main Firestore collection for storing generation metadata. |
| **`SESSIONS_COLLECTION_NAME`** | `sessions` | Firestore collection for user session data. |
| **`GENMEDIA_BUCKET`** | `{PROJECT_ID}-assets` | The primary GCS bucket for storing generated media. |
| **`VIDEO_BUCKET`** | `{PROJECT_ID}-assets/videos` | Specific bucket/path for video files. |
| **`IMAGE_BUCKET`** | `{PROJECT_ID}-assets/images` | Specific bucket/path for image files. |
| **`MEDIA_BUCKET`** | `{PROJECT_ID}-assets` | Used by Lyria and potentially other legacy components. |
| **`GCS_ASSETS_BUCKET`** | *None* | Bucket for static assets used in the "About" page. |

## ⚙️ Application Logic
| Variable | Default | Description |
| :--- | :--- | :--- |
| **`LIBRARY_MEDIA_PER_PAGE`** | `15` | Controls how many items appear per page in the media library. |
| **`USE_MEDIA_PROXY`** | `true` | If `true`, media URLs are proxied to avoid CORS/hotlinking issues. |
| **`CHARACTER_CONSISTENCY_VEO_MODEL`** | `veo-3.0-fast-generate-001` | Model used specifically in the Character Consistency workflow. |
| **`CHARACTER_CONSISTENCY_GEMINI_MODEL`** | `MODEL_ID` | Gemini model used in the Character Consistency workflow. |
