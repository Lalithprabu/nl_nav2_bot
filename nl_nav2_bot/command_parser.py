"""Turns free-text commands into a target waypoint name.

Pure Python, no ROS dependency, so it can be unit-tested without a ROS 2
installation. Two strategies are tried in order:

1. Rule-based matching: look for a known waypoint name (or a close fuzzy
   match) inside the command text. Fast, deterministic, works offline.
2. Optional LLM fallback: if OPENAI_API_KEY is set in the environment and
   the rule-based pass finds nothing, ask an LLM to pick the closest
   waypoint from the known list. This is what makes phrasing like
   "I'm hungry, can you head to where the food is" resolvable, without
   requiring an API key for the project to work at all.
"""
from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParseResult:
    waypoint: Optional[str]
    confidence: float
    method: str  # "rule", "llm", or "none"


_STOPWORDS = {
    "go", "to", "the", "please", "can", "you", "navigate", "head",
    "move", "drive", "take", "me", "a", "over", "towards", "toward",
    "at", "robot",
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9_\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> list[str]:
    return [w for w in _normalize(text).split(" ") if w and w not in _STOPWORDS]


def rule_based_match(command: str, waypoint_names: list[str]) -> ParseResult:
    """Look for a waypoint name (underscored or spaced) inside the command."""
    norm = _normalize(command)
    norm_spaced = norm.replace("_", " ")

    # 1. Exact substring match against each known waypoint.
    for name in waypoint_names:
        candidate = name.replace("_", " ")
        if candidate in norm_spaced or name in norm:
            return ParseResult(waypoint=name, confidence=1.0, method="rule")

    # 2. Fuzzy match against individual meaningful tokens/phrases.
    tokens = _tokenize(command)
    joined = " ".join(tokens)
    search_space = [joined] + tokens
    best_name, best_score = None, 0.0
    for name in waypoint_names:
        candidate = name.replace("_", " ")
        for probe in search_space:
            if not probe:
                continue
            score = difflib.SequenceMatcher(None, probe, candidate).ratio()
            if score > best_score:
                best_score, best_name = score, name

    if best_name and best_score >= 0.6:
        return ParseResult(waypoint=best_name, confidence=best_score, method="rule")

    return ParseResult(waypoint=None, confidence=0.0, method="none")


def llm_match(command: str, waypoint_names: list[str]) -> ParseResult:
    """Ask an LLM to pick the best-matching waypoint. Requires OPENAI_API_KEY."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ParseResult(waypoint=None, confidence=0.0, method="none")

    try:
        from openai import OpenAI
    except ImportError:
        return ParseResult(waypoint=None, confidence=0.0, method="none")

    client = OpenAI(api_key=api_key)
    options = ", ".join(waypoint_names)
    prompt = (
        "You control a mobile robot. Known locations: "
        f"{options}. A user said: \"{command}\". "
        "Reply with exactly one word: the single best-matching location "
        "name from the list, or NONE if nothing reasonably matches."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=8,
        )
        answer = response.choices[0].message.content.strip().lower()
    except Exception:
        return ParseResult(waypoint=None, confidence=0.0, method="none")

    if answer in waypoint_names:
        return ParseResult(waypoint=answer, confidence=0.9, method="llm")
    return ParseResult(waypoint=None, confidence=0.0, method="none")


def parse_command(command: str, waypoint_names: list[str]) -> ParseResult:
    """Main entry point: rule-based first, LLM fallback if configured."""
    result = rule_based_match(command, waypoint_names)
    if result.waypoint is not None:
        return result
    return llm_match(command, waypoint_names)
