import random

import mesop as me
import mesop.labs as mel
import json
from pathlib import Path
from dataclasses import field

from models.image_models import generate_virtual_models
from models.virtual_model_generator import VirtualModelGenerator, DEFAULT_PROMPT

@me.stateclass
class PageState:
    base_prompt: str = DEFAULT_PROMPT
    selected_gender_name: str = "Feminine-presenting"
    selected_silhouette_name: str = "Linear & Balanced"
    selected_mst: str = "MST-5"
    selected_mst_orb_url: str = "https://google-ai-skin-tone-research.imgix.net/orbs/monk-05.png"
    generated_images: list[list[str]] = field(default_factory=list)
    generated_description: str = ""
    loading: bool = False

    # Load options once
    _options: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        config_path = Path(__file__).parent.parent / "config/virtual_model_options.json"
        with open(config_path, "r") as f:
            self._options = json.load(f)

@me.page(
    path="/test_vto_prompt_generator",
    title="VTO Model Composite Card Generator Test Page",
    security_policy=me.SecurityPolicy(
        dangerously_disable_trusted_types=True
    )
)
def page():
    state = me.state(PageState)
    with me.box(style=me.Style(padding=me.Padding.all(20))):
        me.text("Virtual Model Composite Card Generator Matrix", type="headline-5")
        me.text("Generate a matrix of virtual models with different attributes.", style=me.Style(margin=me.Margin(bottom=20)))

        # --- CONTROLS ---
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=20, margin=me.Margin(bottom=20), align_items="flex-start")):
            with me.box(style=me.Style(flex_grow=1)):
                me.textarea(
                    label="Base Prompt",
                    value=state.base_prompt,
                    on_input=on_base_prompt_input,
                    rows=5,
                    style=me.Style(width="100%")
                )
            with me.box(style=me.Style(display="flex", flex_direction="column", gap=10)):
                me.select(
                    label="Gender Presentation",
                    options=[me.SelectOption(label=g["name"], value=g["name"]) for g in state._options.get("genders", [])],
                    value=state.selected_gender_name,
                    on_selection_change=on_gender_select
                )
            with me.box(style=me.Style(display="flex", flex_direction="column", gap=10)):
                me.select(
                    label="Monk Skin Tone",
                    options=[me.SelectOption(label=f'{mst["name"]} ({mst["hex"]})', value=mst["name"]) for mst in state._options.get("MST", [])],
                    value=state.selected_mst,
                    on_selection_change=on_mst_select
                )
                if state.selected_mst_orb_url:
                    with me.box(style=me.Style(display="flex", justify_content="center")):
                        me.image(src=state.selected_mst_orb_url, style=me.Style(width=50, height=50))

        # --- SILHOUETTE PRESETS ---
        me.text("Select a Silhouette Preset", type="headline-6", style=me.Style(margin=me.Margin(bottom=10)))
        with me.box(style=me.Style(display="grid", grid_template_columns="repeat(auto-fill, minmax(250px, 1fr))", gap=15)):
            for preset in state._options.get("silhouette_presets", []):
                with me.box(
                    key=preset["name"],
                    on_click=on_select_silhouette,
                    style=me.Style(
                        border=me.Border.all(me.BorderSide(width=2, style="solid", color=me.theme_var("primary") if state.selected_silhouette_name == preset["name"] else me.theme_var("outline"))),
                        background=me.theme_var("primary-container") if state.selected_silhouette_name == preset["name"] else "transparent",
                        padding=me.Padding.all(15),
                        border_radius=12,
                        cursor="pointer"
                    )
                ):
                    me.text(preset["name"], type="subtitle-1")
                    me.text(preset["description"], type="body-2")

        with me.box(style=me.Style(display="flex", gap=10, margin=me.Margin(top=20))):
            me.button("Generate Matrix", on_click=on_click_generate_matrix, type="raised")
            me.button("I'm Feeling Lucky", on_click=on_click_randomize, type="flat")
            me.button("Generate Description", on_click=on_click_generate_description, type="flat", disabled=not state.generated_images)

        # --- GENERATED DESCRIPTION ---
        if state.generated_description:
            with me.box(style=me.Style(margin=me.Margin(top=20), background=me.theme_var("surface-container-lowest"), padding=me.Padding.all(15), border_radius=8)):
                me.text("Generated Description", type="subtitle-2")
                me.text(state.generated_description)


        # --- IMAGE MATRIX ---
        if state.loading:
            me.progress_spinner()
        elif state.generated_images:
            me.text("Generated Models", type="headline-6", style=me.Style(margin=me.Margin(top=20, bottom=10)))
            with me.box(style=me.Style(display="grid", grid_template_columns="repeat(3, 1fr)", gap=10)):
                for image_row in state.generated_images:
                    for image_url in image_row:
                        me.image(src=image_url.replace("gs://", "https://storage.mtls.cloud.google.com/"), style=me.Style(width="100%"))

def on_base_prompt_input(e: me.InputEvent):
    me.state(PageState).base_prompt = e.value

def on_gender_select(e: me.SelectSelectionChangeEvent):
    me.state(PageState).selected_gender_name = e.value

def on_select_silhouette(e: me.ClickEvent):
    me.state(PageState).selected_silhouette_name = e.key

def on_mst_select(e: me.SelectSelectionChangeEvent):
    state = me.state(PageState)
    state.selected_mst = e.value
    # MST-1 -> 01, MST-10 -> 10
    mst_number = e.value.split("-")[-1].zfill(2)
    state.selected_mst_orb_url = f"https://google-ai-skin-tone-research.imgix.net/orbs/monk-{mst_number}.png"

def on_click_randomize(e: me.ClickEvent):
    state = me.state(PageState)
    state.selected_gender_name = random.choice(state._options.get("genders", []))["name"]
    state.selected_silhouette_name = random.choice(state._options.get("silhouette_presets", []))["name"]
    selected_mst_obj = random.choice(state._options.get("MST", []))
    state.selected_mst = selected_mst_obj["name"]
    mst_number = selected_mst_obj["name"].split("-")[-1].zfill(2)
    state.selected_mst_orb_url = f"https://google-ai-skin-tone-research.imgix.net/orbs/monk-{mst_number}.png"
    yield

def on_click_generate_matrix(e: me.ClickEvent):
    state = me.state(PageState)
    state.loading = True
    state.generated_images = []
    state.generated_description = ""
    yield

    # Find the selected gender and silhouette objects to get their prompt_fragments
    selected_gender_obj = next((g for g in state._options["genders"] if g["name"] == state.selected_gender_name), None)
    selected_silhouette_obj = next((s for s in state._options["silhouette_presets"] if s["name"] == state.selected_silhouette_name), None)
    selected_mst_obj = next((m for m in state._options["MST"] if m["name"] == state.selected_mst), None)

    if not selected_gender_obj or not selected_silhouette_obj or not selected_mst_obj:
        print("Error: Could not find selected gender or silhouette.")
        state.loading = False
        yield
        return

    matrix = []
    for variant in state._options.get("variants", []):
        generator = VirtualModelGenerator(state.base_prompt)
        generator.set_value("gender", selected_gender_obj["prompt_fragment"])
        generator.set_value("silhouette", selected_silhouette_obj["prompt_fragment"])
        generator.set_value("MST", selected_mst_obj["prompt_fragment"])
        generator.set_value("variant", variant["prompt_fragment"])

        prompt = generator.build_prompt()
        print(f"Generating images for prompt: {prompt}")
        image_urls = generate_virtual_models(prompt=prompt, num_images=3)
        matrix.append(image_urls)

    state.generated_images = matrix
    state.loading = False
    yield

def on_click_generate_description(e: me.ClickEvent):
    state = me.state(PageState)
    
    selected_gender_obj = next((g for g in state._options["genders"] if g["name"] == state.selected_gender_name), {})
    selected_silhouette_obj = next((s for s in state._options["silhouette_presets"] if s["name"] == state.selected_silhouette_name), {})

    description = (
        f"A {selected_gender_obj.get('name', 'person')} with an {state.selected_mst} complexion. "
        f"The model has a {selected_silhouette_obj.get('name', 'defined')} silhouette: {selected_silhouette_obj.get('description', '')}"
    )
    state.generated_description = description
    yield
