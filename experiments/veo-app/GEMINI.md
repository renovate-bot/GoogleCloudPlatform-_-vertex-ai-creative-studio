# Genmedia Creative Studio - Mesop python application

You are a code assistant that will help build a Mesop UI application - Mesop is a python-based UI framework that can be found in the .venv/lib. 

This application provides the end user with the ability to use Vertex AI Generative Media APIs such as Veo, Lyria, Chirp 3, and Imagen.

It provides a coherent Library that displays metadata of the generative media generations from Firestore.

See also AGENTS.md for more information.


# Mesop Hints and Lessons Learned

- The `mesop` library was updated, and `me.yield_value(...)` was removed. It should be replaced with `yield`.

## Interacting with Generative AI Models

Here are some key architectural lessons learned when integrating Mesop with Generative AI models:

1.  **Handling Asynchronous-like Operations:** When calling a long-running function (like a GenAI API) from a Mesop event handler, it's crucial to handle the state updates correctly. The recommended pattern is:
    -   The event handler should call a standard Python function that performs the API call and `return`s the result.
    -   The event handler should then assign the returned value to the appropriate state variable.
    -   Finally, the event handler should `yield` to trigger a UI update. This ensures that the result of the long-running operation is correctly reflected in the UI.

2.  **Debugging Model Behavior:** If a model returns an unexpected or truncated response, the issue is often in the prompt or the model parameters. To debug this effectively:
    -   Log the *entire* API response object, not just the text output.
    -   Inspect the response metadata, such as `finish_reason` and `safety_ratings`, to understand why the model stopped generating text.

3.  **Explicit Prompting for Iterative Tasks:** When you need a model to perform the same task on multiple items (e.g., critiquing a list of images), your prompt must be very explicit. To ensure the model completes the entire task:
    -   Instruct the model to iterate through each item.
    -   Define the exact format for each part of the response.
    -   This prevents the model from stopping prematurely after processing only the first item.

## Component Layout and Styling

*   **Use `dialog_actions` for button rows:** When you want to display a row of buttons in a dialog, wrap them in the `dialog_actions` component. This will ensure they are laid out correctly.

*   **Avoid `max_width` for expanding content:** If you want a component to fill the available space in its container, avoid using the `max_width` style property. This will allow the component to expand as expected.

*   **Use `me.Style(margin=me.Margin(top=...))` for spacing:** To add spacing between components, use the `margin` property in the `me.Style` class. This is the correct way to add padding and margins to components.


## Best Practices for Using Mesop with FastAPI

This document outlines key lessons learned and best practices for integrating the Mesop UI library with a FastAPI backend. Following these guidelines can help avoid common issues related to routing, static file serving, and security policies.

### 1. Handling Routing and Path Conflicts

**The Problem:** FastAPI routes (e.g., `@app.get('/')`) do not work as expected if a Mesop app is mounted at the same root path.

**The Cause:** When you mount the Mesop application using `WSGIMiddleware` at a specific path (like `/`), it acts as a catch-all for all requests under that path. This means the Mesop app will receive the request before your FastAPI route handler has a chance to execute, leading to a "Not Found" error in Mesop if the path isn't a registered Mesop page.

**The Solution:** Mount the Mesop WSGI application on a sub-path (e.g., `/app`). This allows FastAPI's router to handle specific root-level paths (like `/` for redirects or `/__/auth/` for authentication) first, before passing requests to the Mesop application.

**Example:**
```python
# Allows FastAPI to handle the root path for redirects
@app.get("/")
def home() -> RedirectResponse:
    return RedirectResponse(url="/app/home")

# Mounts the Mesop app on a sub-path
app.mount(
    "/app",
    WSGIMiddleware(
        me.create_wsgi_app()
    ),
)
```

### 2. Serving Mesop's Static Frontend Assets

**The Problem:** When running the application directly with an ASGI server like Uvicorn (e.g., `python main.py`), the Mesop UI is blank, and the browser console shows 404 (Not Found) errors for files like `prod_bundle.js` and `styles.css`.

**The Cause:** The `mesop` command-line tool automatically handles the serving of Mesop's internal frontend assets. When you bypass this and run your own server, you become responsible for serving these files.

**The Solution:** You must explicitly add a `StaticFiles` mount to your FastAPI application that points to the location of Mesop's frontend assets within the installed `mesop` package. You can find this path dynamically using Python's `inspect` and `os` modules.

**Example:**
```python
import inspect
import os
import mesop as me
from fastapi.staticfiles import StaticFiles

# ... your FastAPI app setup ...

app.mount(
    "/static",
    StaticFiles(
        directory=os.path.join(
            os.path.dirname(inspect.getfile(me)), "web", "src", "app", "prod", "web_package"
        )
    ),
    name="static",
)
```

### 3. Applying a Content Security Policy (CSP)

**The Problem:** A Content Security Policy (CSP) defined in a page-specific decorator (`@me.page(security_policy=...)`) is not applied, causing the browser to block external scripts or resources.

**The Cause:** When Mesop is run inside FastAPI's `WSGIMiddleware`, the environment can prevent these page-specific headers from being correctly propagated to the final HTTP response sent by FastAPI.

**The Solution:** The most reliable method is to apply a global CSP using a FastAPI middleware. This intercepts every outgoing response and adds the necessary `Content-Security-Policy` header, ensuring it is applied consistently across all pages.

**Example:**
```python
from fastapi import Request, Response

# ... your FastAPI app setup ...

@app.middleware("http")
async def add_custom_header(request: Request, call_next):
    response = await call_next(request)
    # This is an example policy. Adjust it to your needs.
    response.headers["Content-Security-Policy"] = "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self';"
    return response
```

## Application Architecture and State Management

### 1. Accessing Global State in Event Handlers

**The Problem:** An event handler (e.g., `on_click`) throws a `NameError` because it cannot access the global `AppState`.

**The Cause:** Unlike the main page function, which receives the application state as a parameter, event handlers operate in a different scope and do not automatically have access to it. 

**The Solution:** You must explicitly get a reference to the global state inside the event handler function by calling `me.state(AppState)`.

**Example:**
```python
from state.state import AppState

def on_click_my_button(e: me.ClickEvent):
    # Correctly get a reference to the global state
    app_state = me.state(AppState)
    
    # Now you can access properties of the global state
    print(f"The current user is: {app_state.user_email}")
```

### 2. Separating Configuration from Code

**The Problem:** The application's navigation menu is hardcoded as a list of dictionaries in a Python file, making it difficult to manage.

**The Best Practice:** For data that is essentially static configuration, such as navigation links or dropdown options, it is better to store it in a dedicated data file (e.g., JSON or YAML) rather than embedding it in Python code. This separates the application's configuration from its logic.

**The Solution:**
1.  Create a `config/navigation.json` file to define the navigation structure.
2.  In your Python code, read this file and parse it. 
3.  (Recommended) Use Pydantic models to validate the structure of the loaded data, which prevents errors from malformed configuration.

This approach makes the configuration easier to read, modify (even for non-developers), and validate.

### 3. Deploying with Gunicorn and Uvicorn

**The Problem:** When deploying to a service like Cloud Run, the application fails to start, or authentication routes do not work.

**The Cause:** The `Procfile` command is configured to run a standard WSGI application, but a FastAPI-wrapped Mesop app is an ASGI application.

**The Solution:** You must instruct the Gunicorn process manager to use a Uvicorn worker, which knows how to run ASGI applications. The `Procfile` command should point to the FastAPI `app` object in your `main.py` file.

**Example `Procfile`:**
```
web: gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 -k uvicorn.workers.UvicornWorker main:app
```

## VTO Page Lessons Learned: Creating the Virtual Try-On (VTO) Page

This section summarizes the process of creating the Virtual Try-On (VTO) page, including the challenges encountered and the solutions implemented.
- **Mutable Default Values:** When defining a state class, avoid using mutable default values like `[]` for fields. Instead, use `field(default_factory=list)` to ensure that a new list is created for each user session.

- **Slider Component:** If the `me.slider` component doesn't support a `label` parameter, you can wrap it in a `me.box` and use a `me.text` component as the label.

- **Generator Functions:** Generator functions (those that use `yield`) must have a `yield` statement after updating the state to ensure that the UI is updated.

- **API Error Handling:** When an API returns an "Internal error" with an Operation ID, it signifies a server-side issue. The best course of action is to wait and retry, and if the problem persists, report the Operation ID to Google Cloud support.

- **GCS URI Construction:** When working with GCS URIs, be mindful of duplicate prefixes. The `store_to_gcs` function returns a full `gs://` URI, so do not prepend the prefix again in the calling function. This applies to both creating display URLs (e.g., `https://storage.mtls.cloud.google.com/`) and passing URIs to the API.


### 1. Initial Scaffolding and Page Creation

- **File Structure:** Following the existing architecture, we created three new files:
    - `pages/vto.py`: For the UI and page logic.
    - `state/vto_state.py`: For managing the page's state.
    - `models/vto.py`: For handling the VTO model interaction.
- **Page Registration:** The new page was registered in `main.py` and added to the navigation in `config/navigation.json`.

### 2. File Uploads and GCS Integration

- **GCS Uploads:** We used the existing `common/storage.py` module to upload the person and product images to Google Cloud Storage.
- **Displaying GCS Images:** We learned that the `me.image` component requires a public HTTPS URL, not a `gs://` URI. The correct way to display GCS images is to replace `gs://` with `https://storage.mtls.cloud.google.com/`.

### 3. Interacting with the VTO Model

- **Model API:** We adapted the provided [generative-ai/vision/getting-started
/virtual_try_on.ipynb](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/vision/getting-started/virtual_try_on.ipynb) sample to work within our application's architecture. This involved:
    - Using GCS URIs instead of local files.
    - Passing the `sampleCount` and `baseSteps` parameters to the model.
    - Handling multiple generated images in the response.
- **Configuration:** We moved the VTO model name to the `config/default.py` file to avoid hardcoding it.

### 4. UI/UX Improvements

- **Image Display:** We resized the person and product images to a maximum width of 400px and centered them under their respective upload buttons.
- **Slider Control:** We added a slider to control the number of images generated, and we displayed the currently selected value next to the slider.
- **Clear Button:** We added a "Clear" button to reset the person, product, and generated images.

### 5. State Management and Debugging

- **Mutable Default Values:** We encountered a `TypeError` because we were using a mutable default value (`[]`) for the `result_images` list in our state class. We resolved this by using `field(default_factory=list)` instead.
- **Slider Component:** We encountered an `Unexpected keyword argument` error when using the `label` parameter on the `me.slider` component. We resolved this by wrapping the slider in a `me.box` and using a `me.text` component as the label.
- **Generator Functions:** We learned that generator functions (those that use `yield`) must have a `yield` statement after updating the state to ensure that the UI is updated.

## Veo Model Interaction: Lessons Learned

- **SDK Type Specificity:** The `google-genai` SDK requires different `types` for different kinds of image-based video generation. Using the wrong type will result in a Pydantic validation error. The key is to be precise:
    - For a standard **Image-to-Video** call (one input image), the image must be wrapped in `types.Image(gcs_uri=..., mime_type=...)`.
    - For **Interpolation** (a first and last frame), both images must also be wrapped in `types.Image(gcs_uri=..., mime_type=...)`. The first frame is passed as the main `image` parameter, and the last frame is passed as the `last_frame` parameter inside the `GenerateVideosConfig`.

- **Configuration-Driven Lookups:** When a feature (like the Motion Portraits page) needs to get configuration for a model, it's crucial to use the correct key. Our `config/veo_models.py` uses a short version string (e.g., `"2.0"`) as the key, not the full model ID (e.g., `"veo-2.0-generate-001"`). Passing the wrong identifier will lead to an "Unsupported model" error. Always ensure the UI state provides the simple version string for lookups.

- **Isolating and Removing Legacy Code:** A major source of our errors was the presence of an old, non-SDK-based function (`generate_video_aiplatform`) that was still being called by one of the pages. This highlights the importance of completely removing obsolete code after a refactor to prevent it from being used accidentally. A single, unified function (`generate_video`) that handles all generation paths is much easier to maintain and debug.

- **Enhanced Error Logging:** When polling a long-running operation from the `google-genai` SDK, the `operation.error` attribute contains a detailed error message if the operation fails. It is critical to log this specific message in the exception handler. Relying on a generic error message hides the root cause and makes debugging significantly harder.


# More Lessons Learned

Fact: When working with the Mesop framework, access shared or global state within an event handler by calling app_state = me.state(AppState) inside that handler. Do not pass state objects directly as parameters to  components, as this will cause a Pydantic validation error.

1. Prioritize Compatibility Over Premature Optimization: My first error was introducing an ImportError with CountAggregation. While the intention was to make counting faster, it relied on a newer version of the  google-cloud-firestore library than was installed in the project. The lesson is to always work within the  constraints of the project's existing dependencies. A slightly less performant but working solution is always  better than a broken one.


2. Refactoring Requires Thoroughness (Read and Write): When we changed the MediaItem dataclass (renaming  enhanced_prompt to enhanced_prompt_used), I initially only fixed where the data was written. This led to the AttributeError because I didn't fix all the places where the data was read (like the library page). The lesson is that refactoring a data structure requires a global search to update every single point of access.


3. Understand Framework-Specific State Management: This was the most important lesson. My final two errors were  caused by misunderstanding Mesop's state management pattern.
    * The Error: I tried to "push" the global AppState into a component as a parameter  (generation_controls(app_state=...)).
    * The Mesop Way: Components should be self-contained. The correct pattern is for an event handler (like  on_click_generate_images) to "pull" the state it needs when it's triggered, by calling me.state(AppState)  within the function itself.


# Refactoring Checklist

When refactoring code, follow these steps to avoid common errors:

1.  **Find all uses of the code being changed.** Use `search_file_content` to find all instances of the code you are changing. This will help you to avoid missing any instances of the code that need to be updated.
2.  **Pay close attention to data models.** When changing a data model, make sure to update all code that uses that data model. This includes code that reads from and writes to the data model.
3.  **Run tests after making changes.** This will help you to catch any errors that you may have introduced.

## Code Quality and Style
After any code modification, ensure the changes adhere to the project's established style guide (e.g., Google Python Style Guide for this project). Proactively run any configured linters or formatters to verify compliance before considering a task complete. This ensures consistency and maintainability.

# Data Consistency

When working with Firestore, it is important to keep the data in Firestore consistent with the data models in the code. This can be done by:

*   **Using a single source of truth for your data models.** This will help to ensure that all code is using the same data models.
*   **Using a data migration tool to update your data in Firestore when you change your data models.** This will help to ensure that your data in Firestore is always consistent with your data models.
*   **When checking field values from external data sources like Firestore, prefer containment checks (e.g., `if 'substring' in value:`) over exact equality checks (`if value == 'exact_string'`) for identifiers that might have variations. This makes the code more robust. Also, always use the `.get('key', default_value)` method to access dictionary keys safely.**

# Working with GCS URIs

When working with GCS URIs, it is important to construct them correctly. The correct way to construct a GCS URI is to use the following format:

```
gs://<bucket-name>/<object-name>
```

When constructing a GCS URI, make sure to not include the `gs://` prefix more than once.

## VTO Page Lessons Learned: Creating the Virtual Try-On (VTO) Page
VTO-generated items stored in Firestore can be identified by checking if the `model` field in their `raw_data` contains the string `'virtual-try-on'`. The original input images are available in the `raw_data` under the keys `person_image_gcs` and `product_image_gcs`.


# More Lessons Learned

Fact: When working with the Mesop framework, access shared or global state within an event handler by calling app_state = me.state(AppState) inside that handler. Do not pass state objects directly as parameters to  components, as this will cause a Pydantic validation error.

1. Prioritize Compatibility Over Premature Optimization: My first error was introducing an ImportError with CountAggregation. While the intention was to make counting faster, it relied on a newer version of the  google-cloud-firestore library than was installed in the project. The lesson is to always work within the  constraints of the project's existing dependencies. A slightly less performant but working solution is always  better than a broken one.


2. Refactoring Requires Thoroughness (Read and Write): When we changed the MediaItem dataclass (renaming  enhanced_prompt to enhanced_prompt_used), I initially only fixed where the data was written. This led to the AttributeError because I didn't fix all the places where the data was read (like the library page). The lesson is that refactoring a data structure requires a global search to update every single point of access.


3. Understand Framework-Specific State Management: This was the most important lesson. My final two errors were  caused by misunderstanding Mesop's state management pattern.
    * The Error: I tried to "push" the global AppState into a component as a parameter  (generation_controls(app_state=...)).
    * The Mesop Way: Components should be self-contained. The correct pattern is for an event handler (like  on_click_generate_images) to "pull" the state it needs when it's triggered, by calling me.state(AppState)  within the function itself.


# Refactoring Checklist

When refactoring code, follow these steps to avoid common errors:

1.  **Find all uses of the code being changed.** Use `search_file_content` to find all instances of the code you are changing. This will help you to avoid missing any instances of the code that need to be updated.
2.  **Pay close attention to data models.** When changing a data model, make sure to update all code that uses that data model. This includes code that reads from and writes to the data model.
3.  **Run tests after making changes.** This will help you to catch any errors that you may have introduced.

# Data Consistency

When working with Firestore, it is important to keep the data in Firestore consistent with the data models in the code. This can be done by:

*   **Using a single source of truth for your data models.** This will help to ensure that all code is using the same data models.
*   **Using a data migration tool to update your data in Firestore when you change your data models.** This will help to ensure that your data in Firestore is always consistent with your data models.

# Working with GCS URIs

When working with GCS URIs, it is important to construct them correctly. The correct way to construct a GCS URI is to use the following format:

```
gs://<bucket-name>/<object-name>
```

When constructing a GCS URI, make sure to not include the `gs://` prefix more than once.