# Add POS UI Color picker

## Summary
Adds a new Odoo addon `pos_ui_color` that provides a POS color picker stored on `res.company.pos_theme_color` and applies the selected color across POS sessions.

## What it includes
- Backend model extension: `res.company.pos_theme_color` (char, hex color).
- Company view field to set default color (color widget).
- Frontend assets: JS, XML templates and CSS to add a color-picker button in the POS top bar, a color picker popup, and apply the chosen color via a CSS variable.
- Simple polling-based synchronization (5s) so other open POS sessions pick up changes.
- Issue markdown at `.github/ISSUES/pos_ui_color_issue.md` with requirements, acceptance criteria, and manual test steps.

## Installation & testing
1. Ensure this branch is available on the server: `feature/pos-ui-color-picker`.
2. Restart Odoo and update Apps list.
3. Install the "POS UI Color" module.
4. Open two POS sessions (same company) in different browsers or tabs.
5. Click the paintbrush color button in one POS, choose a color and Apply.
6. Confirm the current session updates immediately and the other session reflects the change within ~5s.

## Notes
- The implementation uses a 5s polling loop for simplicity. If you prefer immediate push updates, we can implement server-side bus notifications to broadcast changes when `res.company.pos_theme_color` is written.
- Feel free to adjust default color, CSS selectors to style additional elements, or to move the company field to a different backend view.
