"""Service for managing Prompt Templates."""

import json
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from common.metadata import db


class PromptTemplate(BaseModel):
    """Data model for a single Prompt Template."""

    id: Optional[str] = None
    key: str
    label: str
    prompt: str
    category: str
    template_type: Literal["image", "text"]
    attribution: str
    references: Optional[List[str]] = Field(default_factory=list)
    is_default: bool = False


class PromptTemplateService:
    """Service for managing Prompt Templates."""

    def __init__(self, collection_name: str = "prompt_templates"):
        self.collection_name = collection_name

    def _load_from_json(self, path: str, template_type: str) -> list[PromptTemplate]:
        """Loads a list of default templates from a JSON file."""
        templates = []
        try:
            with open(path, "r") as f:
                data = json.load(f)
                for item in data:
                    # Ensure the template matches the expected type for this context
                    if item.get("template_type") == template_type:
                        templates.append(PromptTemplate(**item, is_default=True))
        except FileNotFoundError:
            print(f"Warning: Prompt template file not found at {path}")
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {path}")
        except Exception as e:
            print(
                f"Warning: An unexpected error occurred loading templates from {path}: {e}"
            )
        return templates

    def load_templates(
        self, config_path: str, template_type: str
    ) -> list[PromptTemplate]:
        """Loads default templates from a JSON file and combines them with user-created templates from Firestore."""
        templates = self._load_from_json(config_path, template_type)

        # Add user-created templates from firestore
        if db:
            try:
                query = (
                    db.collection("prompt_templates")
                    .where("template_type", "==", template_type)
                    .order_by("category")
                    .order_by("label")
                )
                for doc in query.stream():
                    try:
                        templates.append(PromptTemplate(**doc.to_dict(), id=doc.id))
                    except Exception as e:
                        print(
                            f"Warning: Skipping invalid prompt template from Firestore ({doc.id}): {e}"
                        )
            except Exception as e:
                # This can happen if the collection doesn't exist or indexes are missing.
                # It's not a critical error, so we just log it.
                print(f"Warning: Could not load templates from Firestore: {e}"
        )

        return templates

    def load_all_templates(self) -> list[PromptTemplate]:
        """Loads all default and user-created templates from all sources."""
        templates: list[PromptTemplate] = []

        # Load defaults from both files
        templates.extend(
            self._load_from_json(
                "config/text_prompt_templates.json", template_type="text"
            )
        )
        templates.extend(
            self._load_from_json(
                "config/image_prompt_templates.json", template_type="image"
            )
        )

        # Load all from Firestore
        if db:
            try:
                query = db.collection("prompt_templates").order_by("label")
                for doc in query.stream():
                    try:
                        # Avoid adding duplicates that came from the default JSON
                        if not any(t.key == doc.to_dict().get("key") for t in templates):
                            templates.append(PromptTemplate(**doc.to_dict(), id=doc.id))
                    except Exception as e:
                        print(
                            f"Warning: Skipping invalid prompt template from Firestore ({doc.id}): {e}"
                        )
            except Exception as e:
                print(f"Warning: Could not load templates from Firestore: {e}")

        return templates

    def add_template(self, template: PromptTemplate) -> PromptTemplate:
        """
        Adds a new template to the Firestore collection.
        """
        if not db:
            raise ConnectionError("Firestore client is not initialized.")

        # Exclude fields that shouldn't be saved directly in the document body
        template_dict = template.model_dump(exclude={"id"})

        _, doc_ref = db.collection(self.collection_name).add(template_dict)

        # Return the template with the new Firestore-generated ID
        template.id = doc_ref.id
        return template

    def update_template(self, template_id: str, updates: dict):
        """Updates an existing template in the Firestore collection."""
        if not db:
            raise ConnectionError("Firestore client is not initialized.")

        doc_ref = db.collection(self.collection_name).document(template_id)
        doc_ref.update(updates)
        print(f"Successfully updated template '{template_id}' in Firestore.")


# Instantiate a global service object
prompt_template_service = PromptTemplateService()
