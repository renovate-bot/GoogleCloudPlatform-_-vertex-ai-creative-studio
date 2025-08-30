### Plan: Advanced Chirp3 HD Features

#### Feature 1: Audio Configuration Sliders

1.  **Backend (`models/chirp_3hd.py`):**
    *   Update the `synthesize_chirp_speech` function to accept new float parameters: `speaking_rate`, `pitch`, and `volume_gain_db`.
    *   Pass these new parameters into the `texttospeech.AudioConfig` object.

2.  **Frontend (`pages/chirp_3hd.py`):**
    *   Add `speaking_rate: float`, `pitch: float`, and `volume_gain_db: float` to the `Chirp3hdState` class with the specified default values.
    *   In the UI, add a new row with three `me.slider` components for Pace, Pitch, and Volume, configured with the correct min/max values.
    *   Create `on_change` event handlers for each slider to update the state.
    *   Update the `on_click_generate` handler to pass the new state values to the backend function.
    *   Update the `on_click_clear` handler to reset these new state values.

#### Feature 2: Custom Pronunciations

1.  **Backend (`models/chirp_3hd.py`):**
    *   Update the `synthesize_chirp_speech` function to accept a new list parameter, `pronunciations`.
    *   Inside the function, if the list is provided, it will loop through it to create a list of `texttospeech.CustomPronunciation` objects.
    *   This list will then be passed as the `custom_pronunciations` argument to the main `client.synthesize_speech` request.

2.  **Frontend (`pages/chirp_3hd.py`):**
    *   Add the following to `Chirp3hdState`:
        *   `custom_pronunciations: list[dict]` to store the list of added phrase/pronunciation pairs.
        *   `current_phrase_input: str` and `current_pronunciation_input: str` to hold the values from the text inputs.
    *   In the UI, add a new "Custom Pronunciations" section with inputs for "Phrase" and "Pronunciation", and an "Add" button.
    *   Below the inputs, dynamically render the list of added pronunciations, with a "Remove" button for each.
    *   Create `on_add_pronunciation` and `on_remove_pronunciation` event handlers to manage the list in the state.
    *   Update the `on_click_generate` and `on_click_clear` handlers to manage and pass the new state.
