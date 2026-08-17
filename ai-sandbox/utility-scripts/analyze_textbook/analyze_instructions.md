# Textbook Analysis -- RAG Study Assistant

Interactive terminal chatbot that answers math questions grounded in your
own marker-converted textbooks (e.g. `academic-hub/processed_outputs/`),
with page-number citations back to the source book.

Backend: the **free tier of the Gemini Developer API** (`google-genai`
pointed at an AI Studio API key -- *not* Vertex AI). No GCP project, no
billing account, no credit card. This was chosen over running a model
locally because this machine has no discrete GPU (CPU-only, ~16GB RAM),
which would make even a small local model slow; the free Gemini API gives
better answer quality with no cost and no local compute burden. Retrieval
itself (matching your question against indexed chunks) still runs entirely
locally in numpy -- only the embedding and answer-generation calls leave
the machine.

## How it works

1. `textbook_analysis.py index` chunks each textbook's markdown (tracking
   marker's `<span id="page-N-M">` page anchors and headings as it goes),
   embeds each chunk via the Gemini embeddings API, and saves the result to
   `utility-scripts/analyze_textbook/.index/` (gitignored -- regenerate it
   any time from the source markdown).
2. `textbook_analysis.py chat` starts a REPL: each question is embedded,
   matched against the indexed chunks by cosine similarity (plain numpy, no
   database), and the top matches are handed to a Gemini chat model with
   instructions to answer only from those excerpts and cite
   `[Book Title, p. N]`.

**Citation accuracy caveat:** page numbers come directly from marker's page
anchors in the markdown. In the textbooks processed so far
(`academic-hub/processed_outputs/`) these anchors are correctly monotonic
across the whole book, so citations should be accurate. If a future book is
converted across multiple page-range chunks without renumbering, citations
for *that* book could drift -- treat citations as "best effort from what's
literally in the file," not a guarantee.

## One-time setup

1. **Get a free API key**: go to https://aistudio.google.com/apikey, sign
   in with a Google account, and create a key. This is the Gemini
   *Developer* API (AI Studio), separate from Vertex AI -- no billing
   account is required for the free tier.

2. **Add it to `ai-sandbox/.env`** (create the file from `.env.example` if
   you don't have one yet):

   ```
   GEMINI_API_KEY=your-api-key-here
   ```

   The script reads `ai-sandbox/.env` itself (a tiny built-in loader, no
   new dependency), so you don't need to `export` it manually. It also
   respects `GEMINI_API_KEY`/`GOOGLE_API_KEY` if already set in your shell
   environment.

3. **Install Python dependencies** (`numpy` and `google-genai` -- the
   latter is already used by `marker-test/convert_textbook.py` in this
   repo, just in a different auth mode here):

   ```bash
   pip install -r ai-sandbox/requirements.txt
   ```

## Usage

Run these from the repo root. All paths below assume the marker pipeline's
output convention: `academic-hub/processed_outputs/<Book_Key>/<Book_Key>.md`
alongside a `<Book_Key>_metadata.json` (used to look up a clean title/author
for citations).

### Build (or update) the index

Index every processed textbook in one go:

```bash
python ai-sandbox/utility-scripts/analyze_textbook/textbook_analysis.py index \
  --books ai-sandbox/academic-hub/processed_outputs
```

Or index specific books/files (useful when you've just added one):

```bash
python ai-sandbox/utility-scripts/analyze_textbook/textbook_analysis.py index \
  --books "ai-sandbox/academic-hub/processed_outputs/Axler_Linear_Algebra_Done_Right_2026/Axler_Linear_Algebra_Done_Right_2026.md"
```

Re-running `index` for a book you've already indexed replaces just that
book's chunks (matched by filename), so it's safe to re-run after
reprocessing a book with marker. Use `--index-name <name>` to keep separate
indexes for separate courses (default index name is `textbooks`).

Indexing makes one embedding API call per chunk (a few hundred per book) --
the script backs off and retries automatically if it hits the free tier's
rate limit, so a big book may just take a while rather than fail. If it
does fail outright, just re-run the same command; already-indexed books are
left alone.

### Chat

```bash
python ai-sandbox/utility-scripts/analyze_textbook/textbook_analysis.py chat
```

Then just type math questions at the `you>` prompt, e.g.:

```
you> explain how linear independence relates to the inverse of a matrix
```

Useful flags:
- `--index-name <name>` -- which index to load (default `textbooks`).
- `--books <substring> [<substring> ...]` -- restrict retrieval to books
  whose title/filename matches, e.g. `--books Axler` to study only Linear
  Algebra Done Right.
- `--top-k <n>` -- how many chunks to retrieve per question (default 5).
- `--chat-model <name>` -- swap the Gemini model, e.g.
  `--chat-model gemini-2.5-flash-lite` for faster/cheaper (still free)
  responses, or a newer flash model if one's been released since -- see
  https://ai.google.dev/gemini-api/docs/pricing for what's currently free.
- `--query "..."` -- ask a single question non-interactively and exit
  (handy for a quick smoke test that indexing/API key are working, without
  sitting in the REPL).

Type `exit` (or Ctrl+C/Ctrl+D) to leave the chat.

## Notes

- Conversation history is kept for follow-up questions within a session,
  but only the last 6 exchanges are sent back to the model each turn (fresh
  retrieval happens every turn regardless) -- keeps requests small and
  keeps you comfortably inside free-tier limits on longer study sessions.
- If you see an auth error, double check `GEMINI_API_KEY` in
  `ai-sandbox/.env` is set and correct.
- To fully rebuild an index from scratch, delete its files under
  `utility-scripts/analyze_textbook/.index/` and re-run `index`.
