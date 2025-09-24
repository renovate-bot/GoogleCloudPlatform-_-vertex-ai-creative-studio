# Developer Guide

This guide provides information for developers working on the GenMedia Creative Studio application.

## Analytics and Instrumentation

When adding new features, it is important to instrument them with the analytics framework from `common/analytics.py` to provide insights into user behavior and application performance.

### Page Views

Page view tracking is handled automatically by the `page_scaffold` component. When creating a new page, ensure it is wrapped with this scaffold to enable automatic page view logging.

### UI Interactions

There are two ways to track UI interactions: the `@track_click` decorator for simple button clicks, and the `log_ui_click` function for other controls.

#### Button Clicks

To track clicks on buttons, use the `@track_click` decorator on your event handler. This is the simplest way to instrument a button.

**Example:**

```python
from common.analytics import track_click

@track_click(element_id="my_page_generate_button")
def on_generate_click(e: me.ClickEvent):
    # Your event handler logic here
    yield
```

#### Other Controls

For UI elements that don't have a simple click event (e.g., sliders, selects, text inputs), you can use the `log_ui_click` function directly inside the event handler.

**Example:**

```python
from common.analytics import log_ui_click
from state.state import AppState

def on_slider_change(e: me.SliderValueChangeEvent):
    app_state = me.state(AppState)
    log_ui_click(
        element_id="my_page_slider",
        page_name=app_state.current_page,
        session_id=app_state.session_id,
        extras={"value": e.value},
    )
    # Your event handler logic here
    yield
```

#### Element IDs

When choosing an `element_id`, use a consistent naming convention. A good practice is to use the format `page_name_element_type_name`. For example:

*   `imagen_generate_button`
*   `veo_aspect_ratio_select`
*   `chirp_text_input`

### Model Calls

To track the performance and status of calls to generative models, use the `track_model_call` context manager.

**Example:**

```python
from common.analytics import track_model_call

with track_model_call("my-generative-model-v1", prompt_length=len(prompt)):
    model.generate_content(...)
```
