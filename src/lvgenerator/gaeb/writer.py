import uuid
from datetime import date, time

from lxml import etree

from lvgenerator.constants import GAEBPhase, GAEB_DEFAULT_VERSION
from lvgenerator.gaeb.namespaces import get_namespace
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.gaeb.text_parser import build_text_element
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo, Totals
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item
from lvgenerator.models.project import GAEBProject


class GAEBWriter:

    def write(self, project: GAEBProject, file_path: str,
              version: str = GAEB_DEFAULT_VERSION) -> None:
        ns_uri = get_namespace(project.phase, version)
        nsmap = {None: ns_uri}

        root = etree.Element(f"{{{ns_uri}}}GAEB", nsmap=nsmap)
        self._write_gaeb_info(root, project.gaeb_info, ns_uri)
        self._write_prj_info(root, project.prj_info, ns_uri)
        self._write_award(root, project, ns_uri)

        tree = etree.ElementTree(root)
        tree.write(
            file_path,
            xml_declaration=True,
            encoding="utf-8",
            pretty_print=True,
        )

    def _sub(self, parent: etree._Element, tag: str, ns: str,
             text: str = None) -> etree._Element:
        elem = etree.SubElement(parent, f"{{{ns}}}{tag}")
        if text is not None:
            elem.text = str(text)
        return elem

    def _write_gaeb_info(self, root: etree._Element, info, ns: str) -> None:
        gi = self._sub(root, "GAEBInfo", ns)
        self._sub(gi, "Version", ns, info.version)
        self._sub(gi, "VersDate", ns, info.vers_date)
        if info.date:
            self._sub(gi, "Date", ns, info.date.isoformat())
        else:
            self._sub(gi, "Date", ns, date.today().isoformat())
        if info.time:
            self._sub(gi, "Time", ns, info.time.isoformat())
        self._sub(gi, "ProgSystem", ns, info.prog_system)
        self._sub(gi, "ProgName", ns, info.prog_name)

    def _write_prj_info(self, root: etree._Element, info, ns: str) -> None:
        pi = self._sub(root, "PrjInfo", ns)
        if info.name:
            self._sub(pi, "NamePrj", ns, info.name)
        if info.label:
            self._sub(pi, "LblPrj", ns, info.label)
        self._sub(pi, "Cur", ns, info.currency)
        self._sub(pi, "CurLbl", ns, info.currency_label)

    def _write_award(self, root: etree._Element, project: GAEBProject, ns: str) -> None:
        award = self._sub(root, "Award", ns)
        self._sub(award, "DP", ns, str(project.phase.dp_value))

        ai = self._sub(award, "AwardInfo", ns)
        boq_id = project.award_info.boq_id or str(uuid.uuid4())
        self._sub(ai, "BoQID", ns, boq_id)
        self._sub(ai, "Cur", ns, project.award_info.currency)
        self._sub(ai, "CurLbl", ns, project.award_info.currency_label)

        if project.owner:
            own = self._sub(award, "OWN", ns)
            addr = self._sub(own, "Address", ns)
            if project.owner.name1:
                self._sub(addr, "Name1", ns, project.owner.name1)
            if project.owner.name2:
                self._sub(addr, "Name2", ns, project.owner.name2)
            if project.owner.name3:
                self._sub(addr, "Name3", ns, project.owner.name3)
            if project.owner.street:
                self._sub(addr, "Street", ns, project.owner.street)
            if project.owner.pcode:
                self._sub(addr, "PCode", ns, project.owner.pcode)
            if project.owner.city:
                self._sub(addr, "City", ns, project.owner.city)

        if project.boq:
            self._write_boq(award, project.boq, project.phase, ns)

    def _write_boq(self, parent: etree._Element, boq: BoQ,
                   phase: GAEBPhase, ns: str) -> None:
        boq_id = boq.id or str(uuid.uuid4())
        boq_elem = self._sub(parent, "BoQ", ns)
        boq_elem.set("ID", boq_id)

        self._write_boq_info(boq_elem, boq.info, phase, ns)

        if boq.categories:
            body = self._sub(boq_elem, "BoQBody", ns)
            for cat in boq.categories:
                self._write_category(body, cat, phase, ns)

    def _write_boq_info(self, parent: etree._Element, info: BoQInfo,
                        phase: GAEBPhase, ns: str) -> None:
        bi = self._sub(parent, "BoQInfo", ns)
        if info.name:
            self._sub(bi, "Name", ns, info.name)
        if info.label:
            self._sub(bi, "LblBoQ", ns, info.label)
        if info.date:
            self._sub(bi, "Date", ns, info.date.isoformat())
        self._sub(bi, "OutlCompl", ns, info.outline_complete)

        for bkdn in info.breakdowns:
            self._write_breakdown(bi, bkdn, ns)

        rules = get_rules(phase)
        if rules.has_totals and info.totals:
            self._write_totals(bi, info.totals, ns)

    def _write_breakdown(self, parent: etree._Element, bkdn: BoQBkdn, ns: str) -> None:
        b = self._sub(parent, "BoQBkdn", ns)
        self._sub(b, "Type", ns, bkdn.type)
        self._sub(b, "Length", ns, str(bkdn.length))
        self._sub(b, "Num", ns, "Yes" if bkdn.numeric else "No")

    def _write_totals(self, parent: etree._Element, totals: Totals, ns: str) -> None:
        t = self._sub(parent, "Totals", ns)
        self._sub(t, "Total", ns, str(totals.total))
        if totals.discount_pcnt is not None:
            self._sub(t, "DiscountPcnt", ns, str(totals.discount_pcnt))
        if totals.discount_amt is not None:
            self._sub(t, "DiscountAmt", ns, str(totals.discount_amt))
        if totals.total_net is not None:
            self._sub(t, "TotalNet", ns, str(totals.total_net))
        if totals.vat_amount is not None:
            self._sub(t, "VATAmount", ns, str(totals.vat_amount))
        if totals.total_gross is not None:
            self._sub(t, "TotalGross", ns, str(totals.total_gross))

    def _write_category(self, parent: etree._Element, cat: BoQCategory,
                        phase: GAEBPhase, ns: str) -> None:
        ctgy = self._sub(parent, "BoQCtgy", ns)
        if cat.id:
            ctgy.set("ID", cat.id)
        if cat.rno_part:
            ctgy.set("RNoPart", cat.rno_part)

        if cat.label:
            lbl = self._sub(ctgy, "LblTx", ns)
            p = etree.SubElement(lbl, f"{{{ns}}}p")
            span = etree.SubElement(p, f"{{{ns}}}span")
            span.text = cat.label

        if cat.subcategories or cat.items:
            body = self._sub(ctgy, "BoQBody", ns)
            for subcat in cat.subcategories:
                self._write_category(body, subcat, phase, ns)
            if cat.items:
                itemlist = self._sub(body, "Itemlist", ns)
                for item in cat.items:
                    self._write_item(itemlist, item, phase, ns)

    def _write_item(self, parent: etree._Element, item: Item,
                    phase: GAEBPhase, ns: str) -> None:
        rules = get_rules(phase)
        item_elem = self._sub(parent, "Item", ns)
        item_id = item.id or str(uuid.uuid4())
        item_elem.set("ID", item_id)
        if item.rno_part:
            item_elem.set("RNoPart", item.rno_part)

        effective_qty = item.get_effective_qty()
        if rules.has_quantities and effective_qty is not None:
            self._sub(item_elem, "Qty", ns, str(effective_qty))
        if item.qty_tbd:
            self._sub(item_elem, "QtyTBD", ns, "Yes")
        if item.qu:
            self._sub(item_elem, "QU", ns, item.qu)

        if rules.has_prices:
            if item.up is not None:
                self._sub(item_elem, "UP", ns, str(item.up))
            for i in range(1, 7):
                if i in item.up_components:
                    self._sub(item_elem, f"UPComp{i}", ns, str(item.up_components[i]))
            if item.discount_pcnt is not None:
                self._sub(item_elem, "DiscountPcnt", ns, str(item.discount_pcnt))

        if rules.has_totals and item.it is not None:
            self._sub(item_elem, "IT", ns, str(item.it))

        if item.vat is not None:
            self._sub(item_elem, "VAT", ns, str(item.vat))
        if item.not_appl:
            self._sub(item_elem, "NotAppl", ns, "Yes")
        if rules.allows_not_offered and item.not_offered:
            self._sub(item_elem, "NotOffered", ns, "Yes")
        if item.hour_it:
            self._sub(item_elem, "HourIt", ns, "Yes")

        self._write_description(item_elem, item.description, ns)

    def _write_description(self, parent: etree._Element, desc, ns: str) -> None:
        if not desc.outline_text and not desc.detail_text:
            return

        description = self._sub(parent, "Description", ns)

        if desc.detail_text or desc.outline_text:
            complete = self._sub(description, "CompleteText", ns)

            if desc.detail_text:
                detail_txt = self._sub(complete, "DetailTxt", ns)
                text_elem = self._sub(detail_txt, "Text", ns)
                for line in desc.detail_text.split("\n"):
                    p = etree.SubElement(text_elem, f"{{{ns}}}p")
                    span = etree.SubElement(p, f"{{{ns}}}span")
                    span.text = line

            if desc.outline_text:
                outline = self._sub(complete, "OutlineText", ns)
                outl_txt = self._sub(outline, "OutlTxt", ns)
                text_outl = self._sub(outl_txt, "TextOutlTxt", ns)
                for line in desc.outline_text.split("\n"):
                    p = etree.SubElement(text_outl, f"{{{ns}}}p")
                    span = etree.SubElement(p, f"{{{ns}}}span")
                    span.text = line
