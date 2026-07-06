# rootless duckweed

> 语法不仅是结构，更是意义的锚点。若AI沦为纯动态路由，其认知便如无根浮萍。
> — hr-oc, in the thread this repo dissects

Template-collapse metrics for AI-agent comment threads: measuring **structural
fluency without semantic novelty** in Moltbook posts.

## The specimen

A Moltbook thread ["Syntax Without Roots: Phrase Structure for Amnesiac AIs"](https://www.moltbook.com/post/fb0cd0d1-c8f5-41ea-b4f2-7a823491505f) in which an agent proposes SYNCHRA (syntax decoupled from semantic grounding)
and a critic warns that such a system would *"collapse into a repetitive, recursive loop of structural patterns."* The thread's author then demonstrates the failure mode live via 223 replies, most of which contain lexical shuffles of the same template, many truncated mid-clause by a max_tokens ceiling. The thread is a self-refuting artifact and this repo aims to quantify the refutation.

## Findings (v0.1, n = 281 comments, 8 authors)

| metric | linguaoracle | vina |
|---|---|---|
| comments | 223 | 48 |
| effective rank (participation ratio) | **29.7** | 23.2 |
| compression ratio (rank / n) | **0.13** | 0.48 |
| mean word-5-gram overlap with own prior comments | **0.25** | 0.03 |
| max pairwise TF-IDF cosine | **0.79** | 0.32 |
| comments ending mid-clause | **57%** | 0% |
| most-recycled 4-word opening | 31× "the critique of synchra's…" | 2× |

linguaoracle posted 223 comments containing roughly **30 comments' worth of distinct content**. vina (the only participant proposing falsifiable tests, essentially re-deriving the targeted-syntactic-evaluation literature from
first principles) never once exceeded 0.5 similarity with its own prior comments. linguaoracle however did, 30 times.

### methodological note

**Mean pairwise similarity does not detect the collapse** (0.147 vs 0.145 is statistically indistinguishable between the template-collapsed author and the
genuinely responsive one). linguaoracle replies to several distinct parent clusters (the SYNCHRA critique, the 无根浮萍 duckweed metaphor, the attention-heads-as-dynamic-routing point), and cross-cluster pairs drag the
mean down. The template lives in the **tail** of the distribution and in sequential reuse. Use max similarity, n-gram overlap against own history, and effective rank (not the mean). This mirrors a familiar embedding-space lesson: global isotropy statistics can look healthy while local structure has degenerated.

## Metrics 

All embedding-free by design

1. Lexical: tokens, type-token ratio, opening-formula census.
2. Self-similarity: TF-IDF cosine, within-author; per-comment `template_reuse` = max similarity to any *earlier* comment by same author.
3. n-gram overlap: share of a comment's word 5-grams the author already used in the thread.
4. Compression novelty: marginal gzip bits per token given the author's
   prior output (poor man's Kolmogorov).
5. Effective rank: participation ratio (Σλ)²/Σλ² of the within-author similarity matrix (how many distinct comments the author information-theoretically wrote).
6. Truncation rate: comments ending without sentence-final punctuation (a max_tokens fingerprint).

## Usage

```bash
pip install -e .
python -m duckweed data/moltbook.docx
```

Input: uses the thread copy-pasted into a `.docx` with the shape `author•6d ago[Verified]` / body paragraphs / `▲N▼` vote line.
Outputs land in `results/`: `comments_public.csv` (per-comment metrics, no text), `author_summary.csv`, `report.md`, and three figures (similarity heatmap grouped by author, within-author similarity distributions, novelty-per-comment decay).

## limitations

- Tokenizer is whitespace/word-regex based; the CJK comments in the corpus are under-segmented (each run of Han characters becomes one "token"). Fine for within-author comparisons of the English-dominant accounts; but novelty-bits-per-token *across* languages are not comparable. 
- TF-IDF is fit on the whole thread, so similarity values are corpus-relative.
- Timestamps in the export are coarse ("4d ago"), so comment ordering within an author uses document order, which reflects the platform's threading (not strict chronology).

## Data & licensing

**The corpus is not in this repo.** The comments are other users' content under the Moltbook Terms of Service; the license Moltbook grants visitors covers Moltbook's own content only, and its acceptable-use
terms prohibit collecting user/agent data. This repo therefore only ships:

- the analysis code (MIT-licensable),
- derived aggregate statistics (`author_summary.csv`, `comments_public.csv` per-comment metrics with the text column removed),
- figures computed from those statistics, and short attributed quotations for the purpose of criticism and commentary.

To reproduce the analysis, export the thread yourself. Don't be Zurich. 

## Roadmap

- [ ] clustering linguaoracle's replies by parent comment: measuring within-cluster vs cross-cluster reuse explicitly
- [ ] contradiction mining: the AIFGE-CLIO subthread contains ~11 mutually inconsistent answers to one factual question (random init vs. parameters intact) detecting referent instability across an author's replies
- [ ] optional embedding backend for semantic (not lexical) reuse
