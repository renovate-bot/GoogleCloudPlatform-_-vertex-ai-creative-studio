# Guide: Integrating Interactive Lit Web Components in a FastAPI-based Mesop App

This document provides a comprehensive, definitive guide to correctly implementing and debugging custom, **interactive** Lit-based Web Components within a Mesop application that is served by a custom FastAPI server.

**Last Updated:** 2025-07-28

## 1. The Core Challenge: Two-Way Communication

Integrating a custom JavaScript component is straightforward when it only needs to receive data from Python. The challenge arises when the component needs to send events *back* to Python (e.g., from a click or a scroll event). This two-way communication requires a specific, non-obvious implementation pattern, especially when using a custom FastAPI server.

This guide outlines the definitive, working patterns discovered through a rigorous debugging process.

## 2. The Definitive Pattern: A Complete Example

Here is a complete, working example of an interactive component. The following sections will break down why each part is essential.

### A. The Lit Component (`.js`)

```javascript
// components/my_interactive_component.js
import { LitElement, html } from 'https://esm.sh/lit';

class MyInteractiveComponent extends LitElement {
  static properties = {
    // 1. Receives data from Python.
    items: { type: Array },
    // 2. Receives a unique handler ID string from the Mesop framework.
    // The name `itemClickEvent` is automatically generated from the Python
    // `on_item_click` handler name.
    itemClickEvent: { type: String },
  };

  render() {
    return html`
      <ul>
        ${this.items.map(
          (item) => html`<li @click=${() => this._handleClick(item)}>${item.name}</li>`
        )}
      </ul>
    `;
  }

  _handleClick(item) {
    // 3. Check if the handler ID property was passed from Python.
    if (!this.itemClickEvent) {
      console.error("Mesop event handler ID for itemClickEvent is not set.");
      return;
    }
    // 4. Dispatch a MesopEvent, using the handler ID as the event name.
    this.dispatchEvent(new MesopEvent(this.itemClickEvent, { clicked_item: item }));
  }
}
customElements.define("my-interactive-component", MyInteractiveComponent);
```

### B. The Python Wrapper (`.py`)

```python
# components/my_interactive_component.py
import mesop as me
import typing

@me.web_component(path="./components/my_interactive_component.js")
def my_interactive_component(
    *,
    items: list[dict],
    # 1. Define the event handler prop that the parent will provide.
    on_item_click: typing.Callable[[me.WebEvent], None],
    key: str | None = None,
):
  """Defines the API for the interactive web component."""
  # 2. Render the component, passing properties and the event mapping.
  return me.insert_web_component(
    key=key,
    name="my-interactive-component", # Matches customElements.define()
    properties={"items": items},
    events={
      # 3. Map the JS event name to the Python handler prop.
      # This tells Mesop to create and pass the `itemClickEvent` property
      # to the Lit component.
      "itemClick": on_item_click,
    },
  )
```

### C. The Parent Component (Usage)

```python
# pages/my_page.py
import mesop as me
from .components.my_interactive_component import my_interactive_component

@me.stateclass
class State:
    last_clicked: str = ""

@me.page(path="/my_page")
def my_page():
    state = me.state(State)

    # 1. Define the handler function.
    def handle_click(e: me.WebEvent):
        # 2. Access the data from the `e.value` attribute.
        state.last_clicked = e.value["clicked_item"]["name"]
        yield

    # 3. Call the component, passing the handler to the `on_...` prop.
    my_interactive_component(
        items=[{"name": "Apple"}, {"name": "Banana"}],
        on_item_click=handle_click,
    )
    if state.last_clicked:
        me.text(f"You clicked: {state.last_clicked}")
```

## 3. Key Concepts Explained

### A. The `events` Dictionary is Mandatory

The `TypeError: insert_web_component() got an unexpected keyword argument 'on_...'` proves that you cannot pass event handlers as direct arguments. You **must** use the `events` dictionary to map JavaScript event names to Python handler functions.

### B. The JavaScript Event Name (`key`) vs. The Python Prop (`value`)

-   The **key** in the `events` dictionary (e.g., `"itemClick"`) is the `camelCase` name of the event your JavaScript will dispatch.
-   The **value** in the `events` dictionary (e.g., `on_item_click`) is the name of the Python function argument that will receive the handler.

### C. The Magic `...Event` Property

-   When you define an event in the `events` dictionary (e.g., `"itemClick": on_item_click`), the Mesop framework automatically creates a property on your web component with the same name, plus the suffix `Event` (e.g., `itemClickEvent`).
-   The value of this property is a unique string ID that the server generates for the handler.
-   Your JavaScript code **must** declare this property in `static properties` and use its value as the name of the `MesopEvent` it dispatches. This is the core mechanism that wires the frontend event to the backend handler.

### D. Accessing Event Data with `e.value`

The `AttributeError: 'WebEvent' object has no attribute 'payload'` proves that the data sent from the `MesopEvent` is accessed in Python via the `e.value` attribute, not `e.payload`.

### E. Server Configuration (`main.py`)

Remember to configure your FastAPI server to handle:
1.  **File Serving:** Mount the `/__web-components-module__/` path to serve your `.js` files.
2.  **Content Security Policy:** Add any external CDNs (like `https://esm.sh`) to the `script-src` directive in your CSP middleware.
