# Web App Mobile Reader Stabilization

## Summary

Refactor the web app so recipe routes behave like a full-page reader on mobile and a stable split-pane detail view on desktop. Remove the mobile modal assumption, guard card taps against scroll gestures, soften cookbook nav sync during smooth scrolling, and refresh the UI toward a warmer editorial look.

## Implementation

- Add a small pure interaction helper module for viewport checks, card tap heuristics, and cookbook nav suppression timing.
- Update the recipe library so touch/pen interactions open cards only for true taps; scrolling over cards must not open recipes.
- Render recipe detail as:
  - mobile: full-page reader with explicit back navigation
  - desktop: in-place detail pane with close/back control
- Restrict card morph animation to desktop only.
- Reduce nested scroll containers on mobile and avoid overlay/backdrop scrolling conflicts.
- Refresh web app tokens and card/detail styling to align the library with the existing cookbook reader aesthetic.

## Acceptance

- On mobile, tapping a card opens the matching recipe and vertical swipes do not open any recipe.
- Returning from a mobile recipe preserves the previous list search/filter state and scroll position.
- Cookbook nav smooth scrolling does not cause active-link flicker or obvious scroll fighting.
- Desktop recipe detail remains usable and keyboard accessible.
- The app bundle still builds from `templates/webapp/` and existing web output structure remains unchanged.
