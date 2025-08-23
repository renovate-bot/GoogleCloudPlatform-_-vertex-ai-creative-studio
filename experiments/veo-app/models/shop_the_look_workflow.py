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

"""Workflow for the Shop the Look page."""
import csv
import datetime
import mesop as me
from google.cloud import firestore

from common.storage import (
    download_from_gcs_as_string,
    store_to_gcs,
)
from config.default import Default
from config.firebase_config import FirebaseClient
from models.shop_the_look_models import (
    CatalogRecord,
    ModelRecord,
)
from state.state import AppState
from state.shop_the_look_state import PageState

config = Default()
db = FirebaseClient(database_id=config.GENMEDIA_FIREBASE_DB).get_client()


def load_model_data(limit: int = 50):
    try:
        app_state = me.state(AppState)
        media_ref = db.collection(config.GENMEDIA_VTO_MODEL_COLLECTION_NAME)

        query = media_ref.where("upload_user", "in", ["everyone", app_state.user_email])

        models = []
        for doc in query.stream():
            model_data = doc.to_dict()
            models.append(ModelRecord(**model_data))

        return models
    except Exception as e:
        print(f"Error fetching models: {e}")


def load_article_data(limit: int = 50):
    state = me.state(PageState)
    app_state = me.state(AppState)
    media_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME)
    query = media_ref.where("upload_user", "in", ["everyone", app_state.user_email])

    articles = []
    for doc in query.stream():
        article_data = doc.to_dict()
        articles.append(CatalogRecord(**article_data))

    articles = sorted(articles, key=lambda article: article.article_type)

    state.articles = articles


def load_look_data(limit: int = 50):
    state = me.state(PageState)
    media_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME).order_by(
        "look_id", direction=firestore.Query.ASCENDING
    )
    looks = []
    for doc in media_ref.stream():
        catalog_data = doc.to_dict()
        record = CatalogRecord(**catalog_data)
        record.clothing_image = (f"gs://{config.GENMEDIA_BUCKET}/{record.item_id}",)
        looks.append(record)

    looks.sort(key=lambda item: (item.look_id, item.try_on_order))
    looks = list(
        filter(
            lambda look: look.article_type not in ("sunglasses", "watch", "hat"),
            looks,
        )
    )

    return looks


def get_selected_look():
    state = me.state(PageState)
    selected_look_data = list(
        filter(lambda catalogrecord: catalogrecord.selected, state.articles)
    )
    return selected_look_data


def get_model_records(model_id):
    state = me.state(PageState)
    model_records = []
    for m in state.models:
        if m.model_id == model_id:
            model_records.append(m)
    return model_records

def store_model_data(file_path):
    state = me.state(PageState)
    app_state = me.state(AppState)
    current_datetime = datetime.datetime.now()
    file_name_only = file_path.split("/")[-1]
    doc_ref = db.collection(config.GENMEDIA_VTO_MODEL_COLLECTION_NAME)

    upload_user = "everyone" if state.upload_everyone else app_state.user_email

    new_doc_data = {
        "model_group": "0",
        "model_id": file_name_only,
        "model_image": file_path,
        "timestamp": current_datetime,
        "upload_user": upload_user,
    }

    update_time, doc_ref = doc_ref.add(new_doc_data)


def store_article_data(file_path, article_category):
    state = me.state(PageState)
    app_state = me.state(AppState)
    current_datetime = datetime.datetime.now()
    file_name_only = file_path.split("/")[-1]
    doc_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME)

    upload_user = "everyone" if state.upload_everyone else app_state.user_email

    new_doc_data = {
        "item_id": file_name_only,
        "article_type": article_category,
        "model_group": "0",
        "timestamp": current_datetime,
        "ai_description": None,
        "selected": False,
        "available_to_select": True,
        "clothing_image": file_path,
        "upload_user": upload_user,
    }

    update_time, doc_ref = doc_ref.add(new_doc_data)

def article_on_delete(e: me.ClickEvent):
    state = me.state(PageState)
    file_to_delete = e.key.split("/")[-1]
    print(f"deleting {file_to_delete}")
    state.current_status = f"Deleting article {file_to_delete}"
    try:
        doc_ref = db.collection(config.GENMEDIA_VTO_CATALOG_COLLECTION_NAME).document(
            file_to_delete
        )

        doc_ref.delete()
        load_article_data()
        state.current_status = ""
        yield
    except:
        print(f"Model data  delete failure: {file_to_delete} cannot be stored")


def model_on_delete(e: me.ClickEvent):
    state = me.state(PageState)
    file_to_delete = e.key.split("/")[-1]
    print(f"deleting {file_to_delete}")
    state.current_status = f"Deleting model {file_to_delete}"
    try:
        doc_ref = db.collection(config.GENMEDIA_VTO_MODEL_COLLECTION_NAME).document(
            file_to_delete
        )

        doc_ref.delete()
        state.models = load_model_data()
        state.current_status = ""
        yield
    except:
        print(f"Model data  delete failure: {file_to_delete} cannot be stored")