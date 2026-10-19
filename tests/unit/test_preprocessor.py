import io
import pytest
from PIL import Image, ImageDraw

from src.pipelines.ai.preprocessing.preprocessor import (
    CorruptDocumentError,
    DocumentLimitExceededError,
    DocumentPreprocessor,
    EncryptedDocumentError,
    PreprocessedPage,
    UnsupportedFileFormatError,
)


def _create_test_image_bytes(
    size=(600, 800),
    color=(255, 255, 255),
    text_lines=True,
    rotation_angle=0.0,
    format_name="PNG"
) -> bytes:
    img = Image.new("RGB", size, color=color)
    d = ImageDraw.Draw(img)
    if text_lines:
        for y in range(50, size[1] - 50, 40):
            d.text((50, y), f"Sample Invoice Text Line at Y={y} VND 1,000,000", fill=(0, 0, 0))
        d.line([(50, 120), (size[0] - 50, 120)], fill=(0, 0, 0), width=2)

    if abs(rotation_angle) > 0.01:
        img = img.rotate(rotation_angle, expand=True, fillcolor=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def _create_test_pdf_bytes(num_pages=2) -> bytes:
    buf = io.BytesIO()
    images = []
    for i in range(num_pages):
        img = Image.new("RGB", (600, 800), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((50, 50), f"INVOICE PAGE {i + 1}", fill=(0, 0, 0))
        images.append(img)

    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    return buf.getvalue()


class TestDocumentPreprocessorValidation:
    """Tests P0: File classification, format validation, and corrupt input rejection."""

    def test_rejects_empty_file(self):
        preprocessor = DocumentPreprocessor()
        with pytest.raises(CorruptDocumentError, match="is empty"):
            preprocessor.process(b"", "empty.pdf")

    def test_rejects_unsupported_format(self):
        preprocessor = DocumentPreprocessor()
        with pytest.raises(UnsupportedFileFormatError, match="not supported"):
            preprocessor.process(b"Some random executable binary or text data", "document.docx")

    def test_rejects_corrupted_pdf(self):
        preprocessor = DocumentPreprocessor()
        # Invalid PDF header/body
        corrupt_bytes = b"%PDF-1.4\ncorrupted damaged unparseable body %%EOF"
        with pytest.raises(CorruptDocumentError):
            preprocessor.process(corrupt_bytes, "corrupt.pdf")

    def test_rejects_corrupted_image(self):
        preprocessor = DocumentPreprocessor()
        corrupt_png = b"\x89PNG\r\n\x1a\ncorrupted data payload"
        with pytest.raises(CorruptDocumentError):
            preprocessor.process(corrupt_png, "corrupt.png")

    def test_file_size_limit_exceeded(self):
        preprocessor = DocumentPreprocessor(max_file_size_mb=1)
        large_bytes = b"0" * (2 * 1024 * 1024)  # 2MB
        with pytest.raises(DocumentLimitExceededError, match="exceeds allowed limit"):
            preprocessor.process(large_bytes, "large.png")


class TestDocumentPreprocessorImageHandling:
    """Tests real image dimensions, orientation, quality scoring, and conditional deskew."""

    def test_preserves_actual_image_dimensions(self):
        preprocessor = DocumentPreprocessor(auto_deskew=False)
        img_bytes = _create_test_image_bytes(size=(720, 960), format_name="JPEG")

        pages = preprocessor.process(img_bytes, "invoice.jpg")
        assert len(pages) == 1
        page = pages[0]
        assert page.width == 720
        assert page.height == 960
        assert page.page_number == 1
        assert page.mime_type == "image/png"
        assert len(page.image_bytes) > 0

    def test_auto_deskew_flag_controls_deskew(self):
        # 1. With auto_deskew=True on tilted image
        preprocessor_deskew = DocumentPreprocessor(auto_deskew=True)
        tilted_bytes = _create_test_image_bytes(size=(600, 800), rotation_angle=4.0)
        pages_deskew = preprocessor_deskew.process(tilted_bytes, "tilted.png")
        assert len(pages_deskew) == 1
        assert abs(pages_deskew[0].skew_angle) > 0.0
        assert any("deskew" in t for t in pages_deskew[0].transforms_applied)

        # 2. With auto_deskew=False on the same tilted image
        preprocessor_no_deskew = DocumentPreprocessor(auto_deskew=False)
        pages_no_deskew = preprocessor_no_deskew.process(tilted_bytes, "tilted.png")
        assert len(pages_no_deskew) == 1
        assert pages_no_deskew[0].skew_angle == 0.0
        assert not any("deskew" in t for t in pages_no_deskew[0].transforms_applied)

    def test_dynamic_quality_score_computation(self):
        preprocessor = DocumentPreprocessor()

        # Sharp clear document
        sharp_bytes = _create_test_image_bytes(size=(800, 1000), text_lines=True)
        sharp_pages = preprocessor.process(sharp_bytes, "sharp.png")
        sharp_score = sharp_pages[0].quality_score
        assert 0.0 <= sharp_score <= 1.0
        assert sharp_score > 0.4  # Well above blur threshold

        # Blank/monochrome low-contrast image
        blank_bytes = _create_test_image_bytes(size=(300, 400), text_lines=False)
        blank_pages = preprocessor.process(blank_bytes, "blank.png")
        blank_score = blank_pages[0].quality_score
        assert "LOW_CONTRAST" in blank_pages[0].quality_warnings or "LOW_RESOLUTION" in blank_pages[0].quality_warnings
        # Sharp document should score noticeably higher than a blank low-res image
        assert sharp_score > blank_score


class TestDocumentPreprocessorPDFHandling:
    """Tests P1: Multipage PDF rendering, error handling, and resource safety."""

    def test_renders_multipage_pdf_correctly(self):
        preprocessor = DocumentPreprocessor(target_dpi=150)
        pdf_bytes = _create_test_pdf_bytes(num_pages=3)

        pages = preprocessor.process(pdf_bytes, "multipage.pdf")
        assert len(pages) == 3
        for i, page in enumerate(pages, start=1):
            assert page.page_number == i
            assert page.width > 0
            assert page.height > 0
            assert page.quality_score > 0.0
            # Ensure it is a valid PNG raster image, NOT raw PDF bytes
            assert page.image_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    def test_page_limit_enforced_for_pdf(self):
        preprocessor = DocumentPreprocessor(max_pages=2)
        pdf_bytes = _create_test_pdf_bytes(num_pages=4)

        with pytest.raises(DocumentLimitExceededError, match="exceeding the maximum allowed limit"):
            preprocessor.process(pdf_bytes, "too_many_pages.pdf")


@pytest.mark.asyncio
async def test_async_preprocessing_wrapper():
    preprocessor = DocumentPreprocessor()
    img_bytes = _create_test_image_bytes(size=(500, 700))
    pages = await preprocessor.process_async(img_bytes, "async_invoice.png")
    assert len(pages) == 1
    assert pages[0].width == 500
    assert pages[0].height == 700
