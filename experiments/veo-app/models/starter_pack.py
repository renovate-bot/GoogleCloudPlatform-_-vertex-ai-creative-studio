"""Backend logic for the Starter Pack page."""

import random
import json
from pathlib import Path

import models.gemini as gemini
from models.image_models import generate_virtual_models
from models.virtual_model_generator import VirtualModelGenerator, DEFAULT_PROMPT

def generate_starter_pack_from_look(look_image_uri: str) -> str:
    """Generates a starter pack from a look image."""
    prompt = "Analyze the image to extract the featured products for a mood board. Lay out only the articles / items, and not the person."
    generated_images, _ = gemini.generate_image_from_prompt_and_images(
        prompt=prompt, images=[look_image_uri]
    )
    if generated_images:
        return generated_images[0]
    return ""

def generate_look_from_starter_pack(
    starter_pack_uri: str, model_image_uri: str
) -> str:
    """Generates a look from a starter pack and model image."""
    prompt = "Try this ensemble on the given model."
    generated_images, _ = gemini.generate_image_from_prompt_and_images(
        prompt=prompt, images=[starter_pack_uri, model_image_uri]
    )
    if generated_images:
        return generated_images[0]
    return ""

def generate_virtual_model() -> str:
    """Generates a virtual model image."""
    config_path = Path(__file__).parent.parent / "config/virtual_model_options.json"
    with open(config_path, "r") as f:
        options = json.load(f)

    selected_gender_obj = random.choice(options.get("genders", []))
    selected_silhouette_obj = random.choice(options.get("silhouette_presets", []))
    selected_mst_obj = random.choice(options.get("MST", []))
    selected_variant_obj = random.choice(options.get("variants", []))

    generator = VirtualModelGenerator(DEFAULT_PROMPT)
    generator.set_value("gender", selected_gender_obj["prompt_fragment"])
    generator.set_value("silhouette", selected_silhouette_obj["prompt_fragment"])
    generator.set_value("MST", selected_mst_obj["prompt_fragment"])
    generator.set_value("variant", selected_variant_obj["prompt_fragment"])
    prompt = generator.build_prompt()

    image_urls = generate_virtual_models(prompt=prompt, num_images=1)
    if image_urls:
        return image_urls[0]
    return ""