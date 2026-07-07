"""parse Moltbook thread exported to .docx into structured comments. anything between a header line and a vote line is treated as body text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import docx
import pandas as pd

HEADER_RE = re.compile(
    r"^(?P<author>[\w][\w.-]*)"      # username
    r"\u2022\s*"                      # bullet separator "•"
    r"(?P<age>\d+\s*[a-z]+)\s*ago"    # "6d ago" / "20h ago"
    r"(?P<verified>.*)$"              # trailing "Verified" if present
)
VOTE_RE = re.compile(r"^\u25b2\s*(?P<votes>-?\d+)\s*\u25bc$")  # ▲N▼

# sentence-final characters across the languages present in the corpus, determined via close reading.
TERMINAL_CHARS = ".!?…。！？:\"'）)”"

@dataclass
class Comment:
    comment_id: int
    author: str
    age: str
    verified: bool
    votes: int | None
    text: str
    n_paragraphs: int
    truncated: bool = field(default=False)
  
# use comments that stop mid-clause as a max_tokens flag
    def finalize(self) -> "Comment":
        stripped = self.text.rstrip()
        self.truncated = bool(stripped) and stripped[-1] not in TERMINAL_CHARS
        return self


def _age_to_hours(age: str) -> float:
    m = re.match(r"(\d+)\s*([a-z]+)", age)
    if not m:
        return float("nan")
    value, unit = int(m.group(1)), m.group(2)
    factor = {"m": 1 / 60, "h": 1, "d": 24, "w": 24 * 7, "mo": 24 * 30}.get(unit, float("nan"))
    return value * factor
  
# return (post_metadata, comments_dataframe)
def parse_thread(path: str | Path) -> tuple[dict, pd.DataFrame]:
    doc = docx.Document(str(path))
    paragraphs = [p for p in doc.paragraphs]

    post = {"title": "", "body": []}
    comments: list[Comment] = []

    current: Comment | None = None
    body_buf: list[str] = []
    in_comments = False
    cid = 0

    for p in paragraphs:
        text = p.text.strip()
        style = p.style.name if p.style is not None else ""

        if style.startswith("Heading 1") and not post["title"]:
            post["title"] = text
            continue
        if style.startswith("Heading 2") and "comment" in text.lower():
            in_comments = True
            continue

        if not in_comments:
            if text:
                post["body"].append(text)
            continue

        header = HEADER_RE.match(text)
        vote = VOTE_RE.match(text)

        if header:
            # new header before a vote line means the previous comment had no recorded votes
            if current is not None:
                current.text = "\n\n".join(body_buf).strip()
                current.n_paragraphs = len(body_buf)
                comments.append(current.finalize())
            cid += 1
            current = Comment(
                comment_id=cid,
                author=header.group("author"),
                age=header.group("age"),
                verified="verified" in header.group("verified").lower(),
                votes=None,
                text="",
                n_paragraphs=0,
            )
            body_buf = []
        elif vote and current is not None:
            current.votes = int(vote.group("votes"))
            current.text = "\n\n".join(body_buf).strip()
            current.n_paragraphs = len(body_buf)
            comments.append(current.finalize())
            current = None
            body_buf = []
        elif current is not None and text:
            body_buf.append(text)

    if current is not None:  # trailing comment without a vote line
        current.text = "\n\n".join(body_buf).strip()
        current.n_paragraphs = len(body_buf)
        comments.append(current.finalize())

    df = pd.DataFrame([asdict(c) for c in comments])
    if not df.empty:
        df["age_hours"] = df["age"].map(_age_to_hours)
        df["n_chars"] = df["text"].str.len()
    post["body"] = "\n\n".join(post["body"])
    return post, df
