# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Application factory for creating the FastAPI app and on_load handler."""

import mesop as me
from fastapi import FastAPI

from state.state import AppState


def create_app():
    """Create the FastAPI app instance."""
    app = FastAPI()
    return app


def create_on_load_handler(app: FastAPI):
    """Create the on_load event handler."""

    def on_load(e: me.LoadEvent):  # pylint: disable=unused-argument
        """On load event."""
        s = me.state(AppState)
        if hasattr(app, "state") and hasattr(app.state, "user_email"):
            s.user_email = app.state.user_email
            s.session_id = app.state.session_id
            print(f"DEBUG: User Email = {s.user_email}, Session ID = {s.session_id}")
        else:
            # Fallback if middleware hasn't run (e.g., direct page load in dev)
            s.user_email = "anonymous@google.com"
            s.session_id = ""

        if s.theme_mode:
            if s.theme_mode == "light":
                me.set_theme_mode("light")
            elif s.theme_mode == "dark":
                me.set_theme_mode("dark")
        else:
            me.set_theme_mode("system")
            s.theme_mode = me.theme_brightness()

    return on_load


app = create_app()
on_load = create_on_load_handler(app)
