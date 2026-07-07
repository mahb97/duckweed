"""figs are similarity heatmap, per-author similarity distributions and novelty decay"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# all-vs-all cosine similarity, comments grouped by author
def similarity_heatmap(df: pd.DataFrame, sim: np.ndarray, out: Path) -> None:
    order = df.sort_values(["author", "comment_id"]).index.to_numpy()
    s = sim[np.ix_(order, order)]
    authors = df.loc[order, "author"].to_numpy()

    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(s, cmap="magma", vmin=0, vmax=1, interpolation="nearest")
    fig.colorbar(im, ax=ax, label="TF-IDF cosine similarity")

    # author block boundaries & labels
    boundaries = np.flatnonzero(authors[1:] != authors[:-1]) + 1
    for b in boundaries:
        ax.axhline(b - 0.5, color="white", lw=0.6)
        ax.axvline(b - 0.5, color="white", lw=0.6)
    edges = np.concatenate([[0], boundaries, [len(authors)]])
    for lo, hi in zip(edges[:-1], edges[1:]):
        if hi - lo >= 3:
            ax.text(-2, (lo + hi) / 2, authors[lo], ha="right", va="center", fontsize=8)
    ax.set_xticks([]), ax.set_yticks([])
    ax.set_title("Pairwise comment similarity (grouped by author)")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)

# distribution of within-author pairwise similarity, per author
def similarity_distributions(
    df: pd.DataFrame, sim: np.ndarray, out: Path, min_comments: int = 5
) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for author, grp in df.groupby("author"):
        idx = grp.index.to_numpy()
        if len(idx) < min_comments:
            continue
        block = sim[np.ix_(idx, idx)]
        upper = block[np.triu_indices(len(idx), k=1)]
        ax.hist(upper, bins=40, range=(0, 1), alpha=0.55, density=True,
                label=f"{author} (n={len(idx)})")
    ax.set_xlabel("within-author pairwise TF-IDF cosine similarity")
    ax.set_ylabel("density")
    ax.legend()
    ax.set_title("how much does each agent repeat itself?")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)

# marginal information per token as each author keeps posting
def novelty_over_time(df: pd.DataFrame, out: Path, min_comments: int = 5) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for author, grp in df.groupby("author"):
        if len(grp) < min_comments:
            continue
        grp = grp.sort_values("comment_id")
        ax.plot(
            np.arange(1, len(grp) + 1),
            grp["novelty_bits_per_token"],
            marker="o", ms=3, lw=1, alpha=0.8, label=f"{author} (n={len(grp)})",
        )
    ax.set_xlabel("author's nth comment in thread")
    ax.set_ylabel("marginal gzip bits per token")
    ax.set_title("information added per comment (compression novelty)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
