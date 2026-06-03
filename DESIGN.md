---
name: InoLabel
description: Desktop image/video annotation tool — tokens extracted from code.
colors:
  bg: "#F0F4FA"
  panel: "#FFFFFF"
  panel_alt: "#EEF3FB"
  border: "#C2D0E8"
  text: "#152040"
  muted: "#526A88"
  fg_light: "#FFFFFF"
  disabled_fg: "#B8C8DC"
  primary: "#1560BD"
  primary_active: "#0D47A1"
  danger: "#C62828"
  danger_active: "#B71C1C"
  neutral: "#DDE5F0"
  neutral_active: "#C8D4E8"
  accent: "#F07820"
  accent_active: "#D96A10"
  input_bg: "#F8FBFF"
  canvas_bg: "#16130f"
rounded:
  sm: "6px"
  md: "8px"
typography:
  display:
    fontFamily: "Helvetica, Arial, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.1
  heading:
    fontFamily: "Helvetica, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 700
  body:
    fontFamily: "Helvetica, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
  caption:
    fontFamily: "Helvetica, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 400
  mono:
    fontFamily: "Courier, monospace"
    fontSize: "11px"
    fontWeight: 400
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  "2xl": "48px"
sizes:
  sidebar_w: "320px"
  sidebar_min_w: "300px"
  sidebar_max_w: "390px"
  topbar_h: "56px"
  status_h: "40px"
  btn_pad_x: "14px"
  btn_pad_y: "10px"
  btn_h: "44px"
  btn_h_sm: "36px"
  input_pad: "8px"
  content_max_w: "1080px"
  content_min_w: "760px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.fg_light}"
    padding: "10px 14px"
  button-primary-hover:
    backgroundColor: "{colors.primary_active}"
---

# Design System: InoLabel

## 1. Overview

Creative North Star: "The Lab Notebook"

InoLabel is a research-focused, practical annotation tool for students and practitioners. The visual system prioritizes clarity, legibility, and efficient keyboard-driven workflows over decorative flourishes. It supports a neutral canvas for most UI surfaces and a distinct blue primary for actions; the canvas area (image/video preview) intentionally reads dark to maximize contrast with overlays.

Key Characteristics:
- Friendly and practical: unobtrusive UI that keeps the image/video content central.
- Research-focused: exposes state and provenance (undo, autosave, exports) clearly.
- Legible and precise: high text contrast, compact spacing, predictable hierarchy.

## 2. Colors

The palette is neutral and tool-focused: a cool-blue primary (`primary`) for actions, an accent orange for occasional highlights, and a set of neutrals for panels, borders, and muted text.

### Primary
- **Primary (Action Blue)** — `#1560BD`: used for primary action buttons, active controls, and focused states.

### Accent
- **Accent (Orange)** — `#F07820`: used sparingly for warnings, secondary accents, or to call out export/augmentation actions.

### Neutrals
- **Panel / Background** — `#FFFFFF` / `#F0F4FA`: card and app backgrounds.
- **Border** — `#C2D0E8`: subtle separators and input strokes.
- **Text** — `#152040` (body), `#526A88` (muted)

### Canvas
- **Canvas Background** — `#16130f`: the image/video rendering surface; UI overlays use high-contrast light strokes on this surface.

Named Rules
**The One-Voice Rule.** The primary blue is the application's single dominant accent and should be used deliberately (buttons, active states). Avoid introducing additional saturated accents without a clear purpose.

## 3. Typography

Display Font: `Helvetica` (system fallback)
Body Font: `Helvetica` (system fallback)
Mono: `Courier` for code/IDs

Character: utilitarian, compact, and legible — tuned for dense panels and toolbar labels.

### Hierarchy
- **Display / Title** — `Helvetica`, 22px, 700: main dialog titles and the wizard title.
- **Heading** — `Helvetica`, 15px, 700: panel headings and section labels.
- **Body** — `Helvetica`, 12px, 400: primary UI copy (buttons use bold 12px where noted).
- **Caption** — `Helvetica`, 11px, 400: auxiliary labels, tooltips, small UI bits.
- **Mono** — `Courier`, 11px: used for `track_id`, exported metadata previews, and any fixed-width data.

Line length: aim for 65–75ch in rich text areas; UI panels are compact and benefit from tighter measures.

## 4. Elevation

The system is largely flat with tonal layering and subtle borders. Depth is conveyed through panel background shifts and thin separation strokes rather than heavy shadows. The canvas area is visually distinct via a dark background and light overlays.

Named Rules
**Flat-By-Default.** Surfaces are flat at rest; use subtle tonal shifts and 1px separators for layering. Reserve shadows for transient overlays or dialogs only.

## 5. Components

Buttons
- Shape: modest corner radii: `rounded.sm` = 6px for primary controls, `rounded.md` = 8px for cards and containers. Default system controls use native styling for platform parity.
- Primary Button: background `{colors.primary}`, text `{colors.fg_light}`, padding `10px 14px`, border-radius `{rounded.sm}`. Hover uses `{colors.primary_active}`; focus-visible should use an accessible outline (3px solid, translucent primary).

Primary Button example CSS (drop-in):

```css
.ds-btn-primary {
  background: #1560BD;
  color: #FFFFFF;
  padding: 10px 14px;
  border: none;
  border-radius: 6px;
  font-weight: 700;
  transition: background 200ms cubic-bezier(0.2,0,0,1), transform 150ms;
}
.ds-btn-primary:hover { background: #0D47A1; transform: translateY(-1px); }
.ds-btn-primary:focus-visible { outline: 3px solid rgba(21,96,189,0.12); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { .ds-btn-primary { transition: none; transform: none; } }
```

Inputs / Fields
- Background: `{colors.input_bg}`; border: `1px solid {colors.border}`; inner padding: `{sizes.input_pad}`; border-radius `{rounded.sm}`.

Input example CSS:

```css
.ds-input { background: #F8FBFF; border: 1px solid #C2D0E8; padding: 8px; border-radius: 6px; }
.ds-input:focus-visible { border-color: #1560BD; box-shadow: 0 0 0 4px rgba(21,96,189,0.08); outline: none; }
```

Sidebar
- Fixed width: `{sizes.sidebar_w}`; sections use `heading` typographic style and compact spacing between controls. Use subtle separators (`border-right:1px solid {colors.neutral}`) rather than heavy shadows.

Card example CSS:

```css
.ds-card { background: #FFFFFF; border: 1px solid #EEF3FB; border-radius: 8px; padding: 16px; }
.ds-card h3 { margin: 0 0 8px 0; }
```

Canvas Overlays
- Overlays (bboxes, ROI markers) are high-contrast strokes on the dark `{colors.canvas_bg}`; avoid relying on filled tints for status — prefer stroked outlines and badges with background tokens when needed.

### Toasts (Transient notifications)
- Usage: small, self-dismissing banners for confirmations and errors.
- Success: green-tinted background, subtle shadow, concise copy.
- Error: red-tinted background; include a clear action where appropriate.

Example CSS:

```css
.ds-toast { display:flex; gap:8px; align-items:center; padding:10px 14px; border-radius:6px; font-family: Helvetica, Arial, sans-serif; }
.ds-toast-success { background:#E8F7EF; color:#0B6B3A; box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
.ds-toast-error { background:#FBEAEA; color:#7A1212; }
```

### Modal / Dialog
- Usage: confirm destructive actions, multi-step export flows, or settings dialogs. Centered, with a translucent backdrop. Modals trap focus and provide clear primary/secondary actions.

Example CSS excerpt:

```css
.ds-modal-backdrop { position:fixed; inset:0; display:flex; align-items:center; justify-content:center; background: rgba(0,0,0,0.35); }
.ds-modal { width:560px; background:#FFFFFF; border-radius:8px; padding:20px; }
```

### Tooltip
- Usage: short helper text on hover/focus. Keep copy to 1–3 words where possible.

Example CSS:

```css
.ds-tooltip { background:#152040; color:#FFFFFF; padding:6px 8px; border-radius:6px; font-size:11px; }
```

### Badge / Chip
- Usage: compact labels for classes, tags, and filters. Use bold label text, high-contrast outline or tinted background.

Example CSS:

```css
.ds-chip { background:#EEF3FB; color:#1560BD; padding:4px 8px; border-radius:999px; font-weight:700; }
```

### Toggle / Switch
- Usage: binary settings inside sidebars or dialogs. Use `aria-pressed` for state and animate knob position; respect reduced-motion.

Example CSS:

```css
.ds-toggle { width:44px; height:24px; background:#DDE5F0; border-radius:999px; }
.ds-toggle[aria-pressed="true"] { background:#1560BD; }
```

### Dropdown / Menu
- Usage: compact contextual actions. Menus should be keyboard-navigable and dismiss on outside click or escape.

Example CSS:

```css
.ds-menu { position:absolute; background:#FFFFFF; border:1px solid #C2D0E8; border-radius:6px; }
.ds-menu-item { padding:8px 12px; }
.ds-menu-item:hover { background:#EEF3FB; }
```

## 6. Do's and Don'ts

Do:
- **Do** use `{colors.primary}` for primary actions and active states only.
- **Do** keep body text at high contrast (`{colors.text}` on `{colors.panel}`) to meet accessibility targets.
- **Do** provide keyboard focus indicators and respect `prefers-reduced-motion`.

Don't:
- **Don't** use side-stripe borders (no `border-left` >1px as an accent). Use background tints or full borders instead.
- **Don't** use gradient text or decorative gradient headings.
- **Don't** rely on color alone for status; always include a shape, icon, or label.
- **Don't** allow headline overflow — test long labels at smaller widths and reduce clamp/max sizes if needed.

***

This DESIGN.md is generated from the code tokens in `app/ui/theme/tokens.py`. Ask if you want tighter radii tokens, an expanded shadow vocabulary, or explicit component HTML/CSS snippets in `.impeccable/design.json`.
