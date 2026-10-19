import argparse
from dataclasses import dataclass, field
import io
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

from src.core.logging import logger
from src.pipelines.ai.preprocessing.preprocessor import DocumentPreprocessor, PreprocessedPage, PreprocessingError


@dataclass
class OCRToken:
    """
    Represents an extracted text token with geometric bounding box and confidence score.
    """
    text: str
    box: List[int]  # [x1, y1, x2, y2]
    confidence: float
    page_number: int


@dataclass
class OCRResult:
    """
    Standard container representing page-level OCR extraction result.
    Compatible with layout detector and downstream field extraction.
    """
    full_text: str
    tokens: List[OCRToken]
    page_number: int
    mean_confidence: float


class OCREngine:
    """
    Enterprise OCR Engine abstraction powered by PaddleOCR (PaddleX v3).
    Extracts text tokens with bounding boxes and calculates composite confidence metrics.
    """

    def __init__(self, lang: str = "vi", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(
                lang=self.lang,
                device="gpu" if self.use_gpu else "cpu",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
            )
            logger.info("Initialized PaddleOCR successfully.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to initialize PaddleOCR -> {type(e).__name__}: {e}")
            self._engine = None

    def extract(self, page: Optional[PreprocessedPage], output_dir: Optional[Path] = None) -> OCRResult:
        """
        Executes text detection and recognition on a preprocessed document page.
        Returns OCRResult containing full page text, tokens with bounding boxes, and mean confidence.
        """
        page_num = page.page_number if page else 1
        empty_result = OCRResult(
            full_text="",
            tokens=[],
            page_number=page_num,
            mean_confidence=0.0,
        )

        if not page or not self._engine:
            return empty_result

        try:
            import cv2

            nparr = np.frombuffer(page.image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode the preprocessed image for OCR.")

            raw_results = self._engine.predict(img)
            tokens: List[OCRToken] = []
            full_text_parts: List[str] = []

            if output_dir is not None:
                output_dir.mkdir(parents=True, exist_ok=True)

            for result in raw_results or []:
                if output_dir is not None:
                    try:
                        result.save_to_img(str(output_dir))
                        result.save_to_json(str(output_dir))
                    except Exception as save_err:
                        logger.warning(f"Failed to save OCR debug artifacts to {output_dir}: {save_err}")

                result_data = result.json
                if callable(result_data):
                    result_data = result_data()
                if not isinstance(result_data, dict):
                    continue
                result_data = result_data.get("res", result_data)

                texts = result_data.get("rec_texts", [])
                scores = result_data.get("rec_scores", [])
                boxes = result_data.get("rec_boxes")
                if boxes is None:
                    boxes = result_data.get("rec_polys", [])

                for index, text in enumerate(texts):
                    box = np.asarray(boxes[index]) if index < len(boxes) else np.array([])
                    if box.size == 4:
                        x1, y1, x2, y2 = (int(value) for value in box.reshape(-1))
                    elif box.size:
                        points = box.reshape(-1, 2)
                        x1 = int(np.min(points[:, 0]))
                        y1 = int(np.min(points[:, 1]))
                        x2 = int(np.max(points[:, 0]))
                        y2 = int(np.max(points[:, 1]))
                    else:
                        x1 = y1 = x2 = y2 = 0

                    confidence = float(scores[index]) if index < len(scores) else 0.0
                    tokens.append(OCRToken(
                        text=str(text),
                        box=[x1, y1, x2, y2],
                        confidence=confidence,
                        page_number=page.page_number,
                    ))
                    full_text_parts.append(str(text))

            mean_conf = sum(token.confidence for token in tokens) / len(tokens) if tokens else 0.0
            return OCRResult(
                full_text="\n".join(full_text_parts),
                tokens=tokens,
                page_number=page.page_number,
                mean_confidence=mean_conf,
            )
        except Exception as e:
            logger.error(f"PaddleOCR execution error: {e}")
            return empty_result


def main():
    parser = argparse.ArgumentParser(description="Test Document Preprocessor and OCR Engine on a single image/PDF.")
    parser.add_argument("file_path", type=str, help="Path to input image or PDF file.")
    parser.add_argument("--save", action="store_true", help="Save preprocessed image and OCR outputs to disk.")
    args = parser.parse_args()

    path = Path(args.file_path)
    if not path.exists():
        print(f"Error: File not found at '{path}'")
        return

    file_bytes = path.read_bytes()
    preprocessor = DocumentPreprocessor()
    ocr_engine = OCREngine(lang="vi")

    try:
        print(f"\n[1/3] Processing file: {path.name}...")
        pages = preprocessor.process(file_bytes, path.name)
        print(f"-> Successfully preprocessed {len(pages)} page(s).")

        for page in pages:
            print(f"\n--- Page {page.page_number} ---")
            print(f"  • Dimensions: {page.width}x{page.height}px | DPI: {page.dpi}")
            print(f"  • Quality Score: {page.quality_score}")
            print(f"  • Transforms Applied: {page.transforms_applied}")
            print(f"  • Quality Warnings: {page.quality_warnings}")

            if args.save:
                out_filename = f"preprocessed_{path.stem}_p{page.page_number}.png"
                Path(out_filename).write_bytes(page.image_bytes)
                print(f"  • Saved preprocessed image to: {out_filename}")

            print(f"\n[2/3] Running OCR on Page {page.page_number}...")
            ocr_output_dir = Path("output") if args.save else None
            ocr_result = ocr_engine.extract(page, output_dir=ocr_output_dir)
            print(f"  • Mean Confidence: {ocr_result.mean_confidence:.2f}")
            print(f"  • Extracted Text:\n{'-'*40}\n{ocr_result.full_text}\n{'-'*40}")

    except PreprocessingError as e:
        print(f"\n[Preprocessing Error]: {e}")
    except Exception as e:
        print(f"\n[Unexpected Error]: {e}")


if __name__ == "__main__":
    main()
