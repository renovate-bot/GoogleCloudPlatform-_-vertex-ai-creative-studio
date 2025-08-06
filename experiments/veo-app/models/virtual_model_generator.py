import json
import random
from pathlib import Path

# The default prompt, used as a fallback if the user's prompt is invalid.
DEFAULT_PROMPT = "A full-length studio shot of {gender} model with {silhouette}, posed for a virtual try-on application. The model has an {MST} skin tone. Lighting is bright and even, highlighting the model's form without harsh shadows. The model is {variant}. The focus is sharp and clear, capturing the details of clothing textures and fit, suitable for e-commerce apparel display."

class VirtualModelGenerator:
    """
    A class to generate prompts for creating virtual models by substituting placeholders.
    """

    def __init__(self, base_prompt: str):
        """
        Initializes the VirtualModelGenerator with a base prompt.

        Args:
            base_prompt: The starting prompt to build upon, containing placeholders.
        """
        self.base_prompt = base_prompt
        self.values = {}
        self._load_options()

    def _load_options(self):
        """Loads the generation options from the JSON config file."""
        config_path = Path(__file__).parent.parent / "config/virtual_model_options.json"
        with open(config_path, "r") as f:
            self.options = json.load(f)

    def set_value(self, key: str, value: str):
        """Sets a value for a given placeholder key."""
        self.values[key] = value
        return self

    def randomize_all(self):
        """Sets a random value for all major placeholders."""
        self.set_value("gender", random.choice(self.options["genders"])["prompt_fragment"])
        self.set_value("silhouette", random.choice(self.options["silhouette_presets"])["prompt_fragment"])
        self.set_value("MST", random.choice(self.options["MST"]))
        return self

    def _validate_prompt(self, prompt_str: str) -> bool:
        """Checks if the prompt string contains all required placeholders."""
        required_placeholders = ["{gender}", "{MST}", "{silhouette}", "{variant}"]
        return all(p in prompt_str for p in required_placeholders)

    def build_prompt(self) -> str:
        """
        Builds the final prompt string by substituting placeholders.
        If the base prompt is invalid, it reverts to the default.
        """
        prompt_template = self.base_prompt
        if not self._validate_prompt(prompt_template):
            print(f"Warning: Invalid prompt template: '{prompt_template}'. Reverting to default.")
            prompt_template = DEFAULT_PROMPT

        final_prompt = prompt_template
        for key, value in self.values.items():
            final_prompt = final_prompt.replace(f"{{{key}}}", value)
        
        return final_prompt