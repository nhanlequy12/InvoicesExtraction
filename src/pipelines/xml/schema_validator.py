from pathlib import Path
from typing import List, Tuple
from lxml import etree
from src.core.config import settings
from src.core.logging import logger


class XMLSchemaValidator:
    """Validates XML documents against Vietnamese e-invoice XSD schemas."""

    def __init__(self, xsd_path: Path = settings.XSD_SCHEMA_PATH):
        self.xsd_path = xsd_path
        self._schema = None
        self._load_schema()

    def _load_schema(self):
        try:
            if self.xsd_path.exists():
                schema_doc = etree.parse(str(self.xsd_path))
                self._schema = etree.XMLSchema(schema_doc)
            else:
                logger.warning(f"XSD schema file not found at {self.xsd_path}")
        except Exception as e:
            logger.error(f"Failed to load XSD schema {self.xsd_path}: {e}")

    def validate(self, xml_bytes: bytes) -> Tuple[bool, List[str]]:
        if not self._schema:
            # Fallback to well-formedness validation if XSD not available
            try:
                etree.fromstring(xml_bytes)
                return True, []
            except etree.XMLSyntaxError as e:
                return False, [f"XML syntax error: {str(e)}"]

        try:
            doc = etree.fromstring(xml_bytes)
            is_valid = self._schema.validate(doc)
            if not is_valid:
                errors = [f"Line {err.line}: {err.message}" for err in self._schema.error_log]
                return False, errors
            return True, []
        except etree.XMLSyntaxError as e:
            return False, [f"Well-formedness error: {str(e)}"]
