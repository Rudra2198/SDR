"""The Context API layers (Plane 05, playbook Part 3).

Each live layer is a pure function returning ``(data, source)``; the `ContextAPI`
wraps the payload in a `ContextResult` envelope and traces the call. Keeping the
store access in pure functions (Part 12) keeps the Temporal path open and the
layers independently testable.
"""
