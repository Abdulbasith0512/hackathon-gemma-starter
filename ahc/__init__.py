"""Asset Intelligence Copilot: evidence-first analytics over oil-well records, manuals and notes.

Layers (each independent of the next):
  ingest / db   documented dataset folders -> SQLite (with provenance)
  rules         thresholds and deadlines read from the manuals and SOPs
  store         shared corrections, rules, notes and per-user memory (auditable, persistent)
  analyst       deterministic, cited calculations (the only code that does arithmetic)
  agent         Gemma picks tools and explains tool results; it never calculates
  server        FastAPI + a static front-end
"""
