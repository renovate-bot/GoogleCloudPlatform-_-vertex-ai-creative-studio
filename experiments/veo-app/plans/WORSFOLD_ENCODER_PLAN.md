# Plan: Integrating the Worsfold Encoder Lit Component

This document outlines a phased plan to adapt the `worsfold/encoder` Angular application into a Lit-based Web Component and integrate it into the GenMedia Creative Studio as a new page.

---

## Build and Deployment Impact

Adding a custom Lit component like this introduces a new type of asset to the application that the server needs to handle. This has the following implications for the build and deployment process:

1.  **New Static Files:** The application will now include JavaScript files (e.g., `worsfold_encoder.js`) and the `ffmpeg.wasm` assets. These are static assets that must be served to the browser.
2.  **Server Configuration (`main.py`):** The FastAPI server must be configured to serve these new files. This involves adding `StaticFiles` mounts in `main.py` for the directories containing the components and the wasm assets.
3.  **Container Image (`Dockerfile`):** When deploying to Cloud Run, the `Dockerfile` must be updated to `COPY` these new directories into the container image so the server can find and serve them. This will increase the overall size of the container image.
4.  **Global Content Security Policy (CSP):** A global CSP, implemented as a FastAPI middleware in `main.py`, is the most robust way to manage security policies. Page-level policies can be unreliable in production. The global policy must account for all resources used by all pages, including:
    *   `script-src`: `'self'`, `'unsafe-inline'`, `'unsafe-eval'` (for WebAssembly), and any CDNs like `https://esm.sh`.
    *   `style-src`: `'self'`, `'unsafe-inline'`, and any font providers like `https://fonts.googleapis.com`.
    *   `connect-src`: `'self'`, and any cloud storage domains like `https://storage.googleapis.com` and `https://*.googleusercontent.com`.
    *   `media-src`: `'self'`, cloud storage domains, and `blob:` (for displaying in-memory generated media).
    *   `worker-src`: `'self'` and `blob:`.

---

## Phase 1 & 2: Lit Component Creation and Mesop Integration (COMPLETE)

**Goal:** Create a self-contained Lit component and integrate it into a minimal Mesop page.

**Lessons Learned:**

*   **Event Naming is Critical:** The key in the `events` dictionary in the Python wrapper (e.g., `"loadCompleteEvent"`) must **exactly match** the property name in the Lit component that will receive the event handler ID. The `Event` suffix is **not** added automatically by Mesop.
*   **Component Lifecycle Timing:** For initialization logic that must communicate with the Mesop backend (e.g., dispatching a `load-complete` event), use the `connectedCallback()` lifecycle method in the Lit component. Do not perform this logic in the `constructor`, as the Mesop framework may not have finished initializing and injecting the necessary event handlers.
*   **UMD Module Loading:** JavaScript libraries distributed as UMD modules often rely on creating global variables. They cannot be imported using standard ES module `import`. The correct pattern is to load them by manually creating and appending `<script>` tags to the document, and then accessing the library via the `window` object (e.g., `window.FFmpegWASM.FFmpeg`).
*   **Web Worker Security:** Web Worker scripts (`.js` files) **must** be served from the same origin as the main application. A CDN-based approach for workers will be blocked by the browser's Same-Origin Policy. All files related to the worker must be served locally.

---

## Phase 3: Full UI and Signed URL Integration (COMPLETE)

**Goal:** Build the full UI and implement a robust, secure pattern for accessing GCS resources.

**Lessons Learned:**

*   **GCS Access from Frontend:** Directly fetching from GCS URLs (especially `mtls` URLs) from the browser is unreliable due to redirects and complex CORS/CSP interactions. The correct and most secure pattern is to use signed URLs.
*   **Signed URL Pattern:**
    1.  Create a FastAPI endpoint (e.g., `/api/get_signed_url`) that takes a `gs://` URI as input.
    2.  This endpoint uses the Python GCS client library to generate a short-lived, signed URL.
    3.  The frontend web component calls this endpoint to get the signed URL.
    4.  The component then uses this signed URL to fetch the resource. This works because the signed URL is designed for public, temporary access and does not have the same cross-origin restrictions.
*   **Local Authentication for Signed URLs:** For the signed URL endpoint to work locally, the developer must have their Application Default Credentials (ADC) configured to impersonate the application's service account. This is done via the `gcloud auth application-default login --impersonate-service-account=<SA_EMAIL>` command.

---

## Phase 4: Implement Saving to GCS and Library (COMPLETE)

**Goal:** Allow the user to save the generated GIF to Google Cloud Storage and have it appear in the application's media library.

**Lessons Learned:**

*   **Data Consistency:** Ensure that all required fields (e.g., `model`, `gcs_uris`) are included when creating a new `MediaItem` to avoid errors in other parts of the application, like the library details view.

---

## Phase 5: Advanced `ffmpeg` Commands (Future)

**Goal:** Extend the encoder to support more advanced `ffmpeg` operations like video concatenation and audio layering.

**Phase 5.1: Refactor for Multiple Commands**

1.  **Refactor Lit Component:**
    *   Modify `worsfold-encoder.js` to be more generic.
    *   Create separate internal functions for each command (e.g., `_createGif()`, `_concatenateVideos()`, `_layerAudio()`).
    *   Add a new `command` property to the component to select which operation to run.
    *   Change the `videoUrl` property to `inputFiles` (an array of objects) to support multiple inputs.
2.  **Refactor Mesop Page:**
    *   Add a `me.select` to the test page to allow users to choose the command.
    *   Dynamically update the UI to show the correct number of file choosers based on the selected command.

**Phase 5.2: Implement Video Concatenation**

1.  **Update Lit Component:** Implement the `_concatenateVideos()` function, which will construct and execute the `ffmpeg` command with the `concat` filter.
2.  **Update Mesop Page:** Add UI logic to allow the user to dynamically add and remove video choosers.

**Phase 5.3: Implement Audio Layering**

1.  **Create Audio Chooser:** Create a new `audio_chooser_button.py` component, similar to the video chooser, that filters for `audio/*` mime types.
2.  **Update Lit Component:** Implement the `_layerAudio()` function, which will construct and execute the `ffmpeg` command to combine the video and audio streams.
3.  **Update Mesop Page:** Add the new audio chooser to the UI when the "Layer Audio" command is selected.

---

## Phase 6: Documentation

**Goal:** Document the new component and its usage for future developers.