# Rebuild-Safety Fix for Duplicate Clone Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `index_search.py rebuild` (with or without `--prune`) safe to run over a course holding a cross-course duplicate "clone" card, by teaching it to recognize and skip clone directories instead of re-hashing them.

**Architecture:** `indexer/duplicate_check.py`'s `copy_duplicate_artifacts` starts writing a `duplicate_of_file_id` marker into the copied `_metadata.json` on disk (today it's only ever written onto the index card, which `rebuild()`'s file-walk never reads). `indexer/index_search.py`'s `rebuild()` then checks for that marker before hashing a book directory's PDF, and if present, skips reconciliation entirely and instead marks the clone's own (already-correct, derived) card id as "seen" so `--prune` doesn't evict it.

**Tech Stack:** Python 3 stdlib only, `unittest` (matches this repo's existing test conventions in `tests/test_duplicate_check.py` and `tests/test_index_search.py`).

**Spec:** `docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`, Component 3.

## Global Constraints

- No change to Tier 1/Tier 2 detection or scoring logic in `duplicate_check.py` — only the metadata write and the rebuild-side read.
- No backfill for clones created before this fix ships — an old clone's `_metadata.json` has no `duplicate_of_file_id` field and will not be recognized retroactively; this matches this repo's established "no backfill" convention for additive fields (see the VM RAM-sizing spec's own explicit non-goal).
- The metadata write in `copy_duplicate_artifacts` must share the existing `try`/`except` block around that file's rewrite (one more dict key before the same write call), not introduce a new failure path.
- Every new test follows this repo's existing conventions exactly: `tests/test_duplicate_check.py`'s `TestCopyDuplicateArtifacts._make_canonical_book` fixture shape, and `tests/test_index_search.py`'s `_make_textbook`/`_fake_client` helpers — do not invent new fixture patterns where an existing one already fits.

---

### Task 1: Write `duplicate_of_file_id` into the copied `_metadata.json`

**Files:**
- Modify: `indexer/duplicate_check.py` (function `copy_duplicate_artifacts`, the metadata-rewrite block currently at lines 287-298)
- Test: `tests/test_duplicate_check.py` (add to the existing `TestCopyDuplicateArtifacts` class)

**Interfaces:**
- Consumes: nothing new — `canonical_card["file_id"]` is already a parameter available in this function's scope.
- Produces: no signature change to `copy_duplicate_artifacts` — the returned `new_card` dict already carries `duplicate_of_file_id` (unchanged); this task additionally writes that same value into the on-disk `_metadata.json` copy, which Task 2 will read.

- [ ] **Step 1: Write the failing test**

Add this method to the `TestCopyDuplicateArtifacts` class in `tests/test_duplicate_check.py` (place it right after `test_copied_metadata_is_repointed_at_the_new_courses_pdf`, which it extends):

```python
    def test_copied_metadata_gets_a_duplicate_of_file_id_marker(self):
        # New behavior (pipeline-autonomy-policies spec, Component 3):
        # index_search.py's rebuild() needs to recognize a clone directory
        # from its on-disk _metadata.json alone -- it never reads the
        # index card while walking book directories on disk. This marker
        # is what lets rebuild() skip re-hashing a clone instead of
        # colliding with the canonical book's own file_id.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            copied_metadata_path = os.path.join(
                academic_hub_root, "academic_resources", "microecon", "textbooks",
                "processed_outputs", folder_name, f"{folder_name}_metadata.json",
            )
            with open(copied_metadata_path, encoding="utf-8") as f:
                copied = json.load(f)
            self.assertEqual(copied["duplicate_of_file_id"], "canonical-fid")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_duplicate_check.py::TestCopyDuplicateArtifacts::test_copied_metadata_gets_a_duplicate_of_file_id_marker -v`
Expected: FAIL with `KeyError: 'duplicate_of_file_id'`

- [ ] **Step 3: Implement**

In `indexer/duplicate_check.py`, find this exact block (the metadata-rewrite section of `copy_duplicate_artifacts`):

```python
    # The copied _metadata.json is a byte-for-byte clone and so still names
    # the CANONICAL course's PDF. index_search.py's `rebuild` textbook
    # backfill reads source_pdf_path (not source_pdf_file_id -- that field
    # is written but never read back by rebuild) to locate a file to hash
    # via compute_file_id(), then derives `course_name` from that same
    # path string. Repointing source_pdf_path at the new course's own PDF
    # keeps `_metadata.json` internally consistent (describe_images.py
    # does key off source_pdf_file_id) and is directionally correct, but
    # it is NOT a reliable fix for the rebuild-corruption risk itself --
    # see spec §6a. In particular, for a Tier 1 (byte-identical) clone,
    # repointing this field makes rebuild MORE likely to evict the
    # canonical card from its own course shard, not less, because hashing
    # the new course's copy yields the same file_id as canonical either
    # way. Do not treat this rewrite as closing that risk. A failure here
    # leaves an already-successful copy in place, so it warns rather than
    # unwinding the whole copy.
    metadata_path = os.path.join(new_book_dir, f"{folder_name}_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            metadata["source_pdf_path"] = new_source_pdf_path
            metadata["source_pdf_file_id"] = new_file_id
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
        except Exception as err:
            print(f"WARNING: could not repoint {folder_name}_metadata.json at the new course's PDF ({err}); "
                  f"a future `index_search.py rebuild` over {new_course!r} may misattribute this book.", file=sys.stderr)
```

Replace it with:

```python
    # The copied _metadata.json is a byte-for-byte clone and so still names
    # the CANONICAL course's PDF. index_search.py's `rebuild` textbook
    # backfill reads source_pdf_path (not source_pdf_file_id -- that field
    # is written but never read back by rebuild) to locate a file to hash
    # via compute_file_id(), then derives `course_name` from that same
    # path string. Repointing source_pdf_path at the new course's own PDF
    # keeps `_metadata.json` internally consistent (describe_images.py
    # does key off source_pdf_file_id) and is directionally correct, but
    # it is NOT what actually prevents rebuild-corruption for a Tier 1
    # (byte-identical) clone -- hashing the new course's copy always
    # yields the same file_id as canonical, repointed or not. The
    # `duplicate_of_file_id` field written below is what actually fixes
    # that: index_search.py's rebuild() recognizes it and skips re-hashing
    # this directory entirely (see
    # docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md
    # Component 3). A failure here leaves an already-successful copy in
    # place, so it warns rather than unwinding the whole copy.
    metadata_path = os.path.join(new_book_dir, f"{folder_name}_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            metadata["source_pdf_path"] = new_source_pdf_path
            metadata["source_pdf_file_id"] = new_file_id
            metadata["duplicate_of_file_id"] = canonical_card["file_id"]
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
        except Exception as err:
            print(f"WARNING: could not repoint {folder_name}_metadata.json at the new course's PDF ({err}); "
                  f"a future `index_search.py rebuild` over {new_course!r} may misattribute this book.", file=sys.stderr)
```

- [ ] **Step 4: Run the test to verify it passes, and re-run the whole class for regressions**

Run: `pytest tests/test_duplicate_check.py::TestCopyDuplicateArtifacts -v`
Expected: PASS (all tests in the class, including the new one and every pre-existing one — this confirms the one-line addition didn't disturb the existing repoint behavior).

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): mark a duplicate clone's on-disk metadata with duplicate_of_file_id

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `rebuild()` recognizes and skips clone directories

**Files:**
- Modify: `indexer/index_search.py` (function `rebuild`, the textbook loop currently at lines 383-476, plus the `stats` dict initialized at line 385)
- Test: `tests/test_index_search.py` (add to the existing `TestRebuild` class)

**Interfaces:**
- Consumes: `indexer.index_card.compute_id_from_parts` (already imported in this file), `indexer.index_card.derive_course` (already imported), the on-disk `_metadata.json`'s `duplicate_of_file_id` field written by Task 1.
- Produces: `rebuild()`'s returned `stats` dict gains a new key, `"skipped_duplicate_clone"` (int, starts at 0) — no other signature change.

- [ ] **Step 1: Write the failing tests**

Add these two methods to the `TestRebuild` class in `tests/test_index_search.py` (place them after `test_backfills_rag_md_path_from_metadata_when_card_is_missing_it`, which shares its post-hoc-metadata-edit pattern):

```python
    def test_rebuild_recognizes_a_clone_directory_and_never_rehashes_it(self):
        # Regression for the original corruption bug (pipeline-autonomy-
        # policies spec, Component 3): a Tier 1 (byte-identical) clone's
        # PDF hashes to the SAME file_id as the canonical book -- before
        # this fix, rebuild()'s textbook loop would recompute that hash,
        # find no card under it in the clone's OWN course shard, and fall
        # through to reconcile_and_write's cross-course "file moved"
        # handling, which relocated the canonical card out of its own
        # shard entirely. A book directory whose _metadata.json carries
        # duplicate_of_file_id must never be re-hashed or reconciled.
        with tempfile.TemporaryDirectory() as tmp:
            # Same pdf_basename ("Ok") in both calls -- _make_textbook's
            # fake PDF bytes are derived only from pdf_basename, so they
            # come out byte-identical, exactly reproducing the real Tier 1
            # collision.
            canonical_pdf = _make_textbook(tmp, "econometrics", "Ok", "Ok_RealAnalysis_2007")
            clone_pdf = _make_textbook(tmp, "microecon", "Ok", "Ok_RealAnalysis_2007")

            canonical_file_id = compute_file_id(canonical_pdf)
            rel_canonical_pdf = os.path.relpath(canonical_pdf, tmp).replace(os.sep, "/")
            save_shard(tmp, "econometrics", [{
                "file_id": canonical_file_id,
                "path": "academic_resources/econometrics/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": rel_canonical_pdf, "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "canonical-hash",
            }])

            from indexer.index_card import compute_id_from_parts
            clone_file_id = compute_id_from_parts([canonical_file_id, "microecon"])
            rel_clone_pdf = os.path.relpath(clone_pdf, tmp).replace(os.sep, "/")
            save_shard(tmp, "microecon", [{
                "file_id": clone_file_id,
                "path": "academic_resources/microecon/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": rel_clone_pdf, "course": "microecon",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "clone-hash",
                "duplicate_of_file_id": canonical_file_id,
            }])

            clone_metadata_path = os.path.join(
                os.path.dirname(clone_pdf), "processed_outputs", "Ok_RealAnalysis_2007",
                "Ok_RealAnalysis_2007_metadata.json",
            )
            with open(clone_metadata_path, encoding="utf-8") as f:
                clone_metadata = json.load(f)
            clone_metadata["duplicate_of_file_id"] = canonical_file_id
            with open(clone_metadata_path, "w", encoding="utf-8") as f:
                json.dump(clone_metadata, f)

            client = _fake_client()
            stats = rebuild(tmp, client=client)

            # The canonical card must still be in ITS OWN shard, under its
            # own file_id -- not relocated into microecon.
            canonical_cards = load_shard(tmp, "econometrics")
            self.assertEqual(len(canonical_cards), 1)
            self.assertEqual(canonical_cards[0]["file_id"], canonical_file_id)

            # The clone's card is untouched -- still present, still its own
            # derived file_id and content_hash, never overwritten.
            clone_cards = load_shard(tmp, "microecon")
            self.assertEqual(len(clone_cards), 1)
            self.assertEqual(clone_cards[0]["file_id"], clone_file_id)
            self.assertEqual(clone_cards[0]["content_hash"], "clone-hash")

            self.assertEqual(stats["skipped_duplicate_clone"], 1)
            # Only the canonical book's own (pre-existing, unchanged) card
            # means no LLM call was made at all in this run.
            self.assertEqual(client.models.generate_content.call_count, 0)

    def test_rebuild_prune_does_not_evict_a_clone_marked_seen(self):
        # A clone card is never "backed by a re-hashed PDF" the normal
        # way -- without adding its own derived id to seen_file_ids,
        # --prune would treat it as an orphan and delete it.
        with tempfile.TemporaryDirectory() as tmp:
            canonical_pdf = _make_textbook(tmp, "econometrics", "Ok", "Ok_RealAnalysis_2007")
            clone_pdf = _make_textbook(tmp, "microecon", "Ok", "Ok_RealAnalysis_2007")
            canonical_file_id = compute_file_id(canonical_pdf)
            from indexer.index_card import compute_id_from_parts
            clone_file_id = compute_id_from_parts([canonical_file_id, "microecon"])

            save_shard(tmp, "econometrics", [{
                "file_id": canonical_file_id,
                "path": "academic_resources/econometrics/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": os.path.relpath(canonical_pdf, tmp).replace(os.sep, "/"),
                "course": "econometrics", "doc_type": "textbook", "title": "T",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "canonical-hash",
            }])
            save_shard(tmp, "microecon", [{
                "file_id": clone_file_id,
                "path": "academic_resources/microecon/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": os.path.relpath(clone_pdf, tmp).replace(os.sep, "/"),
                "course": "microecon", "doc_type": "textbook", "title": "T",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "clone-hash",
                "duplicate_of_file_id": canonical_file_id,
            }])
            clone_metadata_path = os.path.join(
                os.path.dirname(clone_pdf), "processed_outputs", "Ok_RealAnalysis_2007",
                "Ok_RealAnalysis_2007_metadata.json",
            )
            with open(clone_metadata_path, encoding="utf-8") as f:
                clone_metadata = json.load(f)
            clone_metadata["duplicate_of_file_id"] = canonical_file_id
            with open(clone_metadata_path, "w", encoding="utf-8") as f:
                json.dump(clone_metadata, f)

            stats = rebuild(tmp, client=_fake_client(), prune=True)

            self.assertEqual(stats["pruned"], 0)
            self.assertEqual(len(load_shard(tmp, "microecon")), 1)
            self.assertEqual(load_shard(tmp, "microecon")[0]["file_id"], clone_file_id)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_index_search.py::TestRebuild::test_rebuild_recognizes_a_clone_directory_and_never_rehashes_it tests/test_index_search.py::TestRebuild::test_rebuild_prune_does_not_evict_a_clone_marked_seen -v`
Expected: FAIL — without the fix, the first test's canonical card gets relocated out of `econometrics` (assertion on `len(canonical_cards) == 1` fails, since it's empty), and/or an extra `generate_content` call happens for the clone. The second test fails with `stats["pruned"] == 1` and an empty `microecon` shard.

- [ ] **Step 3: Implement**

In `indexer/index_search.py`, find the `stats` dict initialization inside `rebuild()`:

```python
def rebuild(academic_hub_root: str, client, course: str | None = None,
            force: bool = False, prune: bool = False) -> dict:
    stats = {
        "generated": 0, "updated": 0, "unchanged": 0, "moved": 0,
        "orphaned": 0, "pruned": 0, "skipped_no_source_pdf": 0, "skipped_empty_md": 0,
    }
```

Change to:

```python
def rebuild(academic_hub_root: str, client, course: str | None = None,
            force: bool = False, prune: bool = False) -> dict:
    stats = {
        "generated": 0, "updated": 0, "unchanged": 0, "moved": 0,
        "orphaned": 0, "pruned": 0, "skipped_no_source_pdf": 0, "skipped_empty_md": 0,
        "skipped_duplicate_clone": 0,
    }
```

Then find the start of the textbook loop:

```python
    for course_name, category_folder_name, folder_name, book_dir in _textbook_book_dirs(academic_hub_root, course):
        metadata_path = os.path.join(book_dir, f"{folder_name}_metadata.json")
        if not os.path.exists(metadata_path):
            continue
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        source_pdf_path = metadata.get("source_pdf_path")
```

Change to:

```python
    for course_name, category_folder_name, folder_name, book_dir in _textbook_book_dirs(academic_hub_root, course):
        metadata_path = os.path.join(book_dir, f"{folder_name}_metadata.json")
        if not os.path.exists(metadata_path):
            continue
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        duplicate_of_file_id = metadata.get("duplicate_of_file_id")
        if duplicate_of_file_id:
            # A clone directory (indexer/duplicate_check.py's
            # copy_duplicate_artifacts) -- never re-hash or reconcile it.
            # For a Tier 1 (byte-identical) clone, hashing this directory's
            # own PDF yields the SAME file_id as the canonical book, which
            # used to make reconcile_and_write's cross-course "file moved"
            # handling relocate the canonical card out of its own shard
            # (see docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md
            # Component 3). The clone's own card already exists, correctly,
            # under a derived (non-hash) id -- re-derive that same id here,
            # from data already on hand, purely so --prune doesn't evict it
            # as an apparent orphan.
            clone_course = derive_course(metadata["source_pdf_path"])
            seen_file_ids.add(compute_id_from_parts([duplicate_of_file_id, clone_course]))
            stats["skipped_duplicate_clone"] += 1
            continue

        source_pdf_path = metadata.get("source_pdf_path")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_index_search.py::TestRebuild -v`
Expected: PASS (both new tests, and every pre-existing test in `TestRebuild` — this is the regression check confirming the non-clone reconciliation paths — generated/updated/unchanged/moved/orphaned/pruned — are unaffected by this change).

- [ ] **Step 5: Commit**

```bash
git add indexer/index_search.py tests/test_index_search.py
git commit -m "fix(indexer): rebuild() skips duplicate clone directories instead of re-hashing them

Resolves the known corruption risk where rebuild()'s cross-course
'file moved' handling could relocate a canonical card out of its own
shard when a Tier 1 clone existed elsewhere.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: End-to-end integration test using the real duplicate-check flow

**Files:**
- Test only: `tests/test_index_search.py` (new test in `TestRebuild`, or a small new test class `TestRebuildWithRealDuplicateClone` placed right after `TestRebuild` — use the new class, since it needs an import `duplicate_check.py` doesn't otherwise need in this file)

**Interfaces:**
- Consumes: `indexer.duplicate_check.copy_duplicate_artifacts` (Task 1's fix already landed inside it), `indexer.index_search.rebuild` (Task 2's fix).
- Produces: nothing new — this task only adds test coverage confirming the two independently-tested halves (Task 1's write, Task 2's read) work correctly together, using the real production code path a real conversion run would exercise, not hand-fabricated metadata.

- [ ] **Step 1: Write the failing test**

Add this new class at the end of `tests/test_index_search.py`, just before the `if __name__ == "__main__":` line:

```python
class TestRebuildWithRealDuplicateClone(unittest.TestCase):
    """Integration coverage: Task 1 (duplicate_check.py writes the marker)
    and Task 2 (index_search.py reads it) tested together via the real
    production functions, not hand-fabricated metadata -- confirms the
    fix actually closes the loop end to end, the way a real conversion
    run's duplicate-check step and a later `rebuild` would encounter it."""

    def test_a_real_copy_duplicate_artifacts_clone_survives_rebuild(self):
        from indexer.duplicate_check import copy_duplicate_artifacts
        from indexer.index_card import compute_id_from_parts

        with tempfile.TemporaryDirectory() as tmp:
            canonical_pdf = _make_textbook(tmp, "econometrics", "Ok", "Ok_RealAnalysis_2007")
            canonical_file_id = compute_file_id(canonical_pdf)
            rel_canonical_pdf = os.path.relpath(canonical_pdf, tmp).replace(os.sep, "/")

            canonical_card = {
                "file_id": canonical_file_id,
                "path": "academic_resources/econometrics/textbooks-and-papers/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": rel_canonical_pdf, "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
                "embedding": [0.1, 0.2], "tags": [], "needs_indexing": False,
                "source_updated_at": "2026-01-01T00:00:00+00:00", "content_hash": "canonical-hash",
            }
            save_shard(tmp, "econometrics", [canonical_card])

            # The real production call, exactly as duplicate_check.py's
            # run_duplicate_check makes it on a confirmed Tier 1 match --
            # the new course's PDF path is fabricated here (not written to
            # disk) since copy_duplicate_artifacts never reads the new
            # PDF's own bytes, only the canonical book directory's.
            copy_duplicate_artifacts(
                tmp, "econometrics", canonical_card, "microecon", "textbooks-and-papers",
                "academic_resources/microecon/textbooks-and-papers/Ok.pdf",
            )

            client = _fake_client()
            stats = rebuild(tmp, client=client)

            # The canonical card is untouched, in its own shard.
            self.assertEqual(len(load_shard(tmp, "econometrics")), 1)
            self.assertEqual(load_shard(tmp, "econometrics")[0]["file_id"], canonical_file_id)

            # The clone survives, under its real derived id.
            clone_file_id = compute_id_from_parts([canonical_file_id, "microecon"])
            clone_cards = load_shard(tmp, "microecon")
            self.assertEqual(len(clone_cards), 1)
            self.assertEqual(clone_cards[0]["file_id"], clone_file_id)
            self.assertEqual(stats["skipped_duplicate_clone"], 1)

            # A subsequent --prune still doesn't touch either course.
            prune_stats = rebuild(tmp, client=_fake_client(), prune=True)
            self.assertEqual(prune_stats["pruned"], 0)
            self.assertEqual(len(load_shard(tmp, "econometrics")), 1)
            self.assertEqual(len(load_shard(tmp, "microecon")), 1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_index_search.py::TestRebuildWithRealDuplicateClone -v`
Expected: FAIL without Tasks 1-2 landed (or PASS if run after them — since this task is sequenced last, run it now to confirm it genuinely exercises the fix: temporarily comment out Task 2's `if duplicate_of_file_id:` branch, confirm this test fails, then restore it).

- [ ] **Step 3: Run the full test suite**

Run: `pytest tests/test_duplicate_check.py tests/test_index_search.py -v`
Expected: PASS — every test in both files, confirming no regression anywhere across the two modules this plan touches.

- [ ] **Step 4: Commit**

```bash
git add tests/test_index_search.py
git commit -m "test(indexer): add end-to-end coverage for the duplicate-clone rebuild fix

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Update the original duplicate-detection spec's known-limitations section

**Files:**
- Modify: `docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md` (section "## 6a. Known limitations")

**Interfaces:** None — documentation only.

- [ ] **Step 1: Update the known-limitations section**

Find the paragraph in `docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md` that begins:

```
**Duplicate-clone cards are outside `index_search.py`'s file_id
reconciliation model.** That module assumes one card per real file, with
```

Immediately before that paragraph, insert:

```markdown
**Update (2026-09-20): fixed.** The corruption risk described below is
resolved as of
`docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`
Component 3 — `copy_duplicate_artifacts` now marks a clone's on-disk
`_metadata.json` with `duplicate_of_file_id`, and `index_search.py`'s
`rebuild()` recognizes that marker and skips re-hashing the directory
entirely instead of colliding with the canonical card's file_id.
`rebuild`/`--prune` are now safe to run over a course holding a clone
created after this fix shipped. The mechanism section below is kept as
the historical record of the original bug and why the fix works, not as
a still-open warning.

```

- [ ] **Step 2: Verify code-fence balance**

Run: `grep -c '^```' docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md`
Expected: an even count (the new markdown block above adds one open/close pair, keeping the file balanced).

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md
git commit -m "docs(spec): mark the rebuild-corruption known limitation as fixed

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Run the full project test suite once more: `pytest tests/ -q` — expect all green, no regressions anywhere in the repo (not just the two files this plan touches).
- [ ] `grep -n "duplicate_of_file_id" indexer/duplicate_check.py indexer/index_search.py` shows the write (Task 1) and the read (Task 2).
- [ ] `grep -n "skipped_duplicate_clone" indexer/index_search.py` shows both the stats-dict initialization and the increment.

## Self-Review Notes

- **Spec coverage:** Component 3's two numbered fix steps map directly to Task 1 (the metadata write) and Task 2 (the rebuild-side read/skip); the "resolves both known failure modes" claim is covered by Task 2's Tier-1-collision regression test plus the existing `TestRebuild` suite continuing to pass (Tier 2's redundant-generation case never enters the changed code path differently — it's the same `duplicate_of_file_id` check, tier-agnostic); Component 3's Documentation-updates item (the spec §6a note) is Task 4; the memory item mentioned in the design spec's Documentation section is intentionally left out of this plan (it targets an assistant memory file outside the repo, not code) and will be updated separately once this plan ships.
- **Placeholder scan:** no TBD/TODO; every step shows real, complete code matching the actual current content of both files (verified by reading them directly before writing this plan, not from an earlier draft).
- **Type/signature consistency:** `copy_duplicate_artifacts`'s signature is unchanged (Task 1 only adds a dict key internally); `rebuild()`'s signature is unchanged (Task 2 only adds a `stats` dict key). Checked against the real, current file contents of `indexer/duplicate_check.py` and `indexer/index_search.py`, not the original 2026-09-17 plan's draft code (which was found, during this session's review, to have already drifted from the shipped implementation in an unrelated spot — the dismissals path).
- **Scope:** three independently-testable code/test tasks plus one documentation task, all confined to the two files and one spec doc Component 3 names — no change to Tier 1/Tier 2 detection logic, no predictive VM sizing, no batch-splitting, matching the sibling spec's Non-goals.
