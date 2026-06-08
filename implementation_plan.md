# Praxis UI Revamp Plan

This plan details the steps to elevate the Praxis frontend UI from its current "API Test Interface" aesthetic to a premium, professional-grade platform. The focus will be on a modern dark theme featuring glassmorphism, vibrant accent gradients, polished typography, and dynamic micro-animations—without breaking any existing functionality.

## Goal
To deliver a visually stunning, responsive, and dynamic user interface using Vanilla CSS and React inline styling, avoiding external UI frameworks like Tailwind (as per project guidelines) while still achieving a high-end look and feel.

## Proposed Changes

### 1. Global Design System (`index.css` & `index.html`)
We will introduce a central `index.css` file to define a cohesive design system using CSS variables.
- **Typography:** Import the `Inter` font from Google Fonts for a sleek, modern look.
- **Color Palette:**
  - **Backgrounds:** Deep, rich dark backgrounds (`#0B0C10`, `#1F2833`) replacing the flat blacks.
  - **Accents:** Vibrant gradients (e.g., Indigo to Purple, Teal to Cyan) for buttons and active states.
  - **Text:** High-contrast whites for primary text, soft slates for secondary.
- **Glassmorphism:** Utility classes for frosted glass effects (`backdrop-filter: blur()`, semi-transparent backgrounds with subtle borders).
- **Animations:** Define keyframes for smooth fade-ins, slide-ups, and pulsing effects.

#### [NEW] `frontend/src/index.css`
Will contain CSS reset, typography, variables, scrollbar styling, and utility animation classes.

#### [MODIFY] `frontend/index.html` & `frontend/src/main.jsx`
Update `index.html` to load the `Inter` font. Import `index.css` in `main.jsx`.

---

### 2. Upgrading UI Core Components (`ui.jsx`)
The `ui.jsx` file is the backbone of the current frontend. By upgrading these components, the entire app will immediately look better.
- **`Card`:** Apply glassmorphism styling (semi-transparent dark background, subtle border, backdrop blur, soft box-shadow). Add a hover lift effect.
- **`Btn`:** Switch to vibrant gradient backgrounds for primary actions. Add hover state transformations (scale up slightly, increase brightness) and active state press animations.
- **`Input` / `Textarea` / `Select`:** Add focus rings (glow effect) using accent colors, smooth transition on focus, and softer background colors.
- **`Badge` & `Alert`:** Softer background opacities with crisp, saturated text colors. Add entry animations.

#### [MODIFY] `frontend/src/components/ui.jsx`
Rewrite inline styles to consume CSS variables and add CSS classNames for animations where necessary.

---

### 3. Layout & Navigation (`App.jsx` & `Auth.jsx`)
- **`App.jsx`:** 
  - Redesign the top navigation bar into a floating, glassmorphic header.
  - Replace the plain text tabs with beautifully styled, pill-shaped or animated underline tabs with smooth transitions.
  - Apply a subtle animated gradient background or mesh gradient to the main `body`/`root` to give depth to the application.
- **`Auth.jsx`:**
  - Center the authentication form in a polished, floating glass card.
  - Add a stylized hero background or gradient mesh for the login page.

#### [MODIFY] `frontend/src/App.jsx`
#### [MODIFY] `frontend/src/components/Auth.jsx`

---

### 4. Polishing Specific Views
While `ui.jsx` handles most of the work, some views have custom inline styles that need tweaking to match the new design system.
- **`Jobs.jsx`:** Ensure the job cards look like premium interactive elements. Add hover effects to the suggestion pool items.
- **`Chat.jsx`:** Enhance the chat bubbles. User messages get a primary gradient background; AI messages get a glassmorphic dark container. Add entry animations for new messages.
- **`Notifications.jsx`:** Refine the live feed and notification items to have smooth hover states and distinct unread indicators.

#### [MODIFY] `frontend/src/components/Jobs.jsx`
#### [MODIFY] `frontend/src/components/Chat.jsx`
#### [MODIFY] `frontend/src/components/Notifications.jsx`

---

> [!IMPORTANT]
> **User Review Required**
> Do you have any specific color preferences (e.g., sticking to deep purple/indigo, or shifting to another primary color like emerald or ocean blue)? Would you like to proceed with the proposed custom CSS/glassmorphism approach?

## Verification Plan
### Manual Verification
- Start the frontend dev server (`npm run dev`).
- Navigate through all tabs (Auth, Jobs, Chat, CV, etc.) to ensure layout is intact.
- Test interactive elements (hovering buttons, focusing inputs, opening modals) to confirm smooth animations.
- Verify that the websocket notification updates (live feed) continue to work seamlessly without visual breakage.
