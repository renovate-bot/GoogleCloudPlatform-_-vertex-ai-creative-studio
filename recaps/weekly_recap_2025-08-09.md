# Weekly Recap: August 9, 2025

This week saw significant enhancements to the Motion Portraits and Character Consistency features, a major refactor of the Virtual Try-On (VTO) workflow, and the introduction of a new testing framework.

## Key Highlights

*   **Motion Portraits:** You can now dynamically select the VEO model for generating motion portraits, and the results are displayed in a more user-friendly grid layout.
*   **Character Consistency:** The video prompt for character consistency has been improved, and the UI now shows the analysis status.
*   **Virtual Try-On (VTO):** The VTO workflow has been completely overhauled with a new virtual model generator and a dedicated test page. Error handling has also been improved.
*   **Testing:** A new test page index has been created to make it easier to find and run tests.

## Detailed Changes

### Motion Portraits

*   `305ac07` - refactor(v.next): adjustments to qol
*   `0286b2d` - feat(portraits): Add dynamic VEO model selection and grid layout
*   `02f5788` - feat(v.next): enhance motion portraits

### Character Consistency

*   `8183dcb` - feat(character_consistency): enhance video prompt and show analysis status
*   `cb2d9cc` - feat(testing): Enhance character consistency test page
*   `b3a561c` - feat(testing): Enhance character consistency test page

### Testing

*   `4a08e55` - feat(testing): Create test page index and enhance test pages

### Virtual Try-On (VTO)

*   `5cea735` - refactor(v.next): limits original images in generation step, fixes #458
*   `1143489` - fix(data): Prevent auto-saving of virtual models to library
*   `04f9039` - feat(vto): Enhance and unify virtual model generation
*   `06f4c9b` - refactor: vto model preview
*   `315b80b` - feat(vto): Create virtual model generator and test page
*   `308a35e` - feat(vto): Implement error handling dialog for VTO page
*   `899980c` - fix: fixes #438

### Library

*   `cfc31f9` - feat(library): Add 'Mine vs. All' user filter

### Promptlandia

*   `df23395` - feat(experiments): Add Promptlandia and refactor README

### Other Changes

*   `6bc0b41` - feat: Add CODEOWNERS to define code ownership
*   `e1d1b63` - feat: Add CODEOWNERS to define code ownership
*   `999a954` - feat(ui): Add placeholder tiles for new workflows
*   `5034d36` - refactor: updates Imagen fast model fixes #447
*   `351344a` - refactor: updates Imagen fast model fixes #447
*   `30f4929` - doc: updates developers guide
*   Multiple dependency updates

