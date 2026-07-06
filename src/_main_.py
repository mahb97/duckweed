"""imports"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .metrics import compute_all, opening_formulas
from .parse import parse_thread
from .plots import novelty_over_time, similarity_distributions, similarity_heatmap

def main() -> None:
    ap = argparse.ArgumentParser(description="Template-collapse metrics for Moltbook thread")
    ap.add_argument("docx", type=Path, help="thread exported as .docx")
    ap.add_argument("-o", "--outdir", type=Path, default=Path("results"),
                    help="shareable artifacts (metrics, figures, report)")
    ap.add_argument("--top-authors", type=int, default=5,
                    help="how many authors to detail in the report")
    args = ap.parse_args()
    private = args.outdir / "private"  # gitignored
    private.mkdir(parents=True, exist_ok=True)

    post, df = parse_thread(args.docx)
    df, summary, sim = compute_all(df)

    # Full CSV (includes comment text) is hidden in results/private/ —
   
    df.to_csv(private / "comments.csv", index=False)
    df.drop(columns=["text"]).to_csv(args.outdir / "comments_public.csv", index=False)
    summary.to_csv(args.outdir / "author_summary.csv", index=False)

    similarity_heatmap(df, sim, args.outdir / "similarity_heatmap.png")
    similarity_distributions(df, sim, args.outdir / "similarity_distributions.png")
    novelty_over_time(df, args.outdir / "novelty_over_time.png")

    lines = [
        f"# {post['title']}",
        "",
        f"Parsed **{len(df)} comments** from **{df['author'].nunique()} authors**.",
        "",
        "## Author summary",
        "",
        summary.round(3).to_markdown(index=False),
        "",
        "`effective_rank` is the participation ratio of the author's similarity",
        "matrix: roughly, how many *distinct* comments the agents actually wrote.",
        "`compression_ratio` = effective_rank / n_comments (1.0 = every comment",
        "novel; → 0 = one comment posted many times in different forms).",
        "",
    ]
    top = summary.head(args.top_authors)["author"]
    for author in top:
        forms = opening_formulas(df, author)
        if forms.iloc[0] < 2:
            continue
        lines += [f"## Most-recycled openings — {author}", ""]
        lines += [f"- {count}× “{opening} …”" for opening, count in forms.items() if count > 1]
        lines += [""]

    trunc = df[df["truncated"]]
    lines += [
        "## Truncation",
        "",
        f"{len(trunc)} comments ({len(trunc)/len(df):.0%}) end mid-clause "
        "(no sentence-final punctuation) —consistent with a hard max_tokens "
        "cutoff rather than a rhetorical choice.",
        "",
    ]
    (args.outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.outdir}/: report.md, comments_public.csv, author_summary.csv and 3 figs (full text quarantined in {private}/)")
    print()
    print(summary.round(3).to_string(index=False))
if __name__ == "__main__":
    main()
