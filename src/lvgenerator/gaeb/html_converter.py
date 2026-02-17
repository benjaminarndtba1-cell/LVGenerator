"""Bidirectional HTML conversion between GAEB XML text format and QTextEdit HTML."""

import re
from typing import Optional

from lxml import etree


def _parse_css(style_str: str) -> dict[str, str]:
    """Parse a CSS style string into a dict."""
    result = {}
    if not style_str:
        return result
    for part in style_str.split(";"):
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            result[key.strip().lower()] = val.strip()
    return result


def _build_css(props: dict[str, str]) -> str:
    """Build a CSS style string from a dict."""
    return "; ".join(f"{k}: {v}" for k, v in props.items() if v)


def _gaeb_style_to_qt(style_str: str) -> str:
    """Map GAEB CSS properties to Qt-compatible CSS."""
    props = _parse_css(style_str)
    qt_props = {}
    for key, val in props.items():
        if key == "font-weight" and val == "bold":
            qt_props["font-weight"] = "700"
        elif key == "font-family":
            # Qt quotes font names
            qt_props["font-family"] = f"'{val.strip(chr(39))}'"
        else:
            qt_props[key] = val
    return _build_css(qt_props)


def _qt_style_to_gaeb(style_str: str) -> str:
    """Map Qt CSS properties back to GAEB-compatible CSS."""
    props = _parse_css(style_str)
    gaeb_props = {}

    # Filter out Qt-specific layout properties
    skip_keys = {
        "margin-top", "margin-bottom", "margin-left", "margin-right",
        "-qt-block-indent", "text-indent", "-qt-list-indent",
        "-qt-paragraph-type",
    }

    for key, val in props.items():
        if key in skip_keys:
            continue
        if key == "font-weight":
            # Qt uses numeric weights: 700=bold, 400=normal
            try:
                weight = int(val)
                if weight >= 700:
                    gaeb_props["font-weight"] = "bold"
                # Normal weight (400) is omitted
            except ValueError:
                gaeb_props["font-weight"] = val
        elif key == "font-family":
            # Remove quotes
            gaeb_props["font-family"] = val.strip("'\"")
        else:
            gaeb_props[key] = val
    return _build_css(gaeb_props)


def _strip_ns(tag: str) -> str:
    """Remove XML namespace from a tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def gaeb_html_to_qt_html(
    gaeb_html: str,
    default_font_family: str = "",
    default_font_size_pt: int = 0,
) -> str:
    """Convert GAEB XML text (from extract_html()) to QTextEdit-compatible HTML.

    Args:
        gaeb_html: Raw XML string from extract_html(), e.g.
            '<ns:Text xmlns:ns="..."><ns:p><ns:span>text</ns:span></ns:p></ns:Text>'
        default_font_family: Default font family to apply
        default_font_size_pt: Default font size in pt
    Returns:
        HTML string suitable for QTextEdit.setHtml()
    """
    if not gaeb_html or not gaeb_html.strip():
        return ""

    try:
        root = etree.fromstring(gaeb_html.encode("utf-8") if isinstance(gaeb_html, str) else gaeb_html)
    except etree.XMLSyntaxError:
        # Fallback: return as plain text
        return f"<html><body><p>{_escape_html(gaeb_html)}</p></body></html>"

    paragraphs = []
    # Find all <p> elements (any namespace)
    for elem in root.iter():
        if _strip_ns(elem.tag) == "p":
            p_html = _convert_gaeb_p_to_qt(elem)
            paragraphs.append(p_html)

    if not paragraphs:
        # No <p> elements found - extract text directly
        text = etree.tostring(root, method="text", encoding="unicode") or ""
        if text.strip():
            paragraphs.append(f"<p>{_escape_html(text.strip())}</p>")

    body_style = ""
    style_parts = []
    if default_font_family:
        style_parts.append(f"font-family:'{default_font_family}'")
    if default_font_size_pt:
        style_parts.append(f"font-size:{default_font_size_pt}pt")
    if style_parts:
        body_style = f' style="{"; ".join(style_parts)}"'

    body_content = "\n".join(paragraphs)
    return f"<html><body{body_style}>\n{body_content}\n</body></html>"


def _convert_gaeb_p_to_qt(p_elem) -> str:
    """Convert a GAEB <p> element to Qt HTML <p>."""
    spans = []
    for child in p_elem:
        local_tag = _strip_ns(child.tag)
        if local_tag == "span":
            style = child.get("style", "")
            text = child.text or ""
            if style:
                qt_style = _gaeb_style_to_qt(style)
                spans.append(f'<span style="{qt_style}">{_escape_html(text)}</span>')
            else:
                spans.append(_escape_html(text))
            # Handle tail text (text after closing tag)
            if child.tail:
                spans.append(_escape_html(child.tail))
        else:
            # Unknown child - extract text
            text = etree.tostring(child, method="text", encoding="unicode") or ""
            if text:
                spans.append(_escape_html(text))
            if child.tail:
                spans.append(_escape_html(child.tail))

    # If <p> has direct text (no children)
    if not list(p_elem) and p_elem.text:
        spans.append(_escape_html(p_elem.text))

    return f"<p>{''.join(spans)}</p>"


def qt_html_to_gaeb_html(qt_html: str, parent_tag: str, ns: str) -> str:
    """Convert QTextEdit toHtml() output to GAEB XML text string.

    Args:
        qt_html: HTML string from QTextEdit.toHtml()
        parent_tag: The GAEB parent tag name (e.g. "Text", "TextOutlTxt")
        ns: The GAEB XML namespace URI
    Returns:
        XML string suitable for _write_raw_html(), e.g.
            '<ns:Text xmlns:ns="..."><ns:p><ns:span>text</ns:span></ns:p></ns:Text>'
    """
    if not qt_html or not qt_html.strip():
        return ""

    # Build the GAEB parent element
    parent = etree.Element(f"{{{ns}}}{parent_tag}")

    # Parse the Qt HTML to extract body content
    # Use a simple approach: find content between <body...> and </body>
    body_content = _extract_body_content(qt_html)
    if not body_content:
        return ""

    # Parse the body content as HTML fragments
    # Wrap in a div so lxml can parse it
    try:
        from lxml import html as lxml_html
        fragment = lxml_html.fragment_fromstring(
            body_content, create_parent="div"
        )
    except Exception:
        # Fallback: create simple text element
        p = etree.SubElement(parent, f"{{{ns}}}p")
        span = etree.SubElement(p, f"{{{ns}}}span")
        span.text = _strip_html_tags(body_content)
        return etree.tostring(parent, encoding="unicode")

    for child in fragment:
        tag = child.tag if isinstance(child.tag, str) else ""
        if tag == "p":
            _convert_qt_p_to_gaeb(child, parent, ns)
        elif tag == "ul":
            # Bullet list -> convert each <li> to <p> with bullet prefix
            for li in child:
                if (li.tag if isinstance(li.tag, str) else "") == "li":
                    _convert_qt_li_to_gaeb(li, parent, ns)
        elif tag == "ol":
            # Ordered list -> convert each <li> to <p> with number prefix
            for idx, li in enumerate(child, 1):
                if (li.tag if isinstance(li.tag, str) else "") == "li":
                    _convert_qt_li_to_gaeb(li, parent, ns, prefix=f"{idx}. ")

    # Handle case where fragment has text but no <p> elements
    if len(parent) == 0:
        text = fragment.text_content().strip() if hasattr(fragment, 'text_content') else ""
        if text:
            p = etree.SubElement(parent, f"{{{ns}}}p")
            span = etree.SubElement(p, f"{{{ns}}}span")
            span.text = text

    return etree.tostring(parent, encoding="unicode")


def _convert_qt_p_to_gaeb(p_elem, parent, ns: str) -> None:
    """Convert a Qt HTML <p> element to GAEB <p><span> structure."""
    gaeb_p = etree.SubElement(parent, f"{{{ns}}}p")

    # Check if the <p> has <span> children with styles
    has_children = False
    for child in p_elem:
        tag = child.tag if isinstance(child.tag, str) else ""
        if tag == "span":
            has_children = True
            style = child.get("style", "")
            gaeb_style = _qt_style_to_gaeb(style) if style else ""
            span = etree.SubElement(gaeb_p, f"{{{ns}}}span")
            text = _get_element_text(child)
            span.text = text
            if gaeb_style:
                span.set("style", gaeb_style)
            # Handle tail
            if child.tail and child.tail.strip():
                tail_span = etree.SubElement(gaeb_p, f"{{{ns}}}span")
                tail_span.text = child.tail
        elif tag in ("br",):
            continue  # Skip <br> elements
        else:
            # Other elements (strong, em, etc.) - extract formatted
            has_children = True
            _convert_inline_element(child, gaeb_p, ns)

    # Direct text in <p> without spans
    if p_elem.text and p_elem.text.strip():
        span = etree.SubElement(gaeb_p, f"{{{ns}}}span")
        span.text = p_elem.text
        # Insert as first child
        if len(gaeb_p) > 1:
            gaeb_p.insert(0, span)

    # If empty <p> after conversion, add empty span
    if len(gaeb_p) == 0:
        span = etree.SubElement(gaeb_p, f"{{{ns}}}span")
        span.text = p_elem.text or ""


def _convert_inline_element(elem, gaeb_p, ns: str) -> None:
    """Convert inline HTML elements (strong, em, etc.) to GAEB spans with style."""
    tag = elem.tag if isinstance(elem.tag, str) else ""
    style_parts = []

    if tag == "strong" or tag == "b":
        style_parts.append("font-weight: bold")
    elif tag == "em" or tag == "i":
        style_parts.append("font-style: italic")
    elif tag == "u":
        style_parts.append("text-decoration: underline")

    span = etree.SubElement(gaeb_p, f"{{{ns}}}span")
    span.text = _get_element_text(elem)
    if style_parts:
        span.set("style", "; ".join(style_parts))

    if elem.tail and elem.tail.strip():
        tail_span = etree.SubElement(gaeb_p, f"{{{ns}}}span")
        tail_span.text = elem.tail


def _convert_qt_li_to_gaeb(li_elem, parent, ns: str, prefix: str = "\u2022 ") -> None:
    """Convert a Qt HTML <li> element to GAEB <p> with bullet prefix."""
    gaeb_p = etree.SubElement(parent, f"{{{ns}}}p")
    text = _get_element_text(li_elem)
    span = etree.SubElement(gaeb_p, f"{{{ns}}}span")
    span.text = prefix + text


def _get_element_text(elem) -> str:
    """Get all text content from an element including children."""
    if hasattr(elem, 'text_content'):
        return elem.text_content()
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.append(_get_element_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _extract_body_content(html: str) -> str:
    """Extract content between <body...> and </body>."""
    # Find body content
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    if body_match:
        return body_match.group(1).strip()

    # No body tag - try to use the whole thing
    # Strip html/head tags if present
    html = re.sub(r"</?html[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<head>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)
    return html.strip()


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text)
