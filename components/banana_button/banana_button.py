import mesop as me

@me.web_component(path="./banana_button.js")
def banana_button(
    *,
    selected: bool = False,
    badge: str = "",
    label: str = "",
    model_name: str = "",
    on_click=None,
    key: str | None = None,
):
    """
    A custom web component representing a selectable banana model button.
    """
    return me.insert_web_component(
        key=key,
        name="banana-button",
        properties={
            "selected": selected,
            "badge": badge,
            "label": label,
            "modelName": model_name,
        },
        events={
            "model-selected": on_click,
        },
    )
