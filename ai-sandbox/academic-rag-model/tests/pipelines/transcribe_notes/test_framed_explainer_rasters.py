import fitz
import pytest

from pipelines.transcribe_notes.framed_explainer.rasters import (
    PageMappingError, rasterize_frame_pdf)


def _pdf(path, pages):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=300, height=200)
        page.draw_rect(fitz.Rect(20, 20, 20 + 40 * (i + 1), 120), color=(0, 0, 0), fill=(0, 0, 0))
    doc.save(str(path))
    return str(path)


FRAMES = [{"id": "fB", "name": "002 Slide 2"}, {"id": "fA", "name": "001 Slide 1"},
          {"id": "fC", "name": "003 Slide 3"}]


def test_maps_pages_to_frames_in_name_order(tmp_path):
    out = rasterize_frame_pdf(_pdf(tmp_path / "x.pdf", 3), FRAMES, str(tmp_path / "o"))
    assert list(out) == ["fA", "fB", "fC"]
    sizes = {k: fitz.Pixmap(v).width for k, v in out.items()}
    assert sizes["fA"] == sizes["fB"]  # same page size
    # page 1 (fA) has the narrowest block -> fewer dark pixels than page 3 (fC)
    dark = {k: sum(1 for b in fitz.Pixmap(v).samples if b < 128) for k, v in out.items()}
    assert dark["fA"] < dark["fB"] < dark["fC"]


def test_page_count_mismatch_raises(tmp_path):
    with pytest.raises(PageMappingError):
        rasterize_frame_pdf(_pdf(tmp_path / "x.pdf", 2), FRAMES, str(tmp_path / "o"))


def test_png_written_nonblank(tmp_path):
    out = rasterize_frame_pdf(_pdf(tmp_path / "x.pdf", 3), FRAMES, str(tmp_path / "o"))
    pix = fitz.Pixmap(out["fA"])
    assert len(set(pix.samples)) > 1
