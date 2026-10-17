from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from src.core.logging import logger


@dataclass
class ActiveLearningSample:
    document_id: str
    original_ai_prediction: Dict[str, Any]
    human_ground_truth: Dict[str, Any]
    correction_diff: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


class ActiveLearningCollector:
    """
    Active Learning Sample Collector.
    Collects discrepancies between AI extraction predictions and verified
    human ground truth for fine-tuning LayoutLM and OCR recognition models.
    """

    def __init__(self):
        self._samples: List[ActiveLearningSample] = []

    def collect(
        self,
        document_id: str,
        ai_prediction: Dict[str, Any],
        ground_truth: Dict[str, Any]
    ) -> ActiveLearningSample:
        diff = {}
        for k, v in ground_truth.items():
            if ai_prediction.get(k) != v:
                diff[k] = {"ai": ai_prediction.get(k), "human": v}

        sample = ActiveLearningSample(
            document_id=document_id,
            original_ai_prediction=ai_prediction,
            human_ground_truth=ground_truth,
            correction_diff=diff
        )
        self._samples.append(sample)
        logger.info(f"Collected active learning sample for doc {document_id} with {len(diff)} corrections.")
        return sample

    def get_dataset_size(self) -> int:
        return len(self._samples)
