# POS: add color picker in POS UI to change global POS theme color

## Goal
Provide a simple POS-side color picker so a user can pick the POS UI primary color (color plate). When the color is changed from any POS session, the new color should be persisted and reflected across all POS sessions (other open POS clients should update within a short interval).

## Requirements
- Backend:
  - Add a persistent field `pos_theme_color` to `res.company` to store the chosen color (hex string).
  - Expose the field in company settings (optional).
- POS frontend:
  - Add a color-picker button in the POS UI (top bar).
  - When the user chooses a color, write it to `res.company` (RPC).
  - Apply the color immediately to the current POS UI (CSS variable or injected style).
  - Ensure other open POS sessions pick up the update within a short delay (polling or bus notifications). Initial implementation will use polling; bus notifications can be added later for instant push updates.
- Assets and packaging:
  - New module `pos_ui_color` (installable, depends on `point_of_sale`).
  - Provide a simple validation procedure: open multiple POS sessions, change color in one, verify others update within ~5s.

## Acceptance criteria
- User can open POS UI, click the color button, choose a color from a color plate, and apply it.
- The selected color is saved to the company record and becomes the primary color used by POS UI (buttons / header).
- Other open POS sessions update to the chosen color automatically within a few seconds.

## Manual test steps
1. Install `pos_ui_color` module.
2. Open POS in two different browser windows (same company).
3. Click the paintbrush color button in one window, pick a new color and apply.
4. Confirm the color immediately changes in the current session and the second session reflects the change within ~5s.

---