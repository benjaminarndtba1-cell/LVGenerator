"""Tests for GAEB <-> Qt HTML converter."""

from lxml import etree

import pytest

from lvgenerator.gaeb.html_converter import (
    gaeb_html_to_qt_html,
    qt_html_to_gaeb_html,
    _parse_css,
    _gaeb_style_to_qt,
    _qt_style_to_gaeb,
)

NS = "http://www.gaeb.de/GAEB_DA_XML/DA83/3.3"


def _gaeb_text(*paragraphs: str) -> str:
    """Build a GAEB Text element XML string."""
    ns = NS
    parts = [f'<Text xmlns="{ns}">']
    for p in paragraphs:
        parts.append(f"<p><span>{p}</span></p>")
    parts.append("</Text>")
    return "".join(parts)


def _gaeb_styled_text(spans: list[tuple[str, str]]) -> str:
    """Build a GAEB Text element with styled spans."""
    ns = NS
    parts = [f'<Text xmlns="{ns}"><p>']
    for text, style in spans:
        if style:
            parts.append(f'<span style="{style}">{text}</span>')
        else:
            parts.append(f"<span>{text}</span>")
    parts.append("</p></Text>")
    return "".join(parts)


class TestParseCss:
    def test_empty(self):
        assert _parse_css("") == {}

    def test_single_property(self):
        result = _parse_css("font-weight: bold")
        assert result == {"font-weight": "bold"}

    def test_multiple_properties(self):
        result = _parse_css("font-weight: bold; font-size: 10pt; font-family: Arial")
        assert result["font-weight"] == "bold"
        assert result["font-size"] == "10pt"
        assert result["font-family"] == "Arial"


class TestGaebStyleToQt:
    def test_bold(self):
        result = _gaeb_style_to_qt("font-weight: bold")
        assert "700" in result

    def test_font_family_quoted(self):
        result = _gaeb_style_to_qt("font-family: Arial")
        assert "'Arial'" in result

    def test_italic_unchanged(self):
        result = _gaeb_style_to_qt("font-style: italic")
        assert "italic" in result

    def test_font_size_unchanged(self):
        result = _gaeb_style_to_qt("font-size: 8pt")
        assert "8pt" in result


class TestQtStyleToGaeb:
    def test_bold_numeric(self):
        result = _qt_style_to_gaeb("font-weight: 700")
        assert "bold" in result

    def test_normal_weight_omitted(self):
        result = _qt_style_to_gaeb("font-weight: 400")
        assert "font-weight" not in result

    def test_font_family_unquoted(self):
        result = _qt_style_to_gaeb("font-family: 'Arial'")
        assert "Arial" in result
        assert "'" not in result

    def test_margins_stripped(self):
        result = _qt_style_to_gaeb(
            "margin-top: 0px; margin-bottom: 12px; font-weight: 700"
        )
        assert "margin" not in result
        assert "bold" in result

    def test_qt_specific_stripped(self):
        result = _qt_style_to_gaeb("-qt-block-indent: 0; text-indent: 0px")
        assert result == ""


class TestGaebHtmlToQtHtml:
    def test_simple_text(self):
        gaeb = _gaeb_text("Hallo Welt")
        result = gaeb_html_to_qt_html(gaeb)
        assert "<body" in result
        assert "Hallo Welt" in result
        assert "<p>" in result

    def test_multiple_paragraphs(self):
        gaeb = _gaeb_text("Zeile 1", "Zeile 2")
        result = gaeb_html_to_qt_html(gaeb)
        assert "Zeile 1" in result
        assert "Zeile 2" in result
        assert result.count("<p>") == 2

    def test_styled_bold(self):
        gaeb = _gaeb_styled_text([("Fetter Text", "font-weight: bold")])
        result = gaeb_html_to_qt_html(gaeb)
        assert "font-weight" in result
        assert "700" in result
        assert "Fetter Text" in result

    def test_styled_italic(self):
        gaeb = _gaeb_styled_text([("Kursiv", "font-style: italic")])
        result = gaeb_html_to_qt_html(gaeb)
        assert "font-style" in result
        assert "italic" in result

    def test_default_font_applied(self):
        gaeb = _gaeb_text("Text")
        result = gaeb_html_to_qt_html(gaeb, default_font_family="Arial",
                                       default_font_size_pt=8)
        assert "Arial" in result
        assert "8pt" in result

    def test_empty_input(self):
        assert gaeb_html_to_qt_html("") == ""
        assert gaeb_html_to_qt_html(None) == ""

    def test_plain_text_fallback(self):
        # Non-XML input should not crash
        result = gaeb_html_to_qt_html("just plain text")
        assert "just plain text" in result

    def test_no_style_produces_clean_html(self):
        gaeb = _gaeb_text("Einfacher Text")
        result = gaeb_html_to_qt_html(gaeb)
        assert "Einfacher Text" in result
        # No style attribute on the text itself
        assert 'style="font-weight' not in result


class TestQtHtmlToGaebHtml:
    def test_simple_paragraph(self):
        qt_html = '<html><body><p>Hallo Welt</p></body></html>'
        result = qt_html_to_gaeb_html(qt_html, "Text", NS)
        root = etree.fromstring(result)
        assert root.tag == f"{{{NS}}}Text"
        p_elems = list(root.iter(f"{{{NS}}}p"))
        assert len(p_elems) == 1
        span = p_elems[0].find(f"{{{NS}}}span")
        assert span is not None
        assert span.text == "Hallo Welt"

    def test_multiple_paragraphs(self):
        qt_html = '<html><body><p>Zeile 1</p><p>Zeile 2</p></body></html>'
        result = qt_html_to_gaeb_html(qt_html, "Text", NS)
        root = etree.fromstring(result)
        p_elems = list(root.iter(f"{{{NS}}}p"))
        assert len(p_elems) == 2

    def test_bold_span(self):
        qt_html = (
            '<html><body>'
            '<p><span style="font-weight:700;">Fett</span></p>'
            '</body></html>'
        )
        result = qt_html_to_gaeb_html(qt_html, "Text", NS)
        root = etree.fromstring(result)
        span = root.find(f".//{{{NS}}}span")
        assert span is not None
        assert "bold" in span.get("style", "")

    def test_italic_span(self):
        qt_html = (
            '<html><body>'
            '<p><span style="font-style:italic;">Kursiv</span></p>'
            '</body></html>'
        )
        result = qt_html_to_gaeb_html(qt_html, "Text", NS)
        root = etree.fromstring(result)
        span = root.find(f".//{{{NS}}}span")
        assert "italic" in span.get("style", "")

    def test_bullet_list(self):
        qt_html = (
            '<html><body>'
            '<ul><li>Punkt 1</li><li>Punkt 2</li></ul>'
            '</body></html>'
        )
        result = qt_html_to_gaeb_html(qt_html, "Text", NS)
        root = etree.fromstring(result)
        p_elems = list(root.iter(f"{{{NS}}}p"))
        assert len(p_elems) == 2
        span0 = p_elems[0].find(f"{{{NS}}}span")
        assert span0.text.startswith("\u2022")
        assert "Punkt 1" in span0.text

    def test_different_parent_tag(self):
        qt_html = '<html><body><p>Text</p></body></html>'
        result = qt_html_to_gaeb_html(qt_html, "TextOutlTxt", NS)
        root = etree.fromstring(result)
        assert root.tag == f"{{{NS}}}TextOutlTxt"

    def test_empty_input(self):
        assert qt_html_to_gaeb_html("", "Text", NS) == ""

    def test_margins_not_in_output(self):
        qt_html = (
            '<html><body>'
            '<p style="margin-top:0px; margin-bottom:12px;">'
            '<span style="font-weight:700;">Text</span></p>'
            '</body></html>'
        )
        result = qt_html_to_gaeb_html(qt_html, "Text", NS)
        assert "margin" not in result

    def test_different_namespace(self):
        ns_32 = "http://www.gaeb.de/GAEB_DA_XML/DA81/3.2"
        qt_html = '<html><body><p>Text</p></body></html>'
        result = qt_html_to_gaeb_html(qt_html, "Text", ns_32)
        root = etree.fromstring(result)
        assert ns_32 in root.tag


class TestRoundTrip:
    """Test that GAEB -> Qt -> GAEB produces equivalent XML."""

    def test_plain_text_roundtrip(self):
        gaeb_orig = _gaeb_text("Boden loesen und seitlich lagern.")
        qt_html = gaeb_html_to_qt_html(gaeb_orig)
        gaeb_result = qt_html_to_gaeb_html(qt_html, "Text", NS)

        # Parse both and compare text content
        orig_root = etree.fromstring(gaeb_orig)
        result_root = etree.fromstring(gaeb_result)

        orig_text = etree.tostring(orig_root, method="text", encoding="unicode")
        result_text = etree.tostring(result_root, method="text", encoding="unicode")
        assert orig_text.strip() == result_text.strip()

    def test_multi_paragraph_roundtrip(self):
        gaeb_orig = _gaeb_text("Absatz 1", "Absatz 2", "Absatz 3")
        qt_html = gaeb_html_to_qt_html(gaeb_orig)
        gaeb_result = qt_html_to_gaeb_html(qt_html, "Text", NS)

        orig_root = etree.fromstring(gaeb_orig)
        result_root = etree.fromstring(gaeb_result)

        orig_ps = list(orig_root.iter(f"{{{NS}}}p"))
        result_ps = list(result_root.iter(f"{{{NS}}}p"))
        assert len(orig_ps) == len(result_ps)

    def test_styled_text_roundtrip(self):
        gaeb_orig = _gaeb_styled_text([
            ("Fetter Text", "font-weight: bold"),
        ])
        qt_html = gaeb_html_to_qt_html(gaeb_orig)
        gaeb_result = qt_html_to_gaeb_html(qt_html, "Text", NS)

        result_root = etree.fromstring(gaeb_result)
        span = result_root.find(f".//{{{NS}}}span")
        assert span is not None
        assert "bold" in span.get("style", "")
        assert "Fetter Text" in span.text

    def test_mixed_style_roundtrip(self):
        gaeb_orig = _gaeb_styled_text([
            ("Normal", ""),
            ("Fett", "font-weight: bold"),
            ("Kursiv", "font-style: italic"),
        ])
        qt_html = gaeb_html_to_qt_html(gaeb_orig)
        gaeb_result = qt_html_to_gaeb_html(qt_html, "Text", NS)

        result_root = etree.fromstring(gaeb_result)
        text = etree.tostring(result_root, method="text", encoding="unicode")
        assert "Normal" in text
        assert "Fett" in text
        assert "Kursiv" in text
