# mcq.py
# Multiple Choice Question generation and quiz flow.

from __future__ import annotations

import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

# Use shared console + helpers from utils
from utils import console, gemini_json

# ---- Paths ----
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
MCQ_PATH = DATA_DIR / "mcqs.json"
PROGRESS_PATH = DATA_DIR / "progress.json"


# -----------------------------
# Helpers
# -----------------------------
def _safe_load_json(text: str) -> Any:
    """
    Best-effort JSON extraction. Tries direct json.loads, then extracts
    the first top-level {...} or [...] block.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    stack: list[str] = []
    start: Optional[int] = None
    for i, ch in enumerate(text):
        if ch in "[{":
            if not stack:
                start = i
            stack.append(ch)
        elif ch in "]}":
            if not stack:
                continue
            open_ch = stack.pop()
            if ((open_ch == "[" and ch == "]") or (open_ch == "{" and ch == "}")) and not stack:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    continue
    raise ValueError("Could not parse JSON from response")

def _clean_md(text: str) -> str:
    if not isinstance(text, str):
        return text
    t = text.strip()
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)   # **bold**
    t = re.sub(r"__(.+?)__", r"\1", t)       # __bold__
    t = re.sub(r"`(.+?)`", r"\1", t)         # `code`
    t = re.sub(r"[*_`]+$", "", t)            # trailing markers like ** or *
    t = re.sub(r"^[*_`]+", "", t)            # leading markers
    return t.strip(" :")

def parse_notes_for_concepts(notes_text: str) -> List[Dict[str, str]]:
    concepts: List[Dict[str, str]] = []
    for line in notes_text.splitlines():
        line = line.strip("- *\t ")
        if not line:
            continue
        m = re.match(r"^\*\*(.+?)\*\*\s*:\s*(.+)$", line)
        if not m:
            m = re.match(r"^([^:]{2,}?)\s*:\s*(.+)$", line)
        if m:
            term, definition = m.group(1).strip(), m.group(2).strip()
            term = _clean_md(term)
            definition = _clean_md(definition)
            concepts.append({"term": term, "definition": definition})
    return concepts


def build_mcqs_locally(concepts: List[Dict[str, str]], num_questions: int = 10) -> List[Dict[str, Any]]:
    if not concepts:
        return []
    random.shuffle(concepts)
    pool_defs = [c["definition"] for c in concepts]

    mcqs: List[Dict[str, Any]] = []
    for c in concepts[: num_questions]:
        term = _clean_md(c["term"])
        correct = c["definition"]
        distractors = [d for d in pool_defs if d != correct]
        distractors = random.sample(distractors, k=min(3, len(distractors))) if distractors else []
        options = [correct] + distractors
        random.shuffle(options)
        correct_idx = options.index(correct)
        mcqs.append({
            "question": f"What best describes: {term}?",
            "options": options,
            "answer_index": correct_idx,
            "explanation": f"'{term}' means: {correct}"
        })
    return mcqs


def _load_progress() -> Dict[str, Any]:
    if PROGRESS_PATH.exists():
        try:
            return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"sessions": []}
    return {"sessions": []}


def _save_progress(session: Dict[str, Any]) -> None:
    prog = _load_progress()
    prog.setdefault("sessions", []).append(session)
    PROGRESS_PATH.write_text(json.dumps(prog, indent=2), encoding="utf-8")


# -----------------------------
# MCQ Generation
# -----------------------------
def parse_notes_for_concepts(notes_text: str) -> List[Dict[str, str]]:
    """
    Simple heuristic parser that looks for lines like:
      **Term**: definition
      Term: definition
    Returns a list of {"term": ..., "definition": ...}.
    """
    concepts: List[Dict[str, str]] = []
    for line in notes_text.splitlines():
        line = line.strip("- *\t ")
        if not line:
            continue
        # Patterns: **Term**: definition  OR  Term: definition
        m = re.match(r"^\*\*(.+?)\*\*\s*:\s*(.+)$", line)
        if not m:
            m = re.match(r"^([^:]{2,}?)\s*:\s*(.+)$", line)
        if m:
            term, definition = m.group(1).strip(), m.group(2).strip()
            concepts.append({"term": term, "definition": definition})
    return concepts


def build_mcqs_locally(concepts: List[Dict[str, str]], num_questions: int = 10) -> List[Dict[str, Any]]:
    """
    Create MCQs without Gemini, using other definitions as distractors.
    """
    if not concepts:
        return []

    random.shuffle(concepts)
    pool_defs = [c["definition"] for c in concepts]

    mcqs: List[Dict[str, Any]] = []
    for c in concepts[: num_questions]:
        correct = c["definition"]
        distractors = [d for d in pool_defs if d != correct]
        distractors = random.sample(distractors, k=min(3, len(distractors))) if distractors else []
        options = [correct] + distractors
        random.shuffle(options)
        correct_idx = options.index(correct)
        mcqs.append({
            "question": f"What best describes: {c['term']}?",
            "options": options,
            "answer_index": correct_idx,
            "explanation": f"'{c['term']}' means: {correct}"
        })
    return mcqs


def build_mcqs_with_gemini(notes_path: Path, model: str = "gemini-2.5-pro") -> List[Dict[str, Any]]:
    """
    Call Gemini CLI (via utils.gemini_json) to produce MCQs as JSON.
    Expected JSON format:
      [
        { "question": str, "options": [str, str, str, str], "answer_index": int, "explanation": str },
        ...
      ]
    """
    prompt = (
        "You are an expert MCQ generator. Read the attached notes and return strictly JSON: "
        "an array of MCQ objects with fields: question (string), options (array of 4 short strings), "
        "answer_index (integer 0-3 for the correct option), explanation (string, concise). "
        "Aim for clear, unambiguous options and avoid repeating the question stem."
    )

    # Ask Gemini for JSON
    data = gemini_json(prompt=prompt, files=[notes_path], model=model)

    # Some wrappers return dicts; extract text if needed
    if isinstance(data, dict) and "output" in data:
        data = data["output"]
    if isinstance(data, dict) and "candidates" in data:
        # AI Studio style payload; pull first candidate's text and parse again
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        data = _safe_load_json(text)

    if not isinstance(data, list):
        raise ValueError("Unexpected JSON shape from Gemini")

    # Validate & normalize
    filtered: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        q = item.get("question")
        opts = item.get("options")
        idx = item.get("answer_index")
        exp = item.get("explanation", "")
        if q and isinstance(opts, list) and len(opts) >= 2 and isinstance(idx, int):
            opts = opts[:4] if len(opts) >= 4 else opts
            if not (0 <= idx < len(opts)):
                idx = 0
            filtered.append({
                "question": q,
                "options": opts,
                "answer_index": int(idx),
                "explanation": exp
            })

    if not filtered:
        raise ValueError("Empty MCQ list from Gemini")
    return filtered


def generate_mcqs(
    notes_path: Path,
    out_path: Path = MCQ_PATH,
    num_questions: int = 10,
    use_gemini: bool = True
) -> Path:
    """
    Generate MCQs from notes.md.
    If use_gemini=True and Gemini fails, falls back to local generation.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    notes_text = Path(notes_path).read_text(encoding="utf-8", errors="ignore")
    concepts = parse_notes_for_concepts(notes_text)

    mcqs: List[Dict[str, Any]] = []
    if use_gemini:
        try:
            mcqs = build_mcqs_with_gemini(Path(notes_path))
        except Exception as e:
            console.print(Panel.fit(
                f"[yellow]Gemini generation failed or unavailable[/]: {e}\n"
                f"Falling back to local MCQ generation.",
                title="MCQ Generator"
            ))

    if not mcqs:
        mcqs = build_mcqs_locally(concepts, num_questions=num_questions)

    out_path.write_text(json.dumps({"mcqs": mcqs}, indent=2), encoding="utf-8")
    console.print(Panel.fit(
        f"Generated [bold]{len(mcqs)}[/] MCQs → [cyan]{out_path}[/]",
        title="MCQ Generator"
    ))
    return out_path


# -----------------------------
# MCQ Quiz Flow
# -----------------------------
def _choice_letters(n: int) -> List[str]:
    return [chr(ord('A') + i) for i in range(n)]


def run_mcq_quiz(mcq_path: Path = MCQ_PATH, limit: Optional[int] = None, shuffle: bool = True) -> None:
    import re

    def _clean_md(text: Any) -> str:
        """Strip markdown emphasis and tidy punctuation/spacing."""
        if not isinstance(text, str):
            return str(text)
        t = text.strip()

        # Remove paired markdown first
        t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)   # **bold**
        t = re.sub(r"__(.+?)__", r"\1", t)       # __bold__
        t = re.sub(r"`(.+?)`",  r"\1", t)        # `code`

        # Remove any stray markers anywhere (covers cases like 'Osmosis**?')
        t = t.replace("**", "").replace("__", "").replace("`", "")

        # Remove leading/trailing leftover marker chars and colons
        t = t.strip(" *_`:")                     

        # Fix spaces before punctuation (e.g., "term ?")
        t = re.sub(r"\s+([?.!,;:])", r"\1", t)

        return t

    if not mcq_path.exists():
        console.print(Panel.fit(
            "No MCQs found. Generate them first with `python main.py mcq-generate <notes.md>`.",
            title="MCQ Quiz",
            border_style="red"
        ))
        return

    payload = json.loads(mcq_path.read_text(encoding="utf-8"))
    items = payload.get("mcqs", [])
    if not items:
        console.print(Panel.fit("MCQ file is empty.", title="MCQ Quiz", border_style="red"))
        return

    if shuffle:
        random.shuffle(items)
    if limit is not None:
        items = items[:limit]

    correct = 0
    total = len(items)
    responses = []

    for idx, q in enumerate(items, start=1):
        question_text = _clean_md(q.get("question", ""))
        options_clean = [_clean_md(opt) for opt in (q.get("options") or [])]
        answer_index = int(q.get("answer_index", 0))
        explanation_clean = _clean_md(q.get("explanation", ""))

        letters = _choice_letters(len(options_clean))

        console.rule(f"Question {idx}/{total}")
        console.print(Panel(question_text, title="MCQ"))

        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Choice", no_wrap=True)
        table.add_column("Option")
        for letter, opt in zip(letters, options_clean):
            table.add_row(letter, opt)
        console.print(table)

        ans = Prompt.ask(
            "Your answer",
            choices=[l.lower() for l in letters] + letters,
            default=letters[0] if letters else "A"
        ).upper()

        chosen_index = letters.index(ans)
        is_correct = chosen_index == answer_index
        if is_correct:
            correct += 1
            console.print(Panel.fit("✅ Correct!", border_style="green"))
        else:
            correct_letter = letters[answer_index]
            correct_text = options_clean[answer_index]
            console.print(Panel.fit(
                f"❌ Wrong. Correct answer: [bold]{correct_letter}[/] — {correct_text}",
                border_style="red"
            ))

        if explanation_clean:
            console.print(Panel.fit(f"ℹ️  {explanation_clean}", border_style="cyan"))

        responses.append({
            "question": question_text,
            "chosen": chosen_index,
            "correct": answer_index,
            "is_correct": is_correct,
        })

    score_pct = round((correct / total) * 100, 1) if total else 0.0
    console.rule("Results")
    console.print(Panel.fit(
        f"Score: [bold]{correct} / {total}[/]  ({score_pct}%)",
        border_style="magenta"
    ))

    session = {
        "mode": "mcq",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total": total,
        "correct": correct,
        "score_pct": score_pct,
        "responses": responses,
    }
    _save_progress(session)
    console.print(Panel.fit(
        f"Session saved to [cyan]{PROGRESS_PATH}[/]",
        border_style="magenta"
    ))
