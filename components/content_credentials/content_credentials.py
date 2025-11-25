import mesop as me

@me.web_component(path="./content_credentials.js")
def content_credentials_viewer(
    *,
    manifest: str, # Expecting JSON string
    key: str | None = None,
):
    """
    A web component that displays Content Credentials (C2PA) data.
    
    Args:
        manifest: The parsed C2PA manifest as a JSON string.
    """
    if not manifest:
        return
        
    return me.insert_web_component(
        key=key,
        name="content-credentials-viewer",
        properties={
            "manifestJson": manifest,
        },
    )