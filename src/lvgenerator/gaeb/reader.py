from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Optional

from lxml import etree

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.namespaces import detect_phase_and_version
from lvgenerator.gaeb.text_parser import extract_plain_text, extract_html
from lvgenerator.models.address import Address
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo, Totals
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item, ItemDescription
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo


class GAEBReader:

    def read(self, file_path: str) -> GAEBProject:
        tree = etree.parse(file_path)
        root = tree.getroot()
        phase, version = detect_phase_and_version(root)
        ns_uri = root.tag[1:root.tag.index("}")]
        ns = {"g": ns_uri}

        project = GAEBProject()
        project.phase = phase
        project.gaeb_info = self._parse_gaeb_info(root, ns)
        project.gaeb_info.version = version
        project.prj_info = self._parse_prj_info(root, ns)
        project.award_info = self._parse_award_info(root, ns)
        project.owner = self._parse_owner(root, ns)
        project.boq = self._parse_boq(root, ns)
        return project

    def _text(self, parent: etree._Element, xpath: str, ns: dict) -> str:
        elem = parent.find(xpath, ns)
        if elem is not None and elem.text:
            return elem.text.strip()
        return ""

    def _decimal(self, parent: etree._Element, xpath: str, ns: dict) -> Optional[Decimal]:
        text = self._text(parent, xpath, ns)
        if text:
            try:
                return Decimal(text)
            except InvalidOperation:
                return None
        return None

    def _parse_gaeb_info(self, root: etree._Element, ns: dict) -> GAEBInfo:
        info = GAEBInfo()
        gi = root.find("g:GAEBInfo", ns)
        if gi is None:
            return info
        info.version = self._text(gi, "g:Version", ns) or info.version
        info.vers_date = self._text(gi, "g:VersDate", ns) or info.vers_date
        date_str = self._text(gi, "g:Date", ns)
        if date_str:
            try:
                info.date = date.fromisoformat(date_str)
            except ValueError:
                pass
        time_str = self._text(gi, "g:Time", ns)
        if time_str:
            try:
                info.time = time.fromisoformat(time_str)
            except ValueError:
                pass
        info.prog_system = self._text(gi, "g:ProgSystem", ns) or info.prog_system
        info.prog_name = self._text(gi, "g:ProgName", ns) or info.prog_name
        return info

    def _parse_prj_info(self, root: etree._Element, ns: dict) -> PrjInfo:
        info = PrjInfo()
        pi = root.find("g:PrjInfo", ns)
        if pi is None:
            return info
        info.name = self._text(pi, "g:NamePrj", ns)
        info.label = self._text(pi, "g:LblPrj", ns)
        info.currency = self._text(pi, "g:Cur", ns) or info.currency
        info.currency_label = self._text(pi, "g:CurLbl", ns) or info.currency_label
        return info

    def _parse_award_info(self, root: etree._Element, ns: dict) -> AwardInfo:
        info = AwardInfo()
        ai = root.find("g:Award/g:AwardInfo", ns)
        if ai is None:
            return info
        info.boq_id = self._text(ai, "g:BoQID", ns)
        info.currency = self._text(ai, "g:Cur", ns) or info.currency
        info.currency_label = self._text(ai, "g:CurLbl", ns) or info.currency_label
        return info

    def _parse_owner(self, root: etree._Element, ns: dict) -> Optional[Address]:
        addr_elem = root.find("g:Award/g:OWN/g:Address", ns)
        if addr_elem is None:
            return None
        addr = Address()
        addr.name1 = self._text(addr_elem, "g:Name1", ns)
        addr.name2 = self._text(addr_elem, "g:Name2", ns)
        addr.name3 = self._text(addr_elem, "g:Name3", ns)
        addr.street = self._text(addr_elem, "g:Street", ns)
        addr.pcode = self._text(addr_elem, "g:PCode", ns)
        addr.city = self._text(addr_elem, "g:City", ns)
        return addr

    def _parse_boq(self, root: etree._Element, ns: dict) -> Optional[BoQ]:
        boq_elem = root.find("g:Award/g:BoQ", ns)
        if boq_elem is None:
            return None
        boq = BoQ()
        boq.id = boq_elem.get("ID", "")
        boq.info = self._parse_boq_info(boq_elem, ns)
        body = boq_elem.find("g:BoQBody", ns)
        if body is not None:
            boq.categories = self._parse_categories(body, ns)
        return boq

    def _parse_boq_info(self, boq_elem: etree._Element, ns: dict) -> BoQInfo:
        info = BoQInfo()
        bi = boq_elem.find("g:BoQInfo", ns)
        if bi is None:
            return info
        info.name = self._text(bi, "g:Name", ns)
        info.label = self._text(bi, "g:LblBoQ", ns)
        date_str = self._text(bi, "g:Date", ns)
        if date_str:
            try:
                info.date = date.fromisoformat(date_str)
            except ValueError:
                pass
        info.outline_complete = self._text(bi, "g:OutlCompl", ns) or info.outline_complete

        for bkdn in bi.findall("g:BoQBkdn", ns):
            breakdown = BoQBkdn()
            breakdown.type = self._text(bkdn, "g:Type", ns) or breakdown.type
            length_str = self._text(bkdn, "g:Length", ns)
            if length_str:
                try:
                    breakdown.length = int(length_str)
                except ValueError:
                    pass
            num_str = self._text(bkdn, "g:Num", ns)
            breakdown.numeric = num_str == "Yes"
            info.breakdowns.append(breakdown)

        totals_elem = bi.find("g:Totals", ns)
        if totals_elem is not None:
            info.totals = self._parse_totals(totals_elem, ns)

        return info

    def _parse_totals(self, totals_elem: etree._Element, ns: dict) -> Totals:
        totals = Totals()
        totals.total = self._decimal(totals_elem, "g:Total", ns) or totals.total
        totals.discount_pcnt = self._decimal(totals_elem, "g:DiscountPcnt", ns)
        totals.discount_amt = self._decimal(totals_elem, "g:DiscountAmt", ns)
        totals.total_net = self._decimal(totals_elem, "g:TotalNet", ns)
        totals.vat_amount = self._decimal(totals_elem, "g:VATAmount", ns)
        totals.total_gross = self._decimal(totals_elem, "g:TotalGross", ns)
        return totals

    def _parse_categories(self, body: etree._Element, ns: dict) -> list[BoQCategory]:
        categories = []
        for ctgy_elem in body.findall("g:BoQCtgy", ns):
            categories.append(self._parse_category(ctgy_elem, ns))
        return categories

    def _parse_category(self, ctgy_elem: etree._Element, ns: dict) -> BoQCategory:
        cat = BoQCategory()
        cat.id = ctgy_elem.get("ID", "")
        cat.rno_part = ctgy_elem.get("RNoPart", "")

        lbl = ctgy_elem.find("g:LblTx", ns)
        if lbl is not None:
            cat.label = extract_plain_text(lbl)
            cat.label_html = extract_html(lbl)

        inner_body = ctgy_elem.find("g:BoQBody", ns)
        if inner_body is not None:
            cat.subcategories = self._parse_categories(inner_body, ns)

            itemlist = inner_body.find("g:Itemlist", ns)
            if itemlist is not None:
                for item_elem in itemlist.findall("g:Item", ns):
                    cat.items.append(self._parse_item(item_elem, ns))

        return cat

    def _parse_item(self, item_elem: etree._Element, ns: dict) -> Item:
        item = Item()
        item.id = item_elem.get("ID", "")
        item.rno_part = item_elem.get("RNoPart", "")
        item.qty = self._decimal(item_elem, "g:Qty", ns)
        item.qu = self._text(item_elem, "g:QU", ns)
        item.up = self._decimal(item_elem, "g:UP", ns)
        item.it = self._decimal(item_elem, "g:IT", ns)
        item.vat = self._decimal(item_elem, "g:VAT", ns)
        item.discount_pcnt = self._decimal(item_elem, "g:DiscountPcnt", ns)

        qty_tbd = self._text(item_elem, "g:QtyTBD", ns)
        item.qty_tbd = qty_tbd == "Yes"
        not_appl = self._text(item_elem, "g:NotAppl", ns)
        item.not_appl = not_appl == "Yes"
        not_offered = self._text(item_elem, "g:NotOffered", ns)
        item.not_offered = not_offered == "Yes"
        hour_it = self._text(item_elem, "g:HourIt", ns)
        item.hour_it = hour_it == "Yes"

        for i in range(1, 7):
            val = self._decimal(item_elem, f"g:UPComp{i}", ns)
            if val is not None:
                item.up_components[i] = val

        desc = item_elem.find("g:Description", ns)
        if desc is not None:
            item.description = self._parse_description(desc, ns)

        return item

    def _parse_description(self, desc_elem: etree._Element, ns: dict) -> ItemDescription:
        desc = ItemDescription()

        complete = desc_elem.find("g:CompleteText", ns)
        if complete is not None:
            detail = complete.find("g:DetailTxt/g:Text", ns)
            if detail is not None:
                desc.detail_text = extract_plain_text(detail)
                desc.detail_html = extract_html(detail)

            outline = complete.find("g:OutlineText/g:OutlTxt/g:TextOutlTxt", ns)
            if outline is not None:
                desc.outline_text = extract_plain_text(outline)
                desc.outline_html = extract_html(outline)
        else:
            outline = desc_elem.find("g:OutlineText/g:OutlTxt/g:TextOutlTxt", ns)
            if outline is not None:
                desc.outline_text = extract_plain_text(outline)
                desc.outline_html = extract_html(outline)

        return desc
