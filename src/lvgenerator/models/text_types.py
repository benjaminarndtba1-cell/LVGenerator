from dataclasses import dataclass


@dataclass
class AddText:
    outline_text: str = ""
    outline_html: str = ""
    detail_text: str = ""
    detail_html: str = ""
