# Test Plan

This document outlines the tests to be performed to validate the recent refactoring and feature additions.

## 1. Core Functionality (Regression Testing)

The goal here is to confirm that the refactoring and cleanup work did not introduce any side effects.

*   **Test A: Compile All Services**
    *   **Action:** From the `/Users/ghchinoy/dev/vertex-ai-creative-studio-public/experiments/mcp-genmedia/mcp-genmedia-go/` directory, run `go install ./...`.
    *   **Expected Outcome:** All services (`mcp-avtool-go`, `mcp-chirp3-go`, `mcp-imagen-go`, `mcp-lyria-go`, `mcp-veo-go`) should compile without any errors. This will confirm the final code state is valid.

*   **Test B: Verify Lyria Service**
    *   **Action:** Run the `mcp-lyria-go` service and call the `lyria_generate_music` tool with a simple prompt.
    *   **Expected Outcome:** The tool should generate music successfully. This verifies that refactoring the configuration (removing `LyriaLocation`, etc.) and moving its constants into the service worked correctly.

*   **Test C: Verify Imagen & VEO Services (Default Mode)**
    *   **Action:** **Without** setting the `VERTEX_API_ENDPOINT` environment variable, run `mcp-imagen-go` and `mcp-veo-go` individually. Call their respective tools (`imagen_t2i` and `veo_t2v`).
    *   **Expected Outcome:** Both services should work correctly, using the standard production Google Cloud endpoints. This confirms the client initialization logic works correctly when no override is present.

## 2. New Feature Testing

The goal here is to confirm the new custom endpoint feature works as designed.

*   **Test D: Verify Imagen & VEO with Custom Endpoint**
    *   **Action:**
        1.  Set the environment variable with the **full URL**:
            ```bash
            export VERTEX_API_ENDPOINT="https://us-central1-autopush-aiplatform.sandbox.googleapis.com/"
            ```
        2.  Run `mcp-imagen-go` and `mcp-veo-go` again.
        3.  Check the startup logs for the message: `Using custom Vertex AI endpoint: ...`
        4.  Call the `imagen_t2i` and `veo_t2v` tools.
    *   **Expected Outcome:** The services should start, log the custom endpoint message, and successfully process requests by sending them to the specified sandbox URL. The "unsupported protocol scheme" error should be gone.
