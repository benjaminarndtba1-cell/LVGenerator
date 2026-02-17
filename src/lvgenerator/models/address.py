from dataclasses import dataclass


@dataclass
class Address:
    name1: str = ""
    name2: str = ""
    name3: str = ""
    name4: str = ""
    street: str = ""
    pcode: str = ""
    city: str = ""
    country: str = ""
    contact: str = ""
    phone: str = ""
    fax: str = ""
    email: str = ""


@dataclass
class Contractor:
    """CTR (Contractor/Bidder) element."""
    address: Address = None
    dp_no: str = ""
    award_no: str = ""
    accts_pay_no: str = ""
    has_dp_no: bool = False
    has_award_no: bool = False
    has_accts_pay_no: bool = False
