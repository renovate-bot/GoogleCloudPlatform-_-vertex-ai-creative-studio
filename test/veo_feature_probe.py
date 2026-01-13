# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
import json
import traceback
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
OUTPUT_GCS = os.getenv("VIDEO_BUCKET", f"{PROJECT_ID}-assets/videos")

MODELS = [
    "veo-3.1-generate-001",
    "veo-3.1-fast-generate-001",
    "veo-3.1-generate-preview",
    "veo-3.1-fast-generate-preview",
    "veo-2.0-generate-exp",
]

SCENARIOS = [
    {"name": "T2V 1080p", "config": {"aspect_ratio": "16:9", "resolution": "1080p"}, "type": "t2v"},
    {"name": "R2V Asset 16:9", "config": {"aspect_ratio": "16:9", "resolution": "1080p"}, "type": "r2v_asset"},
    {"name": "R2V Style 16:9", "config": {"aspect_ratio": "16:9", "resolution": "1080p"}, "type": "r2v_style"},
    {"name": "Interpolation", "config": {"aspect_ratio": "16:9", "resolution": "1080p"}, "type": "interpolation"},
]

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

def probe_capability(model_id, scenario):
    print(f"Probing {model_id} with {scenario['name']}...")
    
    config_args = {
        "number_of_videos": 1,
        "duration_seconds": 4, 
        "output_gcs_uri": f"gs://{OUTPUT_GCS}",
        "enhance_prompt": True,
        **scenario['config']
    }
    
    image_input = None
    video_input = None
    
    if scenario['type'] == 'i2v':
        image_input = types.Image(
            gcs_uri="gs://cloud-samples-data/generative-ai/image/flowers.png",
            mime_type="image/png"
        )
    elif scenario['type'] == 'r2v_asset':
        config_args["reference_images"] = [
            types.VideoGenerationReferenceImage(
                image=types.Image(
                    gcs_uri="gs://cloud-samples-data/generative-ai/image/flowers.png",
                    mime_type="image/png"
                ),
                reference_type="asset"
            )
        ]
    elif scenario['type'] == 'r2v_3_assets':
        config_args["reference_images"] = [
            types.VideoGenerationReferenceImage(
                image=types.Image(
                    gcs_uri="gs://cloud-samples-data/generative-ai/image/flowers.png",
                    mime_type="image/png"
                ),
                reference_type="asset"
            ),
            types.VideoGenerationReferenceImage(
                image=types.Image(
                    gcs_uri="gs://cloud-samples-data/generative-ai/image/daisy.jpg",
                    mime_type="image/jpeg"
                ),
                reference_type="asset"
            ),
            types.VideoGenerationReferenceImage(
                image=types.Image(
                    gcs_uri="gs://cloud-samples-data/generative-ai/image/small-dog-pink.jpg",
                    mime_type="image/jpeg"
                ),
                reference_type="asset"
            )
        ]
    elif scenario['type'] == 'r2v_style':
        config_args["reference_images"] = [
            types.VideoGenerationReferenceImage(
                image=types.Image(
                    gcs_uri="gs://cloud-samples-data/generative-ai/image/flowers.png",
                    mime_type="image/png"
                ),
                reference_type="style"
            )
        ]
    elif scenario['type'] == 'interpolation':
        image_input = types.Image(
            gcs_uri="gs://cloud-samples-data/generative-ai/image/flowers.png",
            mime_type="image/png"
        )
        config_args["last_frame"] = types.Image(
            gcs_uri="gs://cloud-samples-data/generative-ai/image/daisy.jpg",
            mime_type="image/jpeg"
        )

    try:
        operation = client.models.generate_videos(
            model=model_id,
            prompt="a simple test video",
            config=types.GenerateVideosConfig(**config_args),
            image=image_input,
            video=video_input
        )
        return "✅ Success"
    except Exception as e:
        err_msg = str(e)
        if "allowlisted" in err_msg:
            if "4k" in err_msg.lower(): return "🚫 4K Block"
            if "reference to video" in err_msg.lower(): return "🚫 R2V Block"
            return "🚫 Allowlist Block"
        if "not supported" in err_msg.lower():
            return "❌ Unsupported"
        return f"❌ Error: {err_msg[:30]}..."

def main():
    results = {}
    detailed_errors = []
    
    for model in MODELS:
        results[model] = {}
        for scenario in SCENARIOS:
            status = probe_capability(model, scenario)
            results[model][scenario['name']] = status
            if "Error" in status or "Block" in status:
                # We could capture more details here if needed
                pass
            time.sleep(1)

    # Generate Markdown Table
    headers = ["Model"] + [scenario['name'] for scenario in SCENARIOS]
    print("\n### Expanded Veo Capability Matrix\n")
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    print(header_row)
    print(sep_row)
    
    for model in MODELS:
        row = [model]
        for scenario in SCENARIOS:
            row.append(results[model][scenario['name']])
        print("| " + " | ".join(row) + " |")

if __name__ == "__main__":
    main()