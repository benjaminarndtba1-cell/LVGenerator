from dataclasses import dataclass


@dataclass
class Address:
    name1: str = ""
    name2: str = ""
    name3: str = ""
    street: str = ""
    pcode: str = ""
    city: str = ""
