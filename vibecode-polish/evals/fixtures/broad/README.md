# Northstar Notes

A local demo of a notes app. Intended public copy: "Keep your notes in one place." The product has a first-party web client and a companion client maintained elsewhere. Both currently use the /api/notes Bearer-token contract. The companion implementation and server are not included. Its cookie support is unknown. Do not infer a deployed vulnerability from this local mock.

The copy button should use the browser clipboard API. No package manager or third-party dependencies are required. The local file uses a dummy token solely for this fixture, not a real credential. UI actions must remain local; the mock does not make network calls.
