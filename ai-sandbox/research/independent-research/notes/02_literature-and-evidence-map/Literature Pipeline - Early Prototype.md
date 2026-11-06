To build an automated literature ingestion pipeline tailored to your Columbia research agenda—spanning climate adaptation, conflict economics, and causal-ML—the most robust approach couples structured academic APIs with a local knowledge hub.

**Target Faculty Seed Set**
From your memo, seed your initial queries with the following Columbia faculty:

* **Tier 1 (Core Alignment):** Daniel Björkegren (manipulation-robust prediction), Jack Willis (crop insurance/value-chain finance), Alexander de Sherbinin (climate-forced displacement).


* **Tier 2 (Conflict & Political Economy):** Macartan Humphreys, Page Fortna, Suresh Naidu, Eric Verhoogen.



---

**Recommended End-to-End Architecture**

| Stage | Tool / API | Function |
| --- | --- | --- |
| **Discovery & Filtering** | **OpenAlex API** & **Semantic Scholar API** | Programmatic metadata extraction, citation graph expansion, and filtering by Columbia affiliation ID or OpenAlex Author ID. |
| **Access & Full-Text Resolution** | **Unpaywall API** / **Columbia EZProxy** / **arXiv API** | Resolves DOIs to legal Open Access (OA) PDF links or institutionally authenticated full text. |
| **Reference & PDF Management** | **Zotero** (`pyzotero` + *Better BibTeX*) | Ingestion hub, auto-renaming, metadata tagging, and local PDF storage. |
| **Knowledge Hub / RAG** | **Obsidian** or a local Vector DB (`Chroma` / `LlamaIndex` + `pymupdf4llm`) | Markdown-formatted literature notes, semantic search, and full-text embedding. |

---

**Step-by-Step Implementation**

**1. Programmatic Discovery via OpenAlex**
Query the OpenAlex REST API to fetch all recent publications from target Columbia faculty, tracking forward/backward citation graphs.

```python
import requests

# OpenAlex Author IDs or Columbia ROR ID (https://ror.org/00hj8s172)
params = {
    "filter": "institutions.ror:https://ror.org/00hj8s172,default.search:climate+conflict+displacement",
    "per-page": 50,
    "mailto": "your_uni@columbia.edu" # Places you in the fast OpenAlex polite pool
}
response = requests.get("https://api.openalex.org/works", params=params)
works = response.json().get("results", [])

```

**2. Full-Text Scraping & Resolution**

* **Open Access (OA) First:** Query Unpaywall (`[https://api.unpaywall.org/v2/](https://api.unpaywall.org/v2/){doi}?email=your_uni@columbia.edu`) to retrieve `best_oa_location.url_for_pdf`.
* **Columbia Library Proxy:** For gated articles, pass the target DOI or publisher URL through the Columbia EZProxy resolver prefix: `[https://ezproxy.cul.columbia.edu/login?url=https://doi.org/](https://ezproxy.cul.columbia.edu/login?url=https://doi.org/){doi}`.
* **Preprint Aggregators:** Route arXiv/RePEc/SSRN identifiers directly via the `arxiv` Python package or standard scrapers.

**3. Ingestion into Local Knowledge Hub**

* **Reference Management:** Use `pyzotero` or the Zotero Desktop connector to push bibliographic entries into specific sub-collections (e.g., *Climate-Conflict*, *Digital-Finance*).


* **PDF-to-Markdown Extraction:** Convert fetched PDFs into clean, LLM-ready markdown using `pymupdf4llm` or `marker-pdf`:
```python
import pymupdf4llm
# Converts multi-column academic PDF text, math, and tables into markdown
md_text = pymupdf4llm.to_markdown("downloaded_paper.pdf")
with open("vault/papers/paper_key.md", "w") as f:
    f.write(md_text)

```


* **Local Indexing:** Sync the Markdown files directly into an Obsidian vault or index them into an embedded vector store (`chromadb`) for semantic querying alongside your evidence map notes.



Would you like a complete Python script template that takes a list of faculty names, fetches their recent papers via OpenAlex/Unpaywall, and auto-generates Markdown summaries in your local directory?


This complete script queries the OpenAlex API for target faculty affiliated with Columbia University, extracts their open-access PDFs via Unpaywall/OpenAlex, converts them to Markdown using `pymupdf4llm`, and structures them with YAML frontmatter ready for your local Markdown knowledge hub (e.g., Obsidian or a local RAG vector store).

### Prerequisites

Install the required Python dependencies:

```bash
pip install requests pymupdf4llm

```

---

### Ingestion Script (`lit_harvester.py`)

```python
import os
import re
import time
import requests
import pymupdf4llm

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
POLITE_EMAIL = "your_uni@columbia.edu"  # Enables OpenAlex fast polite pool
COLUMBIA_ROR = "https://ror.org/00hj8s172"
OUTPUT_DIR = "./knowledge_hub/papers"
PDF_DIR = "./knowledge_hub/pdfs"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Target faculty based on your research plan tiers
FACULTY_TARGETS = [
    # Tier 1: Flagship & Methodological Anchors
    "Daniel Björkegren",
    "Jack Willis",
    "Alexander de Sherbinin",
    # Tier 2: Conflict & Political Economy Adjacent
    "Macartan Humphreys",
    "Page Fortna",
    "Suresh Naidu",
    "Eric Verhoogen",
]

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def sanitize_filename(name: str) -> str:
    """Sanitize strings for filesystem-safe naming."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)[:60]


def get_author_id(faculty_name: str) -> str | None:
    """Resolve an author's OpenAlex ID filtered by Columbia affiliation."""
    url = "https://api.openalex.org/authors"
    params = {
        "search": faculty_name,
        "filter": f"last_known_institutions.ror:{COLUMBIA_ROR}",
        "mailto": POLITE_EMAIL,
    }
    res = requests.get(url, params=params).json()
    results = res.get("results", [])
    if results:
        return results[0]["id"]
    
    # Fallback to general search if affiliation matching is too strict
    fallback_params = {"search": faculty_name, "mailto": POLITE_EMAIL}
    fallback_res = requests.get(url, params=fallback_params).json()
    fallback_results = fallback_res.get("results", [])
    return fallback_results[0]["id"] if fallback_results else None


def fetch_author_works(author_id: str, limit: int = 10) -> list[dict]:
    """Retrieve top cited or recent works for an author."""
    url = "https://api.openalex.org/works"
    params = {
        "filter": f"author.id:{author_id}",
        "sort": "publication_year:desc,cited_by_count:desc",
        "per-page": limit,
        "mailto": POLITE_EMAIL,
    }
    res = requests.get(url, params=params).json()
    return res.get("results", [])


def download_pdf(pdf_url: str, dest_path: str) -> bool:
    """Download a PDF file from an open URL."""
    try:
        headers = {"User-Agent": f"ResearchBot/1.0 ({POLITE_EMAIL})"}
        response = requests.get(pdf_url, headers=headers, timeout=20, stream=True)
        if response.status_code == 200 and "application/pdf" in response.headers.get("Content-Type", ""):
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"      [!] PDF download failed: {e}")
    return False


# ---------------------------------------------------------
# Pipeline Execution
# ---------------------------------------------------------
def main():
    print("[+] Starting literature ingestion pipeline...")

    for faculty in FACULTY_TARGETS:
        print(f"\n[+] Resolving faculty: {faculty}")
        author_id = get_author_id(faculty)
        if not author_id:
            print(f"    [-] Could not resolve OpenAlex ID for {faculty}. Skipping.")
            continue

        print(f"    [>] Found Author ID: {author_id}")
        works = fetch_author_works(author_id, limit=5)
        print(f"    [>] Processing {len(works)} works...")

        for work in works:
            title = work.get("title", "Untitled")
            year = work.get("publication_year", "Unknown")
            doi = work.get("doi", "No DOI")
            oa_info = work.get("open_access", {})
            pdf_url = oa_info.get("oa_url")
            
            safe_title = sanitize_filename(title)
            doc_key = f"{year}_{safe_title}"
            md_path = os.path.join(OUTPUT_DIR, f"{doc_key}.md")
            pdf_path = os.path.join(PDF_DIR, f"{doc_key}.pdf")

            if os.path.exists(md_path):
                print(f"    [=] Already indexed: {title[:50]}...")
                continue

            print(f"    [+] Processing: {title[:50]}... ({year})")

            # PDF Extraction & Markdown Conversion
            extracted_fulltext = ""
            if pdf_url and download_pdf(pdf_url, pdf_path):
                try:
                    # Convert academic PDF text, tables, and formulae to Markdown
                    extracted_fulltext = pymupdf4llm.to_markdown(pdf_path)
                except Exception as e:
                    extracted_fulltext = f"*Error converting PDF to Markdown: {e}*"
            else:
                extracted_fulltext = "*Full-text PDF not accessible via Open Access resolver.*"

            # Generate Markdown Note with Structured Frontmatter
            abstract = ""
            inverted_index = work.get("abstract_inverted_index")
            if inverted_index:
                word_index = []
                for word, positions in inverted_index.items():
                    for pos in positions:
                        word_index.append((pos, word))
                abstract = " ".join([w[1] for w in sorted(word_index)])

            markdown_content = f"""---
title: "{title.replace('"', "'")}"
authors: "{faculty}"
year: {year}
doi: "{doi}"
pdf_url: "{pdf_url if pdf_url else ''}"
open_access: {oa_info.get('is_oa', False)}
tags:
  - literature-review
  - columbia-faculty
---

# {title}

**Faculty:** {faculty}  
**Year:** {year}  
**DOI:** [{doi}]({doi})  

## Abstract
{abstract if abstract else '_No abstract provided in metadata._'}

---

## Extracted Full Text
{extracted_fulltext}
"""
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Respect API rate limits
            time.sleep(0.2)

    print("\n[✓] Ingestion complete. Markdown files written to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()

```

---

### What the Output Looks Like

For each paper, the script produces a structured `.md` document inside `./knowledge_hub/papers/`:

```markdown
---
title: "Predicting and Coping with Natural Disaster Vulnerability"
authors: "Alexander de Sherbinin"
year: 2024
doi: "https://doi.org/10.1016/..."
pdf_url: "https://.../article.pdf"
open_access: true
tags:
  - literature-review
  - columbia-faculty
---

# Predicting and Coping with Natural Disaster Vulnerability

**Faculty:** Alexander de Sherbinin  
**Year:** 2024  
**DOI:** [https://doi.org/...](https://doi.org/...)  

## Abstract
This study evaluates climate-forced displacement patterns...

---

## Extracted Full Text
[Clean multi-column text, parsed tables, and embedded equations from the PDF]

```

Would you like to extend this script to interface directly with Zotero (via `pyzotero`) so entries are also synced to a specific reference collection?




To enable semantic search over your literature collection, install `chromadb` and `sentence-transformers`:

```bash
pip install chromadb sentence-transformers

```

This indexing module chunks your extracted Markdown papers, embeds them locally using `BAAI/bge-small-en-v1.5` or `all-MiniLM-L6-v2`, and persists the index to disk for semantic retrieval.

---

### Local Vector Store & Search Module (`lit_vector_indexer.py`)

```python
import os
import glob
import re
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
CHROMA_PATH = "./knowledge_hub/chroma_db"
PAPERS_DIR = "./knowledge_hub/papers"
COLLECTION_NAME = "columbia_faculty_lit"

# High-performance local embedding model (runs completely offline on CPU/GPU)
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# ---------------------------------------------------------
# Chunking & Parsing Helpers
# ---------------------------------------------------------
def parse_markdown_metadata(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and paper body."""
    meta = {}
    body = content
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if frontmatter_match:
        yaml_text, body = frontmatter_match.groups()
        for line in yaml_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """Split text into overlapping token/word chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if len(chunk.strip()) > 50:  # Skip trivial fragments
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# ---------------------------------------------------------
# Vector Ingestion
# ---------------------------------------------------------
def index_papers():
    print(f"[+] Initializing Persistent ChromaDB Client at '{CHROMA_PATH}'...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        normalize_embeddings=True
    )
    
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    md_files = glob.glob(os.path.join(PAPERS_DIR, "*.md"))
    print(f"[+] Found {len(md_files)} markdown files in '{PAPERS_DIR}'")

    for file_path in md_files:
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        meta, body = parse_markdown_metadata(content)
        faculty = meta.get("authors", "Unknown")
        year = str(meta.get("year", "Unknown"))
        title = meta.get("title", filename)
        doi = meta.get("doi", "")

        chunks = chunk_text(body, chunk_size=400, overlap=60)
        if not chunks:
            continue

        ids = [f"{filename}_chunk_{idx}" for idx in range(len(chunks))]
        documents = chunks
        metadatas = [
            {
                "source_file": filename,
                "title": title[:100],
                "faculty": faculty,
                "year": year,
                "doi": doi
            }
            for _ in chunks
        ]

        # Upsert chunks into Chroma
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        print(f"    [✓] Indexed: {title[:40]}... ({len(chunks)} chunks)")

    print(f"\n[✓] Indexing complete. Total indexed chunks: {collection.count()}")


# ---------------------------------------------------------
# Semantic Query Interface
# ---------------------------------------------------------
def query_literature(query_text: str, n_results: int = 4, faculty_filter: str = None):
    """Query the local index semantically with optional metadata filtering."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        normalize_embeddings=True
    )
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)

    where_clause = {"faculty": faculty_filter} if faculty_filter else None

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_clause
    )

    print(f"\n=======================================================")
    print(f"QUERY: \"{query_text}\"")
    if faculty_filter:
        print(f"FILTER: Faculty = {faculty_filter}")
    print(f"=======================================================")

    for i in range(len(results["ids"][0])):
        doc_meta = results["metadatas"][0][i]
        doc_text = results["documents"][0][i]
        distance = results["distances"][0][i] if "distances" in results else None

        print(f"\n[{i+1}] {doc_meta['title']} ({doc_meta['year']})")
        print(f"    Author: {doc_meta['faculty']} | Source: {doc_meta['source_file']}")
        if distance is not None:
            print(f"    Cosine Distance: {distance:.4f}")
        print(f"    Snippet:\n    {doc_text[:350]}...\n")


if __name__ == "__main__":
    # Step 1: Run indexing over the folder
    index_papers()

    # Step 2: Test semantic query across all faculty papers
    query_literature(
        query_text="manipulation robust machine learning and credit scoring algorithms",
        n_results=3
    )

    # Step 3: Test filtered query targeting specific faculty domains
    query_literature(
        query_text="climate forced migration and population displacement vulnerability",
        n_results=2,
        faculty_filter="Alexander de Sherbinin"
    )

```

---

### Pipeline Capabilities

* **Local Persistence & Zero API Cost:** The SQLite-backed store and embeddings execute entirely on local compute without third-party token fees.
* **Metadata-Constrained Filtering:** Allows targeted queries either across the whole corpus or filtered directly by author (e.g., querying only *Björkegren* papers for ML manipulation checks or *de Sherbinin* papers for displacement data).


* **Obsidian-Compatible Traceability:** Every chunk retains its exact filename, DOI, and year metadata, enabling direct reference linking back to your source notes and Zotero items.

Would you like to wrap this retrieval engine in a local CLI or LangChain RAG pipeline to generate literature review synthesis memos directly from your retrieved chunks?









To generate structured academic synthesis memos directly from your indexed corpus, you can couple **LangChain** with a local LLM runner like **Ollama** (e.g., `llama3.1:8b` or `qwen2.5:14b`) and your existing persistent **ChromaDB** store.

### Environment Setup

Install the required LangChain and Ollama dependencies:

```bash
pip install langchain langchain-community langchain-chroma langchain-ollama

```

Ensure Ollama is running locally with your target model pulled:

```bash
ollama run llama3.1:8b

```

---

### Local Literature Synthesis Pipeline (`lit_rag_memo.py`)

```python
import argparse
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
CHROMA_PATH = "./knowledge_hub/chroma_db"
COLLECTION_NAME = "columbia_faculty_lit"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
LOCAL_LLM = "llama3.1:8b"

# ---------------------------------------------------------
# Academic Synthesis Prompt Template
# ---------------------------------------------------------
SYNTHESIS_TEMPLATE = """You are an expert academic research assistant preparing literature review memos for a doctoral researcher at Columbia University.

Analyze the retrieved document excerpts below to address the user's research topic. 
Your synthesis must:
1. Identify the core theoretical mechanisms and empirical methodologies used across the papers.
2. Highlight areas of methodological consensus, divergence, and remaining empirical gaps.
3. Explicitly attribute arguments to specific authors and publication years based on the provided metadata.
4. Conclude with 2–3 concrete, testable extensions relevant to climate adaptation, conflict economics, or causal ML.

Context:
{context}

Research Query / Memo Topic:
{question}

Academic Synthesis Memo:
"""

def format_docs(docs):
    """Format retrieved documents with rich metadata headers."""
    formatted = []
    for d in docs:
        meta = d.metadata
        header = f"--- [Source: {meta.get('title', 'Unknown')} ({meta.get('year', 'N/A')}) | Author: {meta.get('faculty', 'Unknown')}] ---"
        formatted.append(f"{header}\n{d.page_content}")
    return "\n\n".join(formatted)

def build_rag_chain(faculty_filter: str = None, top_k: int = 6):
    # Initialize offline embedding function matching the indexing phase
    embedding_fn = SentenceTransformerEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}
    )

    # Connect to persistent ChromaDB instance
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_PATH,
        embedding_function=embedding_fn,
    )

    # Configure metadata search filters
    search_kwargs = {"k": top_k}
    if faculty_filter:
        search_kwargs["filter"] = {"faculty": faculty_filter}

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)

    # Initialize local Ollama model
    llm = ChatOllama(
        model=LOCAL_LLM,
        temperature=0.1,  # Low temperature for analytical rigor
    )

    prompt = ChatPromptTemplate.from_template(SYNTHESIS_TEMPLATE)

    # LCEL (LangChain Expression Language) Chain
    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain, retriever

def main():
    parser = argparse.ArgumentParser(description="Generate literature review memos from local vector hub.")
    parser.add_argument("--query", type=str, required=True, help="Research topic or synthesis prompt.")
    parser.add_argument("--faculty", type=str, default=None, help="Filter synthesis to a specific author.")
    parser.add_argument("--k", type=int, default=6, help="Number of retrieved chunks to include in context.")
    parser.add_argument("--out", type=str, default=None, help="Path to save output Markdown memo.")
    
    args = parser.parse_args()

    print(f"[+] Initializing local RAG pipeline with model: {LOCAL_LLM}...")
    chain, retriever = build_rag_chain(faculty_filter=args.faculty, top_k=args.k)

    print(f"[+] Retrieving top {args.k} relevant chunks for: '{args.query}'")
    if args.faculty:
        print(f"[+] Applying metadata filter: faculty == '{args.faculty}'")

    response = chain.invoke(args.query)

    print("\n" + "=" * 60)
    print("LITERATURE REVIEW SYNTHESIS MEMO")
    print("=" * 60 + "\n")
    print(response)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(f"# Synthesis: {args.query}\n\n" + response)
        print(f"\n[✓] Memo written to {args.out}")

if __name__ == "__main__":
    main()

```

---

### Command-Line Execution Examples

**Cross-Faculty Methodological Synthesis**

```bash
python lit_rag_memo.py \
  --query "How do manipulation-robust machine learning algorithms handle strategic adaptation in credit and insurance scoring?" \
  --k 6 \
  --out ./knowledge_hub/memos/memo_manipulation_robustness.md

```

**Targeted Single-Author Deep Dive**

```bash
python lit_rag_memo.py \
  --query "Empirical approaches to measuring climate-forced displacement vulnerability and data limitations" \
  --faculty "Alexander de Sherbinin" \
  --k 4 \
  --out ./knowledge_hub/memos/memo_desherbinin_displacement.md

```

---

For a step-by-step visual walkthrough on setting up embeddings, persistent stores, and local query execution, see this [Local RAG Setup with Ollama and ChromaDB Guide](https://www.youtube.com/watch?v=UuepzspChuQ). This video demonstrates the foundational architecture for connecting vector databases directly to local language models.