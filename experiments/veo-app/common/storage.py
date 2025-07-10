# Copyright 2025 Google LLC
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

import base64
from functools import lru_cache

from google.cloud import aiplatform
from google.cloud import storage
import vertexai

from config.default import Default

cfg = Default()

def store_to_gcs(
    folder: str,
    file_name: str,
    mime_type: str,
    contents: str | bytes,
    decode: bool = False,
    bucket_name: str | None = None,
):
    """store contents to GCS"""
    actual_bucket_name = bucket_name if bucket_name else cfg.GENMEDIA_BUCKET
    if not actual_bucket_name:
        raise ValueError(
            "GCS bucket name is not configured. Please set GENMEDIA_BUCKET environment variable or provide bucket_name."
        )
    print(f"store_to_gcs: Target project {cfg.PROJECT_ID}, target bucket {actual_bucket_name}")
    client = storage.Client(project=cfg.PROJECT_ID)
    bucket = client.get_bucket(actual_bucket_name)
    destination_blob_name = f"{folder}/{file_name}"
    print(f"store_to_gcs: Destination {destination_blob_name}")
    blob = bucket.blob(destination_blob_name)
    if decode:
        contents_bytes = base64.b64decode(contents)
        blob.upload_from_string(contents_bytes, content_type=mime_type)
    elif isinstance(contents, bytes):
        blob.upload_from_string(contents, content_type=mime_type)
    else:
        blob.upload_from_string(contents, content_type=mime_type)
    return f"gs://{actual_bucket_name}/{destination_blob_name}"  # Return full gsutil URI
