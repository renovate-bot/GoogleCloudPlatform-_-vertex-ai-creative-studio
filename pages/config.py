# Copyright 2024 Google LLC
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

"""Configuration page for the application."""

from dataclasses import dataclass, field
from typing import Callable

import mesop as me
import pandas as pd

from common.prompt_template_service import prompt_template_service
from components.header import header
from components.page_scaffold import page_frame, page_scaffold
from components.prompt_template_detail_dialog.prompt_template_detail_dialog import (
    prompt_template_detail_dialog,
)
from config.default import Default
from state.state import AppState


# Adapted from components/tab_nav.py and pages/pixie_compositor.py
@dataclass
class Tab:
    key: str
    label: str
    icon: str | None = None


def on_tab_change(e: me.ClickEvent):
    state = me.state(PageState)
    state.active_tab = e.key
    yield


@me.component
def _tab_group(tabs: list[Tab], on_tab_click: Callable, selected_tab_key: str):
    with me.box(
        style=me.Style(
            display="flex",
            border=me.Border(
                bottom=me.BorderSide(
                    width=1, style="solid", color=me.theme_var("outline-variant")
                )
            ),
        )
    ):
        for tab in tabs:
            is_selected = tab.key == selected_tab_key
            with me.box(
                key=tab.key,
                on_click=on_tab_click,
                style=_make_tab_style(is_selected),
            ):
                if tab.icon:
                    me.icon(tab.icon)
                me.text(tab.label)


def _make_tab_style(selected: bool) -> me.Style:
    style = me.Style(
        align_items="center",
        color=me.theme_var("on-surface"),
        display="flex",
        cursor="pointer",
        flex_grow=1,
        justify_content="center",
        line_height=1,
        font_size=14,
        font_weight="medium",
        padding=me.Padding.all(16),
        text_align="center",
        gap=5,
    )
    if selected:
        style.background = me.theme_var("surface-container")
        style.border = me.Border(
            bottom=me.BorderSide(width=2, style="solid", color=me.theme_var("primary"))
        )
        style.cursor = "default"
    return style


@me.stateclass
class PageState:
    templates: list[dict] = field(default_factory=list)
    is_loading: bool = False
    active_tab: str = "details"
    show_template_dialog: bool = False
    selected_template_key: str | None = None


def on_load(e: me.LoadEvent):
    """Loads all prompt templates on page load."""
    state = me.state(PageState)
    state.is_loading = True
    yield

    all_templates = prompt_template_service.load_all_templates()
    state.templates = sorted(
        [t.model_dump() for t in all_templates],
        key=lambda x: (x["category"], x["label"]),
    )
    state.is_loading = False
    yield


def on_row_click(e: me.ClickEvent):
    state = me.state(PageState)
    # The key of the box is the template key
    state.selected_template_key = e.key
    state.show_template_dialog = True
    yield


def on_close_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.show_template_dialog = False
    state.selected_template_key = None
    yield


def on_update_template(template_id: str, updates: dict):
    state = me.state(PageState)
    try:
        prompt_template_service.update_template(template_id, updates)
        # Reload all templates to reflect the change
        all_templates = prompt_template_service.load_all_templates()
        state.templates = sorted(
            [t.model_dump() for t in all_templates],
            key=lambda x: (x["category"], x["label"]),
        )
        # Close the dialog
        state.show_template_dialog = False
        state.selected_template_key = None
    except Exception as e:
        print(f"Error updating template: {e}")
        # Optionally, show an error dialog
    yield


@me.page(path="/config", title="Configuration", on_load=on_load)
def page():
    """Renders the configuration page."""
    state = me.state(PageState)
    app_state = me.state(AppState)

    # Find the template to display at render time
    selected_template = None
    if state.selected_template_key:
        selected_template = next(
            (t for t in state.templates if t["key"] == state.selected_template_key),
            None,
        )

    with page_scaffold(page_name="config"):
        with page_frame():
            header("Configuration", icon="settings")

            tabs = [
                Tab(key="details", label="Config Details", icon="list_alt"),
                Tab(key="templates", label="Prompt Templates", icon="pattern"),
            ]
            _tab_group(
                tabs=tabs,
                on_tab_click=on_tab_change,
                selected_tab_key=state.active_tab,
            )

            if state.active_tab == "details":
                _render_config_details_tab(app_state=app_state)
            elif state.active_tab == "templates":
                _render_prompt_templates_list(app_state=app_state)

            # Conditionally render the dialog, passing the derived template dict
            if state.show_template_dialog and selected_template:
                prompt_template_detail_dialog(
                    template=selected_template,
                    is_open=state.show_template_dialog,
                    is_editable=selected_template["attribution"]
                    == app_state.user_email,
                    on_close=on_close_dialog,
                    on_update=on_update_template,
                )


def get_config_table(app_state: AppState):
    """Construct a table of the Defaults, including optional new attributes"""
    config_data = {
        "Config": [
            "Username",
            "Vertex AI Enabled",
            "Project ID",
            "Location",
            "Default Model ID",
            "GenMedia Bucket",
            "GenMedia Firestore DB / Collection",
            "Veo Project ID",
            "Veo Model ID",
            "Veo Experimental Model ID",
        ],
        "Value": [
            app_state.user_email if app_state.user_email else "Anonymous",
            str(Default.INIT_VERTEX),
            Default.PROJECT_ID,
            Default.LOCATION,
            Default.MODEL_ID,
            f"gs://{Default.GENMEDIA_BUCKET}" if Default.GENMEDIA_BUCKET else "Not Set",
            f"{Default.GENMEDIA_FIREBASE_DB} / {Default.GENMEDIA_COLLECTION_NAME}"
            if Default.GENMEDIA_FIREBASE_DB and Default.GENMEDIA_COLLECTION_NAME
            else "Not Set",
            Default.VEO_PROJECT_ID,
            Default.VEO_MODEL_ID,
            Default.VEO_EXP_MODEL_ID,
        ],
    }

    if hasattr(Default, "LYRIA_PROJECT_ID"):
        lyria_project_id_val = getattr(Default, "LYRIA_PROJECT_ID")
        if lyria_project_id_val is not None and lyria_project_id_val != "":
            config_data["Config"].append("Lyria Project ID")
            config_data["Value"].append(lyria_project_id_val)
        config_data["Config"].append("Lyria Model Version")
        config_data["Value"].append(Default.LYRIA_MODEL_VERSION)

    config_data["Config"].append("Application Verison")
    config_data["Value"].append(f"{Default.VERSION} {Default.APP_ENV}")

    df = pd.DataFrame(data=config_data)
    return df


@me.component
def _render_config_details_tab(app_state: AppState):
    with me.box(style=me.Style(padding=me.Padding(top=24, left=24, right=24))):
        me.table(
            get_config_table(app_state=app_state),
            header=me.TableHeader(sticky=True),
            columns={
                "Config": me.TableColumn(sticky=True),
                "Value": me.TableColumn(sticky=True),
            },
        )


@me.component
def _render_prompt_templates_list(app_state: AppState):
    """Renders the list of prompt templates."""
    state = me.state(PageState)

    if state.is_loading:
        me.progress_spinner()
        return

    with me.box(style=me.Style(padding=me.Padding(top=24, left=24, right=24))):
        me.text("Prompt Templates", type="headline-5")
        with me.box(style=me.Style(margin=me.Margin(top=16))):
            # Header Row
            with me.box(
                style=me.Style(
                    display="grid",
                    grid_template_columns="2fr 2fr 1fr 1fr 2fr 1fr",
                    gap=16,
                    padding=me.Padding(bottom=8),
                    border=me.Border(
                        bottom=me.BorderSide(
                            width=1, style="solid", color=me.theme_var("outline")
                        )
                    ),
                )
            ):
                me.text("Label", style=me.Style(font_weight="bold"))
                me.text("Key", style=me.Style(font_weight="bold"))
                me.text("Category", style=me.Style(font_weight="bold"))
                me.text("Type", style=me.Style(font_weight="bold"))
                me.text("Attribution", style=me.Style(font_weight="bold"))
                me.text("Actions", style=me.Style(font_weight="bold"))

            # Data Rows
            for template in state.templates:
                with me.box(
                    key=template["key"],
                    on_click=on_row_click,
                    style=me.Style(
                        display="grid",
                        grid_template_columns="2fr 2fr 1fr 1fr 2fr 1fr",
                        gap=16,
                        padding=me.Padding(top=8, bottom=8),
                        border=me.Border(
                            bottom=me.BorderSide(
                                width=1,
                                style="solid",
                                color=me.theme_var("outline-variant"),
                            )
                        ),
                        align_items="center",
                        cursor="pointer",
                    ),
                ):
                    me.text(template["label"])
                    me.text(template["key"])
                    me.text(template["category"])
                    me.text(template["template_type"])
                    me.text(template["attribution"])
                    with me.content_button(
                        type="icon",
                        disabled=template["is_default"],
                        # on_click=... # To be implemented later
                    ):
                        me.icon("delete")