# Run, Veo, Run - Developer Context & Conventions

This `GEMINI.md` file defines the context, technology stack, and coding conventions for the "Run, Veo, Run" project. Use this information to guide all code modifications and architectural decisions.

## 1. Project Overview
"Run, Veo, Run" is a real-time, multimodal web application that allows users to extend videos using Vertex AI's Veo 3.1 model. The application features a "Techno-Brutalist" aesthetic inspired by the movie "Run, Lola, Run".

-   **Goal:** Upload video -> Extend with Veo 3.1 + Prompt -> Repeat (Looping).
-   **Architecture:** Client-Server-Cloud (Frontend -> Go Proxy -> GCP APIs).
-   **Key Services:**
    -   **Vertex AI (Veo 3.1):** `veo-3.1-fast-generate-preview` for video extension.
    -   **Vertex AI (Gemini 2.5):** `gemini-2.5-flash` for prompt enhancement.

## 2. Technology Stack & Conventions

### Backend (Server)
-   **Language:** Go (v1.25.2+)
-   **Location:** `server/` directory.
-   **Entry Point:** `server/main.go`.
-   **Reference:** This project uses patterns from the `scream` project (sister project). Refer to `scream` for architectural guidance if not explicitly defined here.
-   **Key Libraries:**
    -   **GenAI:** `google.golang.org/genai`
    -   **WebSockets:** `github.com/gorilla/websocket`
    -   **Firebase:** `firebase.google.com/go` (Server-side auth)
-   **Conventions:**
    -   **API Endpoints:**
        -   `/api/config`: Returns frontend configuration.
        -   `/api/veo/generate`: Text-to-Video generation (POST).
        -   `/api/veo/extend`: Video-to-Video extension (POST).
    -   **Proxy Pattern:** The server acts as a proxy for GCP credentials; the frontend NEVER calls GCP APIs directly.
    -   **Config:** Configuration is loaded via `internal/config/config.go` from environment variables.
    -   **Run:** Use `go run main.go` to run locally (Port 8080).
    -   **Environment Variables:**
        -   Use `.env` for local secrets (gitignored).
        -   Use `sample.env` for documenting required variables.
        -   The `server/internal/config` package is the only place env vars should be read.

### Frontend (Client)
-   **Framework:** Lit (Web Components) & TypeScript.
-   **Location:** `frontend/` directory.
-   **Build Tool:** Vite.
-   **Key Libraries:**
    -   **UI:** `@material/web` (Material Design 3 tokens & components).
    -   **Styling:** Tailwind CSS + Custom Material Design Token Overrides ("Theme Adapter").
    -   **State:** `@lit/context` for global state.
-   **Conventions:**
    -   **Theme:** "Lola Red" (#FF2400) and "Concrete Dark" (#1A1A1A).
    -   **Typography:** 'Oswald' (Headers) and 'JetBrains Mono' (Data).
    -   **Run:** Use `npm run dev` to run locally (Port 5173).

## 3. Development Workflows

### Task Management (`bd`)
We use the `bd` (Beads) tool for **all** issue tracking and planning. Do not use the `write_todos` tool for project-level planning.

*   **Project Prefix:** `run-veo-run`
*   **Workflow:**
    1.  **Check Work:** `bd ready`
    2.  **Create Task:** `bd create "Title" -t task --priority 0`
    3.  **Break Down Work:** For complex features, create multiple smaller tasks and link them:
        *   `bd create "Subtask 1"`
        *   `bd dep add <parent-id> <subtask-id>` (Parent depends on Subtask)
    4.  **Sync Fix:** If `bd sync` fails due to prefix mismatch, use `bd sync --rename-on-import`.
    5.  **Update Status:** `bd update <id> --status in_progress`
    6.  **Close:** `bd close <id>`

    *   **Release Management:**
        *   **Changelog Generation:** Run this command to generate `CHANGELOG.md` from closed tasks:
            ```bash
            bd list --status closed --json | jq -r 'sort_by(.closed_at) | reverse | map(select(.closed_at != null)) | group_by(.closed_at[0:10]) | reverse | .[] | "## " + (.[0].closed_at[0:10]) + "\n" + (map("- " + .title + " (" + .id + ")") | join("\n")) + "\n"' > CHANGELOG.md
            ```

### Local Development
To run the full stack locally:
1.  **Backend:** `cd server && go run main.go` (Runs on port 8080).
2.  **Frontend:** `cd frontend && npm install && npm run dev` (Runs on port 5173).
3.  **Unified Build & Run:** Use `./build-run.sh` in the root (builds frontend to `server/dist` and runs server on port 8080).

### Deployment
*   **Infrastructure Setup:** Run `./setup-sa.sh` once to create the dedicated Service Account (`sa-run-veo-run`) and assign necessary roles (Vertex AI User, Storage Object User, Logging).
*   **Deploy to Cloud Run:** Use `./deploy.sh`. This uses the SA created above by default. You can override it by setting `export SERVICE_ACCOUNT_EMAIL=...`.

## 4. Design Guidelines ("Techno-Brutalist")

### Visual Vibe
*   **Palette:**
    *   Primary: Shock Red (`#FF2400`)
    *   Background: Concrete Dark (`#1A1A1A`)
    *   Surface: Asphalt (`#2D2D2D`)
    *   Accent: Caution Yellow (`#FFD700`)
*   **Shapes:** Sharp edges (`0px` border-radius) replacing standard rounded Material Design.
*   **Typography:** Distressed Sans-Serif (Headers) & Monospace (UI/Data).

### Implementation Strategy (Global Override)
We use a global CSS file (`frontend/src/theme.css`) to map Tailwind colors to Material Design System tokens.

**Token Mapping:**
```css
:root {
    --md-sys-color-primary: #FF2400; 
    --md-sys-color-background: #1A1A1A;
    --md-sys-shape-corner-small: 0px;
    --md-sys-shape-corner-full: 0px; 
    /* ... see frontend/src/theme.css for full map */
}
```

## 5. Operational Rules for the Agent

1.  **Path Verification:** Always construct absolute paths. Verify `server/go.mod` and `frontend/package.json` locations before running commands.
2.  **Tool Usage:**
    *   Use `read_file` (not `default_api:read_file`).
    *   Use `bd` for all task tracking.
3.  **Refactoring:**
    *   When adding new UI components, always create a corresponding `customElement` in `frontend/src/` and import it in `index.html` or the parent component.
    *   Ensure all new components adhere to the `run-veo-run` tag naming convention.
4.  **Security:**
    *   Do not commit secrets.
    -   Use `server/internal/config` for all env var access.
5.  **Instruction Files:** Always check `docs/instructions/` for specific API guides (e.g., `veo-3.1-guide.md`, Gemini) before implementation. These contain authoritative request/response formats.

## 6. Infrastructure Standards
*   **Service Accounts:** Do not use default compute SAs. Create dedicated SAs using a `setup-sa.sh` script (see project root) and assign minimal required roles.
*   **Environment:** Use `.env` (gitignored) for local configuration and `sample.env` for documentation.

## 7. Known Limitations & Workarounds
*   **GenAI Go SDK (v1.39.0+):**
    *   **Veo LRO Polling:** The `GenerateVideosOperation` struct has no `.Wait()` method. You must implement manual polling using `client.Operations.GetVideosOperation(ctx, op, nil)`.
    *   **Backend Config:** You must explicitly set `Backend: genai.BackendVertexAI` in `ClientConfig` to use Vertex AI models; it defaults to Gemini API.
    *   **Struct Naming:** Field names often use caps (e.g., `OutputGCSURI`, `MIMEType`) differing from REST JSON keys. Check `go doc` if unsure.