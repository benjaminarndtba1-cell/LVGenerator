from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Optional

from lxml import etree

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.namespaces import detect_phase_and_version
from lvgenerator.gaeb.text_parser import extract_plain_text, extract_html
from lvgenerator.models.address import Address
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo, Catalog, Totals
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import (
    CtlgAssignment, Item, ItemDescription, SubDescription,
)
from lvgenerator.models.project import AwardInfo, GAEBInfo, GAEBProject, PrjInfo
from lvgenerator.models.text_types import AddText


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

        # Award-level AddTexts
        award = root.find("g:Award", ns)
        if award is not None:
            project.award_add_texts = self._parse_add_texts(award, ns)
            # AwardNo
            own = award.find("g:OWN", ns)
            if own is not None:
                award_no = self._text(own, "g:AwardNo", ns)
                if award_no:
                    project.award_info.award_no = award_no

        # GAEB-level AddTexts (Schlussbemerkungen)
        project.gaeb_add_texts = self._parse_add_texts(root, ns)

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
        bcp = self._text(pi, "g:BidCommPerm", ns)
        info.bid_comm_perm = bcp == "Yes"
        return info

    def _parse_award_info(self, root: etree._Element, ns: dict) -> AwardInfo:
        info = AwardInfo()
        ai = root.find("g:Award/g:AwardInfo", ns)
        if ai is None:
            return info
        info.boq_id = self._text(ai, "g:BoQID", ns)
        info.currency = self._text(ai, "g:Cur", ns) or info.currency
        info.currency_label = self._text(ai, "g:CurLbl", ns) or info.currency_label
        info.cat = self._text(ai, "g:Cat", ns)
        info.open_date = self._text(ai, "g:OpenDate", ns)
        info.open_time = self._text(ai, "g:OpenTime", ns)
        info.eval_end = self._text(ai, "g:EvalEnd", ns)
        info.subm_loc = self._text(ai, "g:SubmLoc", ns)
        info.cnst_start = self._text(ai, "g:CnstStart", ns)
        info.cnst_end = self._text(ai, "g:CnstEnd", ns)
        info.contr_no = self._text(ai, "g:ContrNo", ns)
        info.contr_date = self._text(ai, "g:ContrDate", ns)
        info.accept_type = self._text(ai, "g:AcceptType", ns)
        info.warr_dur = self._text(ai, "g:WarrDur", ns)
        info.warr_unit = self._text(ai, "g:WarrUnit", ns)
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
            breakdown.label = self._text(bkdn, "g:LblBoQBkdn", ns)
            length_str = self._text(bkdn, "g:Length", ns)
            if length_str:
                try:
                    breakdown.length = int(length_str)
                except ValueError:
                    pass
            num_str = self._text(bkdn, "g:Num", ns)
            breakdown.numeric = num_str == "Yes"
            alignment = self._text(bkdn, "g:Alignment", ns)
            if alignment in ("left", "right"):
                breakdown.alignment = alignment
            info.breakdowns.append(breakdown)

        # Kataloge
        for ctlg_elem in bi.findall("g:Ctlg", ns):
            cat = Catalog()
            cat.ctlg_id = self._text(ctlg_elem, "g:CtlgID", ns)
            cat.ctlg_name = self._text(ctlg_elem, "g:CtlgName", ns)
            info.catalogs.append(cat)

        totals_elem = bi.find("g:Totals", ns)
        if totals_elem is not None:
            info.totals = self._parse_totals(totals_elem, ns)

        info.add_texts = self._parse_add_texts(bi, ns)

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

        # Grund-/Wahlgruppen auf Kategorieebene
        cat.aln_b_group_no = self._text(ctgy_elem, "g:ALNBGroupNo", ns)
        cat.aln_b_ser_no = self._text(ctgy_elem, "g:ALNBSerNo", ns)

        exec_descr = ctgy_elem.find("g:ExecDescr/g:Text", ns)
        if exec_descr is not None:
            cat.exec_descr = extract_plain_text(exec_descr)
            cat.exec_descr_html = extract_html(exec_descr)

        inner_body = ctgy_elem.find("g:BoQBody", ns)
        if inner_body is not None:
            cat.subcategories = self._parse_categories(inner_body, ns)

            itemlist = inner_body.find("g:Itemlist", ns)
            if itemlist is not None:
                for item_elem in itemlist.findall("g:Item", ns):
                    cat.items.append(self._parse_item(item_elem, ns))
                for markup_elem in itemlist.findall("g:MarkupItem", ns):
                    cat.items.append(self._parse_markup_item(markup_elem, ns))

        cat.add_texts = self._parse_add_texts(ctgy_elem, ns)

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
        item.pred_qty = self._decimal(item_elem, "g:PredQty", ns)

        qty_tbd = self._text(item_elem, "g:QtyTBD", ns)
        item.qty_tbd = qty_tbd == "Yes"
        not_appl = self._text(item_elem, "g:NotAppl", ns)
        item.not_appl = not_appl == "Yes"
        not_offered = self._text(item_elem, "g:NotOffered", ns)
        item.not_offered = not_offered == "Yes"
        hour_it = self._text(item_elem, "g:HourIt", ns)
        item.hour_it = hour_it == "Yes"
        lump_sum = self._text(item_elem, "g:LumpSumItem", ns)
        item.lump_sum_item = lump_sum == "Yes"

        for i in range(1, 7):
            val = self._decimal(item_elem, f"g:UPComp{i}", ns)
            if val is not None:
                item.up_components[i] = val

        # Positionstypen
        item.provis = self._text(item_elem, "g:Provis", ns)
        item.aln_group_no = self._text(item_elem, "g:ALNGroupNo", ns)
        item.aln_ser_no = self._text(item_elem, "g:ALNSerNo", ns)
        item.free_qty = self._text(item_elem, "g:FreeQty", ns) == "Yes"
        item.key_it = self._text(item_elem, "g:KeyIt", ns) == "Yes"
        item.markup_it = self._text(item_elem, "g:MarkupIt", ns) == "Yes"

        # Zuschlag
        add_pl_it = item_elem.find("g:AddPlIT", ns)
        if add_pl_it is not None:
            item.surcharge_type = self._text(add_pl_it, "g:SurchargeType", ns)
            for grp in add_pl_it.findall("g:AddPlITGrp", ns):
                rno = self._text(grp, "g:RNoPart", ns)
                if rno:
                    item.surcharge_refs.append(rno)

        # Bezugspositionen
        if item_elem.find("g:RefDescr", ns) is not None:
            item.ref_descr = True
        item.ref_rno = self._text(item_elem, "g:RefRNo", ns)
        item.ref_perf_no = self._text(item_elem, "g:RefPerfNo", ns)
        if item_elem.find("g:SumDescr", ns) is not None:
            item.sum_descr = True

        # Unterbeschreibungen
        for sd_elem in item_elem.findall("g:SubDescr", ns):
            sd = SubDescription()
            sd.sub_d_no = self._text(sd_elem, "g:SubDNo", ns)
            sd.qty = self._decimal(sd_elem, "g:Qty", ns)
            sd.qty_spec = self._text(sd_elem, "g:QtySpec", ns)
            sd.qu = self._text(sd_elem, "g:QU", ns)
            desc_elem = sd_elem.find("g:Description", ns)
            if desc_elem is not None:
                sd.description = self._parse_description(desc_elem, ns)
            item.sub_descriptions.append(sd)

        # Katalogzuordnungen
        for ca_elem in item_elem.findall("g:CtlgAssign", ns):
            ca = CtlgAssignment()
            ca.ctlg_id = self._text(ca_elem, "g:CtlgID", ns)
            ca.ctlg_code = self._text(ca_elem, "g:CtlgCode", ns)
            item.ctlg_assignments.append(ca)

        # Mengensplit
        for qs_elem in item_elem.findall("g:QtySplit", ns):
            split = {}
            split_qty = self._decimal(qs_elem, "g:Qty", ns)
            if split_qty is not None:
                split["qty"] = split_qty
            for ca_elem in qs_elem.findall("g:CtlgAssign", ns):
                split["ctlg_id"] = self._text(ca_elem, "g:CtlgID", ns)
                split["ctlg_code"] = self._text(ca_elem, "g:CtlgCode", ns)
            item.qty_splits.append(split)

        desc = item_elem.find("g:Description", ns)
        if desc is not None:
            item.description = self._parse_description(desc, ns)

        # Zusatztexte
        item.add_texts = self._parse_add_texts(item_elem, ns)

        # Bieterkommentare und Textergaenzungen
        for bc_elem in item_elem.findall("g:BidComm", ns):
            text_elem = bc_elem.find("g:Text", ns)
            if text_elem is not None:
                item.bid_comments.append(extract_plain_text(text_elem))
        for tc_elem in item_elem.findall("g:TextCompl", ns):
            text_elem = tc_elem.find("g:Text", ns)
            if text_elem is not None:
                item.text_compls.append(extract_plain_text(text_elem))

        return item

    def _parse_markup_item(self, elem: etree._Element, ns: dict) -> Item:
        """Parse a MarkupItem (Zuschlagsposition) element."""
        item = Item()
        item.id = elem.get("ID", "")
        item.rno_part = elem.get("RNoPart", "")
        item.is_markup_item = True
        item.markup_type = self._text(elem, "g:MarkupType", ns)

        # MarkupSubQty references
        msq = elem.find("g:MarkupSubQty", ns)
        if msq is not None:
            for ref in msq.findall("g:RefItem", ns):
                id_ref = ref.get("IDRef", "")
                if id_ref:
                    item.markup_sub_qty_refs.append(id_ref)

        # MarkupItem can have Qty, QU, UP, IT etc.
        item.qty = self._decimal(elem, "g:Qty", ns)
        item.qu = self._text(elem, "g:QU", ns)
        item.up = self._decimal(elem, "g:UP", ns)
        item.it = self._decimal(elem, "g:IT", ns)
        item.pred_qty = self._decimal(elem, "g:PredQty", ns)

        desc = elem.find("g:Description", ns)
        if desc is not None:
            item.description = self._parse_description(desc, ns)

        item.add_texts = self._parse_add_texts(elem, ns)

        return item

    def _parse_description(self, desc_elem: etree._Element, ns: dict) -> ItemDescription:
        desc = ItemDescription()
        desc.stl_no = self._text(desc_elem, "g:StLNo", ns)

        # STLBBau (preserve raw XML for roundtrip)
        stlb_bau = desc_elem.find("g:STLBBau", ns)
        if stlb_bau is not None:
            from copy import deepcopy
            desc.stlb_bau_raw = deepcopy(stlb_bau)

        complete = desc_elem.find("g:CompleteText", ns)
        if complete is not None:
            # ComplTSA / ComplTSB
            desc.compl_tsa = self._text(complete, "g:ComplTSA", ns)
            desc.compl_tsb = self._text(complete, "g:ComplTSB", ns)

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

    def _parse_add_texts(self, parent: etree._Element, ns: dict) -> list[AddText]:
        result = []
        for at_elem in parent.findall("g:AddText", ns):
            at = AddText()
            outline = at_elem.find(
                "g:OutlineAddText/g:OutlTxt/g:TextOutlTxt", ns
            )
            if outline is None:
                # Manche AddTexts nutzen direkt p/span unter OutlineAddText
                outline = at_elem.find("g:OutlineAddText", ns)
            if outline is not None:
                at.outline_text = extract_plain_text(outline)
                at.outline_html = extract_html(outline)
            detail = at_elem.find("g:DetailAddText/g:Text", ns)
            if detail is None:
                detail = at_elem.find("g:DetailAddText", ns)
            if detail is not None:
                at.detail_text = extract_plain_text(detail)
                at.detail_html = extract_html(detail)
            result.append(at)
        return result
