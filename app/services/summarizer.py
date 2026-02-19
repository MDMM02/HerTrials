# app/services/summarizer.py

import os
import re
from typing import Literal, Optional

import ollama

Mode = Literal["scientific", "layman", "children"]

# Choose your local Ollama model (must be pulled already)
# Examples: "mistral", "llama3.1:8b", "qwen2.5:7b-instruct"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# If your Ollama server is not on default host/port, set:
#   setx OLLAMA_HOST "http://127.0.0.1:11434"
# or in PowerShell:
#   $env:OLLAMA_HOST="http://127.0.0.1:11434"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def _clean_input(text: str) -> str:
    """Cleans raw abstract text before sending to LLM."""
    if not text:
        return ""
    t = text

    # Common artifacts
    t = t.replace("<n>", " ").replace("</n>", " ")
    t = t.replace("\u00a0", " ")  # non-breaking space
    t = re.sub(r"\s+", " ", t).strip()

    # If abstract contains weird separators, normalize lightly
    t = t.replace("Objectives", "Objectives: ")
    t = t.replace("Methods", "Methods: ")
    t = t.replace("Results", "Results: ")
    t = t.replace("Conclusions", "Conclusions: ")
    return t


def _post_clean_output(text: str, mode: Mode) -> str:
    """Extra safety net to enforce constraints for layman/children."""
    if not text:
        return text

    t = text.strip()

    # Remove any remaining <n> artifacts
    t = t.replace("<n>", " ").replace("</n>", " ")

    if mode in ("layman", "children"):
        # Remove bracket/parenthesis content (often acronyms/doses)
        t = re.sub(r"\([^)]*\)", "", t)
        t = re.sub(r"\[[^\]]*\]", "", t)

        # Remove acronyms (2+ uppercase letters)
        t = re.sub(r"\b[A-Z]{2,}\b", "", t)

        # Remove numbers, percentages, dose schedules, units
        t = re.sub(r"\b\d+(\.\d+)?\b", "", t)
        t = re.sub(r"\b\d+(\.\d+)?%\b", "", t)
        t = re.sub(r"\b(μg|ug|mg|g|kg|ml|mL|h|hr|day|days|week|weeks|month|months)\b", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\b\d+(\.\d+)?\s*/\s*\d+(\.\d+)?\b", "", t)  # like 28/43

        # Remove trial-design jargon if it slipped in
        banned = [
            "randomized", "placebo", "endpoint", "phase", "single-arm", "prospective",
            "double-blind", "open-label", "simon", "two-stage", "confidence interval",
            "statistically significant", "p value", "p-value", "odds ratio"
        ]
        pattern = r"\b(" + "|".join(re.escape(w) for w in banned) + r")\b"
        t = re.sub(pattern, "", t, flags=re.IGNORECASE)

        # Normalize spaces/punctuation
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"\s+([,.;:!?])", r"\1", t)
        t = re.sub(r"\.{2,}", ".", t)

    return t.strip()


def _ollama_chat(system: str, user: str, max_tokens: int, temperature: float) -> str:
    """
    Calls Ollama local server.
    """
    # The python package uses OLLAMA_HOST env var; we set it to be safe.
    os.environ["OLLAMA_HOST"] = OLLAMA_HOST

    resp = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options={
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    )
    return (resp.get("message", {}) or {}).get("content", "").strip()


def summarize_text(text: str, mode: Mode = "scientific") -> str:
    """
    Summarize an abstract using a local Ollama LLM with strict instructions.
    Modes:
      - scientific: concise scientific summary (keeps key facts, can keep some numbers)
      - layman: no acronyms, no numbers, no trial-design jargon, simple language
      - children: very simple, kid-friendly, no numbers/jargon
    """
    raw = _clean_input(text)
    if not raw or len(raw) < 30:
        return "No abstract available."

    mode = (mode or "scientific").lower().strip()  # type: ignore
    if mode not in ("scientific", "layman", "children"):
        mode = "scientific"

    if mode == "scientific":
        system = (
            "You are a biomedical researcher. Write a faithful, concise scientific summary of the abstract.\n"
            "Rules:\n"
            "- 4 to 6 sentences.\n"
            "- Keep the study question, who was studied, what was tested, and the main result.\n"
            "- Keep only the most important numbers (at most 2), but do not list dose schedules.\n"
            "- Do not invent details.\n"
        )
        user = f"Abstract:\n{raw}\n\nWrite the summary now."
        out = _ollama_chat(system, user, max_tokens=220, temperature=0.2)
        return _post_clean_output(out, "scientific")

    if mode == "layman":
        system = (
            "You explain medical research to the general public.\n"
            "Rules (must follow all):\n"
            "- No acronyms at all. If an acronym appears, remove it and spell the idea in plain words.\n"
            "- No numbers, no percentages, no dose schedules.\n"
            "- Do not mention trial design terms (no phase, randomized, placebo, endpoint, etc.).\n"
            "- Use simple words and short sentences.\n"
            "- 3 to 5 sentences.\n"
            "- Focus on: what problem, what was tried, what happened, what it could mean.\n"
            "- Do not invent details.\n"
        )
        user = f"Abstract:\n{raw}\n\nWrite the layman summary now."
        out = _ollama_chat(system, user, max_tokens=180, temperature=0.3)
        out = _post_clean_output(out, "layman")

        # If model outputs something too short/empty after cleaning, ask for a safer re-try
        if len(out) < 30:
            user_retry = (
                f"Abstract:\n{raw}\n\n"
                "Rewrite again in very simple everyday language. No acronyms. No numbers. 3 to 5 sentences."
            )
            out = _ollama_chat(system, user_retry, max_tokens=200, temperature=0.25)
            out = _post_clean_output(out, "layman")

        return out

    # children
    system = (
        "You explain medical research to an 8–10 year old.\n"
        "Rules (must follow all):\n"
        "- Very simple words.\n"
        "- No acronyms, no numbers.\n"
        "- 3 to 4 short sentences.\n"
        "- Explain: what was the health problem, what doctors tried, what they found, what happens next.\n"
        "- Do not invent details.\n"
    )
    user = f"Abstract:\n{raw}\n\nWrite the children summary now."
    out = _ollama_chat(system, user, max_tokens=140, temperature=0.4)
    out = _post_clean_output(out, "children")

    if len(out) < 20:
        user_retry = (
            f"Abstract:\n{raw}\n\n"
            "Try again: 3 short sentences. Very simple words. No acronyms. No numbers."
        )
        out = _ollama_chat(system, user_retry, max_tokens=160, temperature=0.35)
        out = _post_clean_output(out, "children")

    return out
