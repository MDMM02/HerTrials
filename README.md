# HerTrials 🩷  
A lightweight PubMed trial explorer that lets you search a topic, store results in a Postgres database (Neon), and generate **3 on-demand summaries** per record:
- **A — Scientific summary**
- **B — Layman summary (simple, no acronyms, no trial design jargon, avoid numbers)**
- **C — Children summary (very simple, friendly, short)**

Built with **FastAPI + SQLAlchemy + Jinja templates**, and uses **Ollama (local LLM)** for summaries.

---

## Features
- 🔎 Search PubMed by topic/keywords
- 🧾 Persist records (title, abstract, year, PMID, source, URL) in Postgres
- ✨ One-click summary generation (A/B/C) per record
- ♻️ Caches summaries in DB so you don’t regenerate every time
- 🎀 Simple HTML frontend (Jinja) + customizable CSS theme

---

## Tech Stack
- **Backend:** FastAPI, Uvicorn
- **Database:** Postgres (Neon) + SQLAlchemy
- **Templates:** Jinja2 (HTML pages)
- **Summaries:** Ollama (local) via Python client
- **Optional legacy:** HuggingFace Pegasus (older path; can be removed if using Ollama only)

---
