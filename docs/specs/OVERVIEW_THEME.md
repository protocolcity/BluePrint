# Shared visual system

The active operations app owns the design tokens in `overview/v1/static` and
the shared Map styles. Use those files as the implementation source of truth.
The current register is a restrained dark operations interface: near-black
surfaces, readable compact type, a quiet accent and semantic state colors.

Prioritize hierarchy, legibility and consistent interaction over decoration.
Use the existing font stack, spacing, borders, focus treatments and readers.
Do not introduce a competing palette or restore older cream/paper concepts.

Overview, Work, Projects, Agents, Delivery/Timeline, Map, Calendar, Connections
and Settings share chrome and vocabulary. Distinguish unavailable, stale, empty
and healthy states with text as well as color. Motion follows real interactions
and content changes, respects reduced-motion preferences, and never simulates
work or presence.

Verify desktop/narrow layouts, keyboard navigation, focus restoration, contrast,
loading/error states and long labels against the actual app. Token changes need
a rationale and comparison across surfaces. See [operations design](OPERATIONS_EVOLUTION_2026_09.md).
