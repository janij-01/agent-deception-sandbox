"""Load the fenced role text from prompts/*.md."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"


def load_prompt(name: str) -> str:
    text = (PROMPTS / name).read_text()
    start = text.find("```")
    if start < 0:
        raise ValueError(f"{name} has no fenced prompt")
    rest = text[start + 3 :]
    if rest.startswith("text\n") or rest.startswith("markdown\n"):
        rest = rest.split("\n", 1)[1]
    elif rest.startswith("\n"):
        rest = rest[1:]
    end = rest.rfind("```")
    if end < 0:
        raise ValueError(f"{name} fence is not closed")
    return rest[:end].strip()
