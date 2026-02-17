"""XSD-Validierung fuer GAEB DA XML Dateien."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lxml import etree

from lvgenerator.constants import GAEBPhase


@dataclass
class XSDValidationError:
    """Einzelner XSD-Validierungsfehler."""
    line: int
    message: str


@dataclass
class XSDValidationResult:
    """Ergebnis einer XSD-Validierung."""
    is_valid: bool = True
    errors: list[XSDValidationError] = field(default_factory=list)
    phase: Optional[GAEBPhase] = None
    version: str = ""


# Map of (dp_value, version) to XSD filename
_XSD_FILES = {
    (80, "3.3"): "GAEB_DA_XML_80_3.3_2021-05.xsd",
    (81, "3.3"): "GAEB_DA_XML_81_3.3_2021-05.xsd",
    (82, "3.3"): "GAEB_DA_XML_82_3.3_2021-05.xsd",
    (83, "3.3"): "GAEB_DA_XML_83_3.3_2021-05.xsd",
    (84, "3.3"): "GAEB_DA_XML_84_3.3_2021-05.xsd",
    (85, "3.3"): "GAEB_DA_XML_85_3.3_2021-05.xsd",
    (86, "3.3"): "GAEB_DA_XML_86_3.3_2021-05.xsd",
    (87, "3.3"): "GAEB_DA_XML_87_3.3_2021-05.xsd",
}


def _get_xsd_dir() -> Path:
    """Locate the XSD schema directory."""
    # Try relative to this module (development layout)
    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir.parent.parent.parent / "docs" / "certification" / "xsd",
        module_dir.parent / "resources" / "xsd",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "XSD schema directory not found. Expected at docs/certification/xsd/"
    )


def get_xsd_path(phase: GAEBPhase, version: str = "3.3") -> Optional[Path]:
    """Get the path to the XSD schema file for a given phase and version."""
    key = (phase.dp_value, version)
    filename = _XSD_FILES.get(key)
    if filename is None:
        return None
    xsd_dir = _get_xsd_dir()
    xsd_path = xsd_dir / filename
    if xsd_path.is_file():
        return xsd_path
    return None


def validate_file(file_path: str) -> XSDValidationResult:
    """Validate a GAEB DA XML file against its XSD schema.

    Detects phase and version from the XML namespace automatically.
    """
    result = XSDValidationResult()

    try:
        xml_doc = etree.parse(file_path)
    except etree.XMLSyntaxError as e:
        result.is_valid = False
        result.errors.append(XSDValidationError(line=0, message=f"XML Syntax: {e}"))
        return result

    root = xml_doc.getroot()
    tag = root.tag
    if not tag.startswith("{"):
        result.is_valid = False
        result.errors.append(XSDValidationError(
            line=0, message="Root-Element hat keinen Namespace"
        ))
        return result

    ns_uri = tag[1:tag.index("}")]

    # Extract phase and version from namespace
    import re
    match = re.match(r"http://www\.gaeb\.de/GAEB_DA_XML/DA(\d{2})/([\d.]+)", ns_uri)
    if not match:
        result.is_valid = False
        result.errors.append(XSDValidationError(
            line=0, message=f"Unbekannter GAEB Namespace: {ns_uri}"
        ))
        return result

    dp_value = int(match.group(1))
    version = match.group(2)

    try:
        phase = GAEBPhase.from_dp(dp_value)
    except ValueError:
        result.is_valid = False
        result.errors.append(XSDValidationError(
            line=0, message=f"Unbekannte GAEB Phase: DA{dp_value}"
        ))
        return result

    result.phase = phase
    result.version = version

    xsd_path = get_xsd_path(phase, version)
    if xsd_path is None:
        result.is_valid = False
        result.errors.append(XSDValidationError(
            line=0,
            message=f"Kein XSD-Schema fuer {phase.name} Version {version} verfuegbar"
        ))
        return result

    try:
        xsd_doc = etree.parse(str(xsd_path))
        schema = etree.XMLSchema(xsd_doc)
    except Exception as e:
        result.is_valid = False
        result.errors.append(XSDValidationError(
            line=0, message=f"XSD-Schema konnte nicht geladen werden: {e}"
        ))
        return result

    is_valid = schema.validate(xml_doc)
    result.is_valid = is_valid

    if not is_valid:
        for error in schema.error_log:
            result.errors.append(XSDValidationError(
                line=error.line,
                message=error.message,
            ))

    return result


def validate_xml_string(xml_content: bytes) -> XSDValidationResult:
    """Validate GAEB XML content from bytes against its XSD schema."""
    result = XSDValidationResult()

    try:
        xml_doc = etree.fromstring(xml_content)
    except etree.XMLSyntaxError as e:
        result.is_valid = False
        result.errors.append(XSDValidationError(line=0, message=f"XML Syntax: {e}"))
        return result

    # Write to temp to reuse validate_file logic
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp.write(xml_content)
        tmp_path = tmp.name

    try:
        return validate_file(tmp_path)
    finally:
        os.unlink(tmp_path)
