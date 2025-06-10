import mesop as me

from components.header import header
from components.imagen.advanced_controls import advanced_controls
from components.imagen.generation_controls import generation_controls
from components.imagen.image_output import image_output
from components.imagen.modifier_controls import modifier_controls
from components.page_scaffold import page_frame, page_scaffold
from state.imagen_state import PageState


def imagen_content(app_state: me.state):
    """Imagen Mesop Page"""
    state = me.state(PageState)

    with page_scaffold():  # pylint: disable=not-context-manager
        with page_frame():  # pylint: disable=not-context-manager
            header("Imagen Creative Studio", "image")

            generation_controls()
            modifier_controls()
            advanced_controls()
            image_output()

