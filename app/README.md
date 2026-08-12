---
title: Leibniz — Universal Calculator for Truth
emoji: 🧮
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# Leibniz 🧮

**A three-stage LLM-driven mathematical discovery & proof-checking engine**, realizing Leibniz's 400-year-old vision of a *universal calculator for truth*.

Two modes, running on the **free CPU tier** (StubBackend — no model needed):

- **Discovery Playground**: seed a topic → generate conjectures → auto-prove → verify
- **Proof Reviewer**: paste a theorem + proof → 3-gate review (validity, alignment, graded reading)

Set `LEIBNIZ_API_URL` to point at a deployed API host for real-model inference.
