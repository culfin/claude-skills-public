# Product quality checks

Apply these as contextual checks, not mandatory feature requests. Inspect shared components once and verify representative usages; expand coverage for systemic defects.

## Journeys and states

Define critical journeys from product purpose: first useful outcome, search/detail, create/edit, or checkout as applicable. Record tested routes, roles, data conditions, and expected outcomes.

- Buttons, links, tabs, filters, sorting, settings, and navigation produce the promised result. Prioritize critical and distinct interactions rather than blindly clicking every control.
- Back, reload, and deep links behave sensibly; relevant shareable view state survives in the URL.
- Loading, empty, first-run, success, validation, expired-session, permission-denied, missing-resource, and failure states provide a useful next action.
- Timeouts, retries, offline conditions, and partial failures do not strand the user or destroy unsaved input.
- Destructive actions have a proportionate confirmation or undo mechanism.
- Mutations persist after reload; optimistic updates roll back on failure; delayed responses do not overwrite newer state.
- Error boundaries prevent avoidable full-screen failures and keep stack traces/internal details out of user-facing responses. Generic wording can be appropriate for security-sensitive errors; actionable recovery should remain available.

## Forms

- Server-side validation enforces trusted constraints; client validation provides compatible feedback. Do not require identical rules where server-only business checks are needed.
- Labels, accessible error association, input types, autocomplete, inputmode, and password-manager behavior fit the task.
- Pending submissions are guarded; server-side duplicate protection exists where repeated requests have consequential effects.
- Failed requests preserve recoverable input. Limits are meaningful and locale-aware.
- Mobile keyboard, zoom, and focus behavior are tested where possible. Avoid disabling browser zoom.

## Accessibility

Use applicable WCAG criteria as the standard; automated scans supplement manual verification.

- Keyboard access, logical focus order, visible and unobscured focus, and a usable route past repeated navigation.
- Appropriate semantics, landmarks, descriptive accessible names, and a meaningful heading hierarchy.
- Useful image alternatives, appropriate contrast, and information conveyed beyond color.
- Dialog focus management and dismissal fit the interaction; async announcements inform without excessive interruption.
- Reduced-motion preferences, zoom/reflow, and high-contrast modes work on important flows.
- WCAG 2.2 AA target-size minimum is 24 × 24 CSS pixels with specified exceptions; 44 × 44 is a useful stronger usability target, not a universal AA minimum.
- Automated success is not a full accessibility conformance claim. Document manual and assistive-technology coverage separately.

Reference when needed: https://www.w3.org/TR/WCAG22/

## Responsive and browser coverage

Choose a manageable matrix from supported audience and layout breakpoints. Start with a narrow phone, a desktop, and a breakpoint-sensitive intermediate width; add landscape, wide screens, browsers, and real devices when risk warrants it. Do not label desktop viewport emulation as a real-device test.

Check long content, unbroken strings, text expansion, empty/large datasets, zoom/reflow, touch interactions, keyboard overlap, safe areas, overlays, and tables. Identify unintended horizontal overflow without banning intentionally scrollable tables or canvases. Record browsers actually tested; do not assume one engine proves all engines.

## Design and content

Preserve intentional brand decisions. Compare spacing, typography, component states, colors, icon treatment, layering, and dark mode against existing tokens and patterns. Recommend consolidation only where inconsistency creates meaningful friction or maintenance cost.

Gradients, cards, emojis, asymmetric spacing, and animations are not defects by themselves. Explain any criticism through readability, task clarity, accessibility, consistency, brand fit, or distracting repetition. Avoid redesigning the app to match the agent's aesthetic preferences.

Check concrete copy, consistent language/tone, correct locale formatting, meaningful labels, and honest calls to action. Distinguish unfinished placeholders from intentional examples.

Treat unsupported testimonials, invented metrics, misleading partner claims, and advertised-but-missing functionality as content-credibility findings. If provenance is unknown, request evidence rather than asserting fabrication or inventing replacements.
