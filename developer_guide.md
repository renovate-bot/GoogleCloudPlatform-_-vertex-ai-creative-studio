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

## State Management

### Working with Dataclasses

When using dataclasses in the Mesop state, it's important to be aware of how they are serialized. Mesop's state management system does not automatically serialize dataclasses that contain non-serializable objects, such as `datetime.datetime`.

To work around this, you have two options:

1.  **Use simple types:** The simplest solution is to use only simple types (e.g., `str`, `int`, `float`, `bool`, `list`, `dict`) in your dataclasses. For example, instead of using a `datetime.datetime` object for a timestamp, you can use an ISO 8601 string.

2.  **Use `asdict`:** If you need to use complex types in your dataclasses, you can use the `asdict` function from Python's `dataclasses` module to convert the dataclass instance to a dictionary before assigning it to the state.

    **Example:**

    ```python
    from dataclasses import asdict

    # ...

    state.my_dataclass = asdict(MyDataClass(timestamp=datetime.datetime.now()))
    ```

    When you access the dataclass from the state, you will need to access it as a dictionary:

    ```python
    timestamp = state.my_dataclass["timestamp"]
    ```
