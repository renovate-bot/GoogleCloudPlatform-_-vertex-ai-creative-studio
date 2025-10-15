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

## Application Architecture and State Management

This section outlines critical architectural patterns and solutions to common but subtle bugs encountered in this Mesop application. Adhering to these patterns is crucial for building robust and maintainable features.

### 1. The Parent-Managed State Pattern (for Reusable Components)

**The Problem:** A reusable component (e.g., a "chooser" button) used multiple times on the same page exhibits bizarre behavior, where interacting with one instance affects the others.

**The Cause:** Using `@me.stateclass` on a class creates a **single, global state object** for all instances of that component. This leads to state collisions, where one component overwrites the state of another. Attempts to work around this with component keys (`me.state(State, key=...)`) or by defining the state class inside the component function are **not supported** by the version of Mesop in this project and will cause crashes.

**The Solution: Parent-Managed State**

The only robust solution is to make reusable components stateless ("dumb") and have the parent page manage all state and complex UI.

-   **Stateless Component:** The component itself should be simple. It should not have a `@me.stateclass`. It should only accept properties (like an `on_click` handler) from its parent.
-   **Parent Page Manages State:** The page that uses the component is responsible for all state management. This includes fields for dialog visibility, loading states, and data.
-   **Parent Page Renders Dialogs:** Any complex UI, like a `dialog`, should be rendered by the parent page, not the component. The component's `on_click` handler updates the page's state to show the dialog, and the page re-renders to display it with the correct content.

For a complete working example of this pattern, see `pages/test_media_chooser.py`.

### 2. Handling Non-Serializable Objects in State

**The Problem:** The application crashes with an error like `Object of type DocumentSnapshot is not JSON serializable` or `Unhandled stateclass deserialization`.

**The Cause:** Mesop's state must be fully JSON serializable to be passed between the server and the browser. Complex Python objects cannot be placed in a state class directly.

**The Solutions:**

-   **For Dictionaries (`dict`):** If a dataclass field within your state holds a dictionary (e.g., a JSON API response), it will cause a deserialization error.
    -   **Best Practice:** The field in the dataclass should be typed as `str`.
    -   **On Write:** Before saving, convert the dictionary to a string with `json.dumps()`.
    -   **On Read:** To make reading robust, use the `__post_init__` method in your dataclass to automatically check if the data is a `dict` (from an old record in Firestore) and convert it to a string. This centralizes the fix.

-   **For Firestore `DocumentSnapshot`:** To implement cursor-based pagination, you need the `DocumentSnapshot` object.
    -   **Do not** store the `DocumentSnapshot` object in the state.
    -   **Instead:** Store only the document's ID (`last_doc.id`), which is a string.
    -   When fetching the next page, use the stored ID to re-fetch the `DocumentSnapshot` object just before making the next query: `db.collection(...).document(state.last_doc_id).get()`.

### 3. Event Handlers and Rendering

**The Problem:** An event handler runs (as seen in logs), but the UI does not update, or a dialog fails to appear.

**The Cause:** This can happen if the function containing the `yield` statement is not the function directly assigned to the event handler (e.g., it is wrapped in a `lambda`). This can interrupt Mesop's render cycle.

**The Solution:** The function that contains `yield` must be assigned **directly** to the event property. If you need to pass extra parameters, create a new, dedicated handler function for each specific action rather than using a `lambda`.

**Example:**
```python
# In your page code:

# GOOD: Direct assignment
def on_open_video_dialog(e: me.ClickEvent):
    state = me.state(PageState)
    state.dialog_media_type = "video"
    state.show_dialog = True
    yield

me.button("Choose Video", on_click=on_open_video_dialog)

# BAD: yield is inside a function called by a lambda
def open_dialog(media_type: str):
    state = me.state(PageState)
    state.dialog_media_type = media_type
    state.show_dialog = True
    yield

me.button("Choose Video", on_click=lambda e: open_dialog("video")) # This may not work reliably
```