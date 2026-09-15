# Current route decision

1. User requires data/diagram objects editable: native.
2. User explicitly requests generated baked slide imagery: image-deck, then text-editable only when ordinary text editing is requested.
3. Input is existing slide images and ordinary text editing is the goal: text-editable.
4. Otherwise: native.

NotebookLM is an explicitly selected source, not a competing mandatory output. Current host authoring contract chooses the implementation backend. Formal/company defaults do not override the user's explicit image-only scope.
