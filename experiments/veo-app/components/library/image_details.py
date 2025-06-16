import mesop as me

from common.metadata import MediaItem


@me.component
def image_details(item: MediaItem):
    """Image details component"""
    with me.box(
        style=me.Style(
            display="grid",
            grid_template_columns="repeat(auto-fill, minmax(200px, 1fr))",
            gap="16px",
            width="100%",
        )
    ):
        for uri in item.gcs_uris:
            me.image(
                src=uri.replace("gs://", "https://storage.googleapis.com/"),
                style=me.Style(
                    width="100%",
                    height="auto",
                    border_radius="8px",
                ),
            )
    me.text(f"Prompt: \"{item.prompt or 'N/A'}\"")
    if item.rewritten_prompt:
        me.text(f'Rewritten Prompt: "{item.rewritten_prompt}"')
    if item.critique:
        me.text(f"Critique: {item.critique}")
