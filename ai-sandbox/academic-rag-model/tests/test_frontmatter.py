from common.frontmatter import parse_frontmatter, render_frontmatter


def test_parse_frontmatter_splits_fields_and_body():
    content = "---\nsource_pdf: a.pdf\nfolder_category: ta_notes\ntotal_pages: 3\n---\n\nBody text here."
    fields, body = parse_frontmatter(content)
    assert fields == {"source_pdf": "a.pdf", "folder_category": "ta_notes", "total_pages": "3"}
    assert body == "Body text here."


def test_parse_frontmatter_preserves_raw_list_value():
    content = "---\ntags: [real-analysis, optimization]\n---\n\nBody."
    fields, _body = parse_frontmatter(content)
    assert fields["tags"] == "[real-analysis, optimization]"


def test_parse_frontmatter_no_block_returns_empty_fields_and_original_content():
    content = "Just a plain markdown file, no frontmatter."
    fields, body = parse_frontmatter(content)
    assert fields == {}
    assert body == content


def test_render_frontmatter_round_trips_with_parse():
    content = "---\nsource_pdf: a.pdf\nfolder_category: ta_notes\n---\n\nBody text."
    fields, body = parse_frontmatter(content)
    rendered = render_frontmatter(fields) + body
    assert rendered == content


def test_render_frontmatter_reflects_overridden_and_added_fields():
    fields = {"source_pdf": "old.pdf", "folder_category": "ta_notes"}
    fields["source_pdf"] = "new.pdf"
    fields["duplicate_of_file_id"] = "abc123"
    rendered = render_frontmatter(fields)
    assert "source_pdf: new.pdf" in rendered
    assert "duplicate_of_file_id: abc123" in rendered
    assert rendered.startswith("---\n")
    assert rendered.endswith("---\n\n")  # trailing blank line after the closing ---
