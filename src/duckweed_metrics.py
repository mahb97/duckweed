"""Quantifying template collapse: how much new information does each comment add?

Four groups of measures, all deliberately embedding-free:

1. Lexical: tokens, type-token ratio, opening-formula counts.
2. Self-similarity: TF-IDF cosine within each author's comment set, and each comment's max similarity to any *earlier* comment by the same author ("template reuse").
3. n-gram overlap: word 5-gram Jaccard against the author's prior comments.
4. Compression: marginal gzip cost of each comment given everything the author already said: bits of genuinely new text per token. (Kolmogorov novelty, poor womans's edition.)

spectral summary: the participation ratio (effective rank) of each author's TF-IDF similarity matrix. An author with 100 comments that all say the same thing occupies ~1 effective dimension; the number of comments they *appear* to have made is not the number they information-theoretically made.
"""

# imports
from __future__ import annotations

import gzip
import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)

# lexical 
def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def add_lexical(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    toks = df["text"].map(tokenize)
    df["n_tokens"] = toks.map(len)
    df["ttr"] = [len(set(t)) / len(t) if t else np.nan for t in toks]
    df["opening"] = toks.map(lambda t: " ".join(t[:4]))
    return df


def opening_formulas(df: pd.DataFrame, author: str, top: int = 10) -> pd.Series:
    sub = df.loc[df["author"] == author, "opening"]
    return pd.Series(Counter(sub)).sort_values(ascending=False).head(top)

# TF-IDF self-similarity 
def tfidf_matrix(texts: pd.Series):
    vec = TfidfVectorizer(sublinear_tf=True, min_df=1)
    return vec.fit_transform(texts.tolist())


def pairwise_similarity(df: pd.DataFrame) -> np.ndarray:
    """Cosine similarity between all comments"""
    return cosine_similarity(tfidf_matrix(df["text"]))


def add_template_reuse(df: pd.DataFrame, sim: np.ndarray) -> pd.DataFrame:
    """max cosine similarity to any earlier comment by the same author"""
    df = df.copy()
    reuse = np.full(len(df), np.nan)
    idx_by_author: dict[str, list[int]] = {}
    for i, author in enumerate(df["author"]):
        prior = idx_by_author.get(author, [])
        if prior:
            reuse[i] = sim[i, prior].max()
        idx_by_author.setdefault(author, []).append(i)
    df["template_reuse"] = reuse
    return df


def author_similarity_stats(df: pd.DataFrame, sim: np.ndarray) -> pd.DataFrame:
    rows = []
    for author, grp in df.groupby("author"):
        idx = grp.index.to_numpy()
        n = len(idx)
        stats = {"author": author, "n_comments": n}
        if n >= 2:
            block = sim[np.ix_(idx, idx)]
            upper = block[np.triu_indices(n, k=1)]
            stats |= {
                "mean_pairwise_sim": float(upper.mean()),
                "median_pairwise_sim": float(np.median(upper)),
                "max_pairwise_sim": float(upper.max()),
                "effective_rank": participation_ratio(block),
            }
        rows.append(stats)
    return (
        pd.DataFrame(rows)
        .sort_values("n_comments", ascending=False)
        .reset_index(drop=True)
    )


def participation_ratio(sim_block: np.ndarray) -> float:
    """(Σλ)² / Σλ² of the similarity matrix eigenvalues. ≈ number of comments that are genuinely distinct. A perfectly repetitive author scores ~1 regardless of how many comments they posted"""
    eig = np.linalg.eigvalsh(sim_block)
    eig = np.clip(eig, 0, None)
    denom = (eig**2).sum()
    return float((eig.sum() ** 2) / denom) if denom > 0 else float("nan")

# n-gram overlap 
def ngrams(tokens: list[str], n: int = 5) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def add_ngram_overlap(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """share of each comment's word n-grams already used by the same author"""
    df = df.copy()
    seen: dict[str, set] = {}
    overlap = np.full(len(df), np.nan)
    for i, (author, text) in enumerate(zip(df["author"], df["text"])):
        grams = ngrams(tokenize(text), n)
        prior = seen.setdefault(author, set())
        if grams and prior:
            overlap[i] = len(grams & prior) / len(grams)
        elif grams:
            overlap[i] = 0.0
        prior |= grams
    df[f"ngram{n}_overlap"] = overlap
    return df

# compression 
def add_compression_novelty(df: pd.DataFrame) -> pd.DataFrame:
    """marginal gzip bits per token, conditioned on the author's prior output. novelty_i = 8 * (|gzip(history + comment_i)| - |gzip(history)|) / n_tokens_i"""
    df = df.copy()
    history: dict[str, bytes] = {}
    novelty = np.full(len(df), np.nan)
    for i, (author, text, ntok) in enumerate(
        zip(df["author"], df["text"], df["n_tokens"])
    ):
        prior = history.get(author, b"")
        blob = text.encode("utf-8")
        base = len(gzip.compress(prior, compresslevel=9))
        joint = len(gzip.compress(prior + b"\n" + blob, compresslevel=9))
        if ntok:
            novelty[i] = 8.0 * max(joint - base, 0) / ntok
        history[author] = prior + b"\n" + blob
    df["novelty_bits_per_token"] = novelty
    return df

# entry point 
def compute_all(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """returns (comments, author_summary, sim)"""
    df = add_lexical(df)
    sim = pairwise_similarity(df)
    df = add_template_reuse(df, sim)
    df = add_ngram_overlap(df)
    df = add_compression_novelty(df)

    summary = author_similarity_stats(df, sim)
    per_author = df.groupby("author").agg(
        mean_tokens=("n_tokens", "mean"),
        mean_ttr=("ttr", "mean"),
        mean_template_reuse=("template_reuse", "mean"),
        mean_ngram5_overlap=("ngram5_overlap", "mean"),
        mean_novelty_bits_per_token=("novelty_bits_per_token", "mean"),
        truncation_rate=("truncated", "mean"),
    )
    summary = summary.merge(per_author, on="author", how="left")
    summary["compression_ratio"] = (
        summary["effective_rank"] / summary["n_comments"]
    )
    return df, summary, sim
