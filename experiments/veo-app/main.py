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
"""Main Mesop App."""

import inspect
import os
import uuid

import mesop as me
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from common.auth import set_user_identity_and_session
from components.page_scaffold import page_scaffold
from pages.character_consistency import character_consistency_page_content
from pages.config import config_page_contents
from pages.edit_images import content as edit_images_content
from pages.home import home_page_content
from pages.imagen import imagen_content
from pages.library import library_content
from pages.lyria import lyria_content
from pages.portraits import motion_portraits_content
from pages.recontextualize import recontextualize
from pages.test_uploader import test_uploader_page
from pages.veo import veo_content
from pages.vto import vto
from state.state import AppState


class UserInfo(BaseModel):
    email: str | None
    agent: str | None


# FastAPI server with Mesop
app = FastAPI()
router = APIRouter()
app.include_router(router)


@app.middleware("http")
async def add_custom_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self';"
    )
    return response


# from pages.gemini2 import gemini_page_content


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


@me.page(
    path="/home",
    title="GenMedia Creative Studio - v.next",
    on_load=on_load,
)
def home_page():
    """Main Page."""
    state = me.state(AppState)
    with page_scaffold():  # pylint: disable=not-context-manager
        home_page_content(state)


@me.page(
    path="/veo",
    title="Veo - GenMedia Creative Studio",
    on_load=on_load,
)
def veo_page():
    """Veo Page."""
    veo_content(me.state(AppState))


@me.page(
    path="/motion_portraits",
    title="Motion Portraits - GenMedia Creative Studio",
    on_load=on_load,
)
def motion_portrait_page():
    """Motion Portrait Page."""
    motion_portraits_content(me.state(AppState))


@me.page(
    path="/lyria",
    title="Lyria - GenMedia Creative Studio",
    on_load=on_load,
)
def lyria_page():
    """Lyria Page."""
    lyria_content(me.state(AppState))


@me.page(
    path="/config",
    title="GenMedia Creative Studio - Config",
    on_load=on_load,
)
def config_page():
    """Config Page."""
    config_page_contents(me.state(AppState))


@me.page(
    path="/imagen",
    title="GenMedia Creative Studio - Imagen",
    on_load=on_load,
    security_policy=me.SecurityPolicy(
        allowed_script_srcs=[
            "https://cdn.jsdelivr.net",
        ],
        dangerously_disable_trusted_types=True,
    ),
)
def imagen_page():
    """Imagen Page."""
    imagen_content(me.state(AppState))


@me.page(
    path="/library",
    title="GenMedia Creative Studio - Library",
    on_load=on_load,
)
def library_page():
    """Library Page."""
    library_content(me.state(AppState))


@me.page(
    path="/edit_images",
    title="GenMedia Creative Studio - Edit Images",
    on_load=on_load,
)
def edit_images_page():
    """Edit Images Page."""
    edit_images_content(me.state(AppState))


@me.page(
    path="/vto",
    title="GenMedia Creative Studio - Virtual Try-On",
    on_load=on_load,
)
def vto_page():
    """VTO Page"""
    vto()


@me.page(
    path="/recontextualize",
    title="GenMedia Creative Studio - Product in Scene",
    on_load=on_load,
)
def recontextualize_page():
    """Recontextualize Page"""
    recontextualize()


@me.page(
    path="/character_consistency",
    title="GenMedia Creative Studio - Character Consistency",
    on_load=on_load,
)
def character_consistency_page():
    """Character Consistency Page"""
    character_consistency_page_content()


from common.storage import get_or_create_session


@app.get("/__/auth/")
def auth_proxy(request: Request) -> RedirectResponse:
    print(f"DEBUG: Cookies received in auth_proxy: {request.cookies}")
    user_email = request.headers.get(
        "X-Goog-Authenticated-User-Email", "anonymous@google.com"
    )
    if ":" in user_email:
        user_email = user_email.split(":")[-1]

    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    get_or_create_session(session_id, user_email)

    app.state.user_email = user_email
    app.state.session_id = session_id

    response = RedirectResponse(url="/home")
    response.set_cookie(
        key="session_id", value=session_id, httponly=True, samesite="Lax"
    )
    return response


@app.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/__/auth/")


# Use this to mount the static files for the Mesop app
app.mount(
    "/static",
    StaticFiles(
        directory=os.path.join(
            os.path.dirname(inspect.getfile(me)),
            "web",
            "src",
            "app",
            "prod",
            "web_package",
        )
    ),
    name="static",
)

app.mount(
    "/",
    WSGIMiddleware(
        me.create_wsgi_app(debug_mode=os.environ.get("DEBUG_MODE", "") == "true")
    ),
)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        reload_includes=["*.py", "*.js"],
        timeout_graceful_shutdown=0,
    )
