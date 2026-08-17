#!/usr/bin/env python3
"""
textbook_analysis.py
RAG study assistant over marker-converted textbook markdown, backed by the
free-tier Gemini Developer API (not Vertex AI -- no GCP billing account
needed, just an API key from https://aistudio.google.com/apikey).

Two subcommands:
  index  -- chunk + embed one or more markdown textbooks (or directories of
            them) into a local index under .index/, via the Gemini
            embeddings API. Re-indexing a book replaces just its chunks.
  chat   -- interactive terminal chat grounded in an index: each question is
            embedded, matched against indexed chunks by cosine similarity,
            and the top matches are handed to a Gemini chat model with
            instructions to answer only from those excerpts and cite
            [Book Title, p. N].

The local index (chunk text/metadata + embedding vectors) is plain
JSON + a numpy .npy file under .index/ -- retrieval itself (the actual RAG
matching) runs entirely locally; only the embedding and chat *generation*
calls go out to Google. See analyze_instructions.md for one-time setup
(getting an API key) and example commands.

Page citations are only as good as the page anchors marker embedded in the
source markdown (`<span id="page-N-M">`). If a book was converted across
multiple page-range chunks without renumbering, citations for that book may
drift -- treat them as "best effort from what's literally in the file."
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

import numpy as np
from google import genai
from google.genai import errors, types

INDEX_DIR = Path(__file__).parent / ".index"
ENV_FILE = Path(__file__).parents[2] / ".env"

PAGE_ANCHOR_RE = re.compile(r'<span id="page-(\d+)-\d+"></span>')
IMAGE_RE = re.compile(r'!\[[^\]]*\]\([^)]*\)')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]*\)')
EMPHASIS_RE = re.compile(r'[*_`]')
HTML_TAG_RE = re.compile(r'<[^>]+>')


def load_dotenv_defaults():
    """
    Minimal .env reader for ai-sandbox/.env (KEY=VALUE lines), matching this
    repo's existing convention (see .env.example) without adding a
    python-dotenv dependency. Never overrides a variable already set in the
    real environment.
    """
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def get_client() -> genai.Client:
    load_dotenv_defaults()
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            "No Gemini API key found. Set GEMINI_API_KEY in ai-sandbox/.env or your "
            "environment -- see analyze_instructions.md for how to get a free key."
        )
    return genai.Client()


def clean_heading_text(raw: str) -> str:
    """Strips marker's markdown-link/anchor/emphasis noise out of a heading line."""
    text = MD_LINK_RE.sub(r'\1', raw)
    text = HTML_TAG_RE.sub('', text)
    text = EMPHASIS_RE.sub('', text)
    return text.strip()


def load_book_info(md_path: Path) -> dict:
    """
    Prefers the sidecar <stem>_metadata.json marker writes next to its
    output (markdown_parsed_info, falling back to source_pdf_document_info),
    then falls back to the filename if no metadata file is present.
    """
    meta_path = md_path.with_name(md_path.stem + "_metadata.json")
    title, author, year = "", "", ""
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            parsed = data.get("markdown_parsed_info") or {}
            source = data.get("source_pdf_document_info") or {}
            title = parsed.get("title") or source.get("title") or ""
            author = parsed.get("author") or source.get("author") or ""
            year = parsed.get("year") or source.get("year") or ""
        except (json.JSONDecodeError, OSError):
            pass
    if not title:
        title = md_path.stem.replace("_", " ")
    return {"title": title, "author": author, "year": year}


def chunk_markdown(text: str, chunk_size: int) -> list:
    """
    Splits markdown on blank-line paragraph boundaries and accumulates
    paragraphs into ~chunk_size-character chunks, tracking the nearest
    preceding page anchor and heading as it goes. Each chunk carries the
    page/heading that was current when the chunk *started*, and starts with
    the previous chunk's last paragraph for a little context overlap.
    """
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    buffer = []
    buffer_len = 0
    buffer_page = 0
    buffer_heading = ""
    current_page = 0
    current_heading = ""
    carry = None

    def flush():
        nonlocal buffer, buffer_len, carry
        chunk_text = "\n\n".join(buffer).strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "page": buffer_page, "heading": buffer_heading})
            carry = buffer[-1]
        buffer = []
        buffer_len = 0

    for raw_para in paragraphs:
        anchors = PAGE_ANCHOR_RE.findall(raw_para)
        if anchors:
            current_page = int(anchors[-1])
        para = PAGE_ANCHOR_RE.sub('', raw_para)
        para = IMAGE_RE.sub('', para).strip()
        if not para:
            continue

        heading_match = HEADING_RE.match(para)
        if heading_match:
            current_heading = clean_heading_text(heading_match.group(2))

        if not buffer:
            buffer_page = current_page
            buffer_heading = current_heading
            if carry:
                buffer.append(carry)
                buffer_len += len(carry)

        buffer.append(para)
        buffer_len += len(para)

        if buffer_len >= chunk_size:
            flush()

    if buffer:
        flush()

    return chunks


def collect_markdown_files(paths) -> list:
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"WARNING: path not found, skipping: {raw}")
    return files


def embed_text(client: genai.Client, model: str, text: str, task_type: str, max_retries: int = 5) -> list:
    """Embeds text via the Gemini API, retrying with backoff on free-tier rate limits."""
    delay = 5
    for attempt in range(max_retries + 1):
        try:
            resp = client.models.embed_content(
                model=model,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            return resp.embeddings[0].values
        except errors.ClientError as e:
            is_rate_limit = getattr(e, "code", None) == 429
            if is_rate_limit and attempt < max_retries:
                print(f"  Rate limited by the free tier, waiting {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


def index_paths(index_name: str):
    return (INDEX_DIR / f"{index_name}_meta.json", INDEX_DIR / f"{index_name}_vectors.npy")


def cmd_index(args):
    client = get_client()
    INDEX_DIR.mkdir(exist_ok=True)
    meta_path, vec_path = index_paths(args.index_name)

    existing_meta, existing_vecs = [], None
    if meta_path.exists() and vec_path.exists():
        existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        existing_vecs = np.load(vec_path)

    md_files = collect_markdown_files(args.books)
    if not md_files:
        print("No markdown files found for the given paths.")
        return

    replaced_keys = {f.stem for f in md_files}
    keep_idx = [i for i, m in enumerate(existing_meta) if m["book_key"] not in replaced_keys]
    kept_meta = [existing_meta[i] for i in keep_idx]
    kept_vecs = existing_vecs[keep_idx] if existing_vecs is not None and keep_idx else None

    new_meta, new_vecs = [], []
    for md_path in md_files:
        info = load_book_info(md_path)
        text = md_path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, chunk_size=args.chunk_size)
        print(f"{md_path.name} ({info['title']}): {len(chunks)} chunks")
        for i, c in enumerate(chunks):
            vec = embed_text(client, args.embed_model, c["text"], task_type="RETRIEVAL_DOCUMENT")
            new_vecs.append(vec)
            new_meta.append({
                "book_key": md_path.stem,
                "title": info["title"],
                "author": info["author"],
                "source_file": str(md_path),
                "page": c["page"],
                "heading": c["heading"],
                "text": c["text"],
            })
            if (i + 1) % 25 == 0 or (i + 1) == len(chunks):
                print(f"  ...{i + 1}/{len(chunks)} chunks embedded")

    all_meta = kept_meta + new_meta
    if kept_vecs is not None and len(kept_vecs):
        all_vecs = np.vstack([kept_vecs, np.array(new_vecs, dtype=np.float32)]) if new_vecs else kept_vecs
    else:
        all_vecs = np.array(new_vecs, dtype=np.float32)

    meta_path.write_text(json.dumps(all_meta, indent=2), encoding="utf-8")
    np.save(vec_path, all_vecs)
    n_books = len({m["book_key"] for m in all_meta})
    print(f"\nIndex '{args.index_name}' now has {len(all_meta)} chunks across {n_books} book(s).")


SYSTEM_PROMPT = (
    "You are a study assistant helping the user review their course textbooks. "
    "Answer ONLY using the excerpts given in the Context section of the current message. "
    "Cite every factual claim inline as [Book Title, p. N] using the page numbers given in "
    "the excerpts. If the excerpts don't contain enough information to answer well, say so "
    "explicitly instead of filling gaps from outside knowledge."
)

MAX_HISTORY_TURNS = 6


def cmd_chat(args):
    client = get_client()
    meta_path, vec_path = index_paths(args.index_name)
    if not meta_path.exists() or not vec_path.exists():
        print(f"No index named '{args.index_name}' found. Run the 'index' command first.")
        return

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    vecs = np.load(vec_path)

    if args.books:
        keep = [i for i, m in enumerate(meta)
                if any(b.lower() in (m["title"] + " " + m["book_key"]).lower() for b in args.books)]
        if not keep:
            print("No indexed chunks matched --books filter.")
            return
        meta = [meta[i] for i in keep]
        vecs = vecs[keep]

    norms = np.linalg.norm(vecs, axis=1)
    norms[norms == 0] = 1e-8

    def answer_once(question: str, history: list) -> str:
        q_vec = np.array(
            embed_text(client, args.embed_model, question, task_type="RETRIEVAL_QUERY"), dtype=np.float32
        )
        q_norm = np.linalg.norm(q_vec) or 1e-8
        sims = (vecs @ q_vec) / (norms * q_norm)
        top_idx = np.argsort(-sims)[:args.top_k]

        context = "\n\n---\n\n".join(
            f"[{meta[i]['title']}, p. {meta[i]['page']}] (section: {meta[i]['heading'] or 'n/a'})\n{meta[i]['text']}"
            for i in top_idx
        )
        contents = history[-(MAX_HISTORY_TURNS * 2):] + [
            {"role": "user", "parts": [{"text": f"Context:\n{context}\n\nQuestion: {question}"}]}
        ]
        config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)

        parts = []
        for chunk in client.models.generate_content_stream(model=args.chat_model, contents=contents, config=config):
            if chunk.text:
                print(chunk.text, end="", flush=True)
                parts.append(chunk.text)
        print()
        return "".join(parts)

    print(f"Loaded index '{args.index_name}' ({len(meta)} chunks). Type 'exit' to quit.\n")

    try:
        if args.query:
            answer_once(args.query, [])
            return

        history = []
        while True:
            try:
                question = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not question:
                continue
            if question.lower() in {"exit", "quit"}:
                break

            print("assistant> ", end="", flush=True)
            answer = answer_once(question, history)
            history.append({"role": "user", "parts": [{"text": question}]})
            history.append({"role": "model", "parts": [{"text": answer}]})
    except errors.ClientError as e:
        if getattr(e, "code", None) in (401, 403):
            print("Gemini API rejected the request -- check that GEMINI_API_KEY is set and valid.")
        else:
            raise


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--embed-model", default="gemini-embedding-001",
                         help="Gemini embedding model (default: gemini-embedding-001).")

    parser = argparse.ArgumentParser(description="RAG study assistant over textbook markdown, via the free Gemini API.",
                                      parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Chunk and embed textbook markdown into a local index.", parents=[common])
    p_index.add_argument("--books", nargs="+", required=True,
                          help="One or more markdown file paths, or directories to search recursively for .md files.")
    p_index.add_argument("--index-name", default="textbooks", help="Index name (default: textbooks).")
    p_index.add_argument("--chunk-size", type=int, default=1500,
                          help="Target characters per chunk before splitting (default: 1500).")
    p_index.set_defaults(func=cmd_index)

    p_chat = sub.add_parser("chat", help="Interactive terminal chat grounded in an index.", parents=[common])
    p_chat.add_argument("--index-name", default="textbooks", help="Index name to load (default: textbooks).")
    p_chat.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve per question (default: 5).")
    p_chat.add_argument("--books", nargs="+", default=None,
                         help="Restrict retrieval to books whose title/filename matches one of these substrings.")
    p_chat.add_argument("--chat-model", default="gemini-2.5-flash", help="Gemini chat model (default: gemini-2.5-flash).")
    p_chat.add_argument("--query", default=None,
                         help="Ask a single question non-interactively and exit (for smoke-testing the setup).")
    p_chat.set_defaults(func=cmd_chat)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
