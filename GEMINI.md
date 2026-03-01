---

## 7. Documentation Workflows

### Updating Documentation for New Features/Experiments

When new code, features, or experiments are added, it's crucial to update the relevant documentation to ensure discoverability and maintainability.

1.  **Identify Relevant Docs:** Determine which documentation files need updating (e.g., main `README.md`, `experiments/README.md`, `developers_guide.md`).
2.  **Analyze Existing Conventions:** Read the target documentation to understand its structure, tone, and formatting conventions for similar items.
3.  **Synthesize New Content:** Extract key information from the new feature's source code or its own README to create a concise and accurate description.
4.  **Propose Changes:** Present the proposed documentation changes to the user for review and approval before applying them. Use markdown blocks to clearly show the additions or modifications.
5.  **Apply Changes:** Use the `replace` or `write_file` tool to apply the approved changes.

## 8. Mesop Development Practices

### Refactoring and State Management
*   **Component Modularity:** Mesop pages can quickly grow to thousands of lines. Proactively refactor UI sections (e.g., `upload_ui`, `controls`, `gallery`) into separate files within a `components/` directory to keep page files tractable.
*   **Event Handler Factories:** When sharing UI components across multiple pages that maintain their own `PageState` classes, use closure factories (e.g., `def get_on_click_handler(state_class): ...`) to generate reusable event handlers. This avoids duplicating state-mutation logic across pages.
*   **Safe Python Refactoring:** When executing large refactors via CLI tools, be extremely cautious with string replacements (`sed` or python scripts) on nested Mesop structures (`with me.box():`). Missing or extra spaces will cause fatal `IndentationError`s. Prefer targeted replacements or abstracting the block into a function first.

### Component Styling Gotchas
*   **Button Types:** The `me.content_button` component strictly enforces the `type` argument as a literal: `'raised'`, `'flat'`, `'stroked'`, or `'icon'`. Using invalid MD3 concepts like `'tonal'` will cause a Pydantic `ValidationError` and crash the UI block.
*   **Interactive Toggles:** When changing the background of a button dynamically (e.g., to indicate selection), ensure you also dynamically update the `color` property of its children (e.g., `me.theme_var("on-primary") if is_selected else me.theme_var("on-surface")`) so icons and text don't become invisible.

### SDK Integration Nuances
*   **Model Parameter Probing:** The `google-genai` SDK and Vertex AI backend can be incredibly strict. For example, `types.ImageConfig(image_size="512PX")` will fail validation; it must be `"512"`. `types.ThinkingConfig` expects `thinking_budget` (not `thinking_level`), and setting `include_thoughts=True` without a budget throws a `400 INVALID_ARGUMENT`. Always write a short `test_probe.py` script to verify exact SDK payload shapes before wiring them into the Mesop UI state.



### Lit WebComponents Interop
Mesop allows integrating custom Lit WebComponents, but the bridge between JavaScript and Python is highly specific. When creating custom components like `<banana-button>`:
1. **Property Binding:** Declare properties explicitly in your Lit element's `static properties = { ... }`. Mesop dynamically sets these from the `properties={}` dict in the python wrapper.
2. **Event Naming (CamelCase Rule):** Mesop automatically transforms kebab-case into camelCase for internal event routing. When firing events from JS to Python, **always use camelCase strings** for both the JS `CustomEvent` name and the python `events={}` dictionary key (e.g. `modelSelected`, not `model-select`).
3. **Payload Structure:** Mesop expects incoming custom event data to live on the `detail` object, specifically under a `value` key. Always dispatch like this: `this.dispatchEvent(new CustomEvent('eventName', { detail: { value: this.myValue }, bubbles: true, composed: true }))`.
4. **Python Type Hinting (Critical):** In the python wrapper function (e.g. `@me.web_component(...) def my_component():`), the event handler argument *must* be strictly typed as a callable accepting a `WebEvent` (e.g. `on_click: Callable[[me.WebEvent], Any]`). If you type it as `None` or `Any`, Mesop's reflection engine will silently fail to register the listener, and the events will be dropped over the websocket bridge.

### 🚨 The `git restore` Trap (Data Loss)
When performing iterative, multi-step refactoring in a single session without intermediate commits, **do not use `git restore <file>` or `git checkout -- <file>`** to recover from a botched regex or Python script edit.
*   **Why:** `git restore` resets the file to the last *commit*. This instantly wipes out *all* uncommitted progress you made earlier in the session (such as adding new variables to a `@me.stateclass`, importing new modules, or fixing specific bugs).
*   **The Bug Cycle:** If you `git restore` to fix an indentation error in a UI component, but forget to manually re-add the state variables you defined 10 minutes ago, the app will compile but crash at runtime with `AttributeError: 'PageState' object has no attribute '...'`.
*   **The Solution:** 
    1. Always run `cp file.py file.py.bak` *before* executing a risky string replacement script. If it fails, restore from the local backup: `mv file.py.bak file.py`.
    2. Alternatively, use `git add file.py` to stage known-good intermediate states, allowing you to `git checkout -- file.py` safely back to the *index* rather than the last commit.
