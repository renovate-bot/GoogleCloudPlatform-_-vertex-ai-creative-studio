import mesop as me

@me.web_component(path="./search_entry_point.js")
def search_entry_point(
    *,
    html_content: str,
    theme_mode: str = "light",
    key: str | None = None,
):
    return me.insert_web_component(
        name="search-entry-point",
        key=key,
        properties={
            "htmlContent": html_content,
            "themeMode": theme_mode,
        },
    )
