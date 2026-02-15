from lxml import etree


def extract_plain_text(element: etree._Element) -> str:
    if element is None:
        return ""
    parts = []
    for p_elem in element.iter():
        if p_elem.tag.endswith("}p") or p_elem.tag == "p":
            text_parts = []
            for child in p_elem.iter():
                if child.text:
                    text_parts.append(child.text)
                if child.tail:
                    text_parts.append(child.tail)
            line = "".join(text_parts).strip()
            if line:
                parts.append(line)
    if not parts:
        text = element.text or ""
        for child in element:
            text += etree.tostring(child, method="text", encoding="unicode") or ""
        return text.strip()
    return "\n".join(parts)


def extract_html(element: etree._Element) -> str:
    if element is None:
        return ""
    return etree.tostring(element, encoding="unicode", method="xml")


def build_text_element(plain_text: str, ns: str, tag: str = "Text") -> etree._Element:
    text_elem = etree.SubElement(etree.Element("_dummy"), f"{{{ns}}}{tag}")
    for line in plain_text.split("\n"):
        p = etree.SubElement(text_elem, f"{{{ns}}}p")
        span = etree.SubElement(p, f"{{{ns}}}span")
        span.text = line
    # Remove from dummy parent
    text_elem.getparent().remove(text_elem)
    return text_elem
