from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Optional

from lxml import etree

from lvgenerator.constants import GAEBPhase
from lvgenerator.gaeb.namespaces import detect_phase_and_version
from lvgenerator.gaeb.text_parser import extract_plain_text, extract_html
from lvgenerator.models.address import Address, Contractor
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
        project.contractor = self._parse_contractor(root, ns)
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
        info.currency = self._text(pi, "g:Cur", ns)
        info.currency_label = self._text(pi, "g:CurLbl", ns)
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

    def _parse_address(self, addr_elem: etree._Element, ns: dict) -> Address:
        addr = Address()
        addr.name1 = self._text(addr_elem, "g:Name1", ns)
        addr.name2 = self._text(addr_elem, "g:Name2", ns)
        addr.name3 = self._text(addr_elem, "g:Name3", ns)
        addr.name4 = self._text(addr_elem, "g:Name4", ns)
        addr.street = self._text(addr_elem, "g:Street", ns)
        addr.pcode = self._text(addr_elem, "g:PCode", ns)
        addr.city = self._text(addr_elem, "g:City", ns)
        addr.country = self._text(addr_elem, "g:Country", ns)
        addr.contact = self._text(addr_elem, "g:Contact", ns)
        addr.phone = self._text(addr_elem, "g:Phone", ns)
        addr.fax = self._text(addr_elem, "g:Fax", ns)
        addr.email = self._text(addr_elem, "g:Email", ns)
        return addr

    def _parse_owner(self, root: etree._Element, ns: dict) -> Optional[Address]:
        addr_elem = root.find("g:Award/g:OWN/g:Address", ns)
        if addr_elem is None:
            return None
        return self._parse_address(addr_elem, ns)

    def _parse_contractor(self, root: etree._Element, ns: dict) -> Optional[Contractor]:
        ctr_elem = root.find("g:Award/g:CTR", ns)
        if ctr_elem is None:
            return None
        ctr = Contractor()
        addr_elem = ctr_elem.find("g:Address", ns)
        if addr_elem is not None:
            ctr.address = self._parse_address(addr_elem, ns)
        # These elements may exist but be empty
        dp_no = ctr_elem.find("g:DPNo", ns)
        if dp_no is not None:
            ctr.dp_no = dp_no.text.strip() if dp_no.text else ""
            ctr.has_dp_no = True
        award_no = ctr_elem.find("g:AwardNo", ns)
        if award_no is not None:
            ctr.award_no = award_no.text.strip() if award_no.text else ""
            ctr.has_award_no = True
        accts_pay = ctr_elem.find("g:AcctsPayNo", ns)
        if accts_pay is not None:
            ctr.accts_pay_no = accts_pay.text.strip() if accts_pay.text else ""
            ctr.has_accts_pay_no = True
        return ctr

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
            boq.remarks_raw = self._parse_remarks_raw(body, ns)
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
        info.outline_complete = self._text(bi, "g:OutlCompl", ns)

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
            cat.ctlg_type = self._text(ctlg_elem, "g:CtlgType", ns)
            cat.ctlg_name = self._text(ctlg_elem, "g:CtlgName", ns)
            info.catalogs.append(cat)

        # UP Component labels
        no_up = self._text(bi, "g:NoUPComps", ns)
        if no_up:
            try:
                info.no_up_comps = int(no_up)
            except ValueError:
                pass
        for i in range(1, 7):
            lbl_elem = bi.find(f"g:LblUPComp{i}", ns)
            if lbl_elem is not None:
                lbl = lbl_elem.text.strip() if lbl_elem.text else ""
                if lbl:
                    info.up_comp_labels[i] = lbl
                comp_type = lbl_elem.get("Type", "")
                if comp_type:
                    info.up_comp_types[i] = comp_type

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
        totals.tot_after_disc = self._decimal(totals_elem, "g:TotAfterDisc", ns)
        totals.total_net = self._decimal(totals_elem, "g:TotalNet", ns)
        totals.vat = self._decimal(totals_elem, "g:VAT", ns)
        totals.vat_amount = self._decimal(totals_elem, "g:VATAmount", ns)
        totals.total_gross = self._decimal(totals_elem, "g:TotalGross", ns)
        totals.total_lsum = self._decimal(totals_elem, "g:TotalLSUM", ns)
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
            cat.remarks_raw = self._parse_remarks_raw(inner_body, ns)

            itemlist = inner_body.find("g:Itemlist", ns)
            if itemlist is not None:
                for item_elem in itemlist.findall("g:Item", ns):
                    cat.items.append(self._parse_item(item_elem, ns))
                for markup_elem in itemlist.findall("g:MarkupItem", ns):
                    cat.items.append(self._parse_markup_item(markup_elem, ns))
                cat.itemlist_remarks_raw = self._parse_remarks_raw(itemlist, ns)
                # PerfDescr (Leistungsbeschreibung) - preserve raw XML
                from copy import deepcopy
                for pd_elem in itemlist.findall("g:PerfDescr", ns):
                    cat.perf_descrs_raw.append(deepcopy(pd_elem))

        # Category-level Totals
        totals_elem = ctgy_elem.find("g:Totals", ns)
        if totals_elem is not None:
            cat.totals = self._parse_totals(totals_elem, ns)

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
        if item_elem.find("g:UPBkdn", ns) is not None:
            item.up_bkdn = True

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
        ref_descr_elem = item_elem.find("g:RefDescr", ns)
        if ref_descr_elem is not None:
            item.ref_descr = ref_descr_elem.text.strip() if ref_descr_elem.text else "Ref"
        ref_rno_elem = item_elem.find("g:RefRNo", ns)
        if ref_rno_elem is not None:
            item.ref_rno = ref_rno_elem.text.strip() if ref_rno_elem.text else ""
            item.ref_rno_idref = ref_rno_elem.get("IDRef", "")
        ref_perf_elem = item_elem.find("g:RefPerfNo", ns)
        if ref_perf_elem is not None:
            item.ref_perf_no = ref_perf_elem.text.strip() if ref_perf_elem.text else ""
            item.ref_perf_no_idref = ref_perf_elem.get("IDRef", "")
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
            assigns = []
            for ca_elem in qs_elem.findall("g:CtlgAssign", ns):
                assigns.append({
                    "ctlg_id": self._text(ca_elem, "g:CtlgID", ns),
                    "ctlg_code": self._text(ca_elem, "g:CtlgCode", ns),
                })
            if assigns:
                split["ctlg_assigns"] = assigns
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

        # MarkupItem can have Qty, QU, UP, IT, ITMarkup, Markup etc.
        item.qty = self._decimal(elem, "g:Qty", ns)
        item.qu = self._text(elem, "g:QU", ns)
        item.up = self._decimal(elem, "g:UP", ns)
        item.it = self._decimal(elem, "g:IT", ns)
        item.it_markup = self._decimal(elem, "g:ITMarkup", ns)
        markup_elem = elem.find("g:Markup", ns)
        if markup_elem is not None:
            item.has_markup = True
            item.markup_value = self._decimal(elem, "g:Markup", ns)
        item.pred_qty = self._decimal(elem, "g:PredQty", ns)

        # Bezugspositionen
        ref_descr_elem2 = elem.find("g:RefDescr", ns)
        if ref_descr_elem2 is not None:
            item.ref_descr = ref_descr_elem2.text.strip() if ref_descr_elem2.text else "Ref"
        ref_rno_elem = elem.find("g:RefRNo", ns)
        if ref_rno_elem is not None:
            item.ref_rno = ref_rno_elem.text.strip() if ref_rno_elem.text else ""
            item.ref_rno_idref = ref_rno_elem.get("IDRef", "")
        ref_perf_elem = elem.find("g:RefPerfNo", ns)
        if ref_perf_elem is not None:
            item.ref_perf_no = ref_perf_elem.text.strip() if ref_perf_elem.text else ""
            item.ref_perf_no_idref = ref_perf_elem.get("IDRef", "")

        # Katalogzuordnungen
        for ca_elem in elem.findall("g:CtlgAssign", ns):
            ca = CtlgAssignment()
            ca.ctlg_id = self._text(ca_elem, "g:CtlgID", ns)
            ca.ctlg_code = self._text(ca_elem, "g:CtlgCode", ns)
            item.ctlg_assignments.append(ca)

        desc = elem.find("g:Description", ns)
        if desc is not None:
            item.description = self._parse_description(desc, ns)

        item.add_texts = self._parse_add_texts(elem, ns)

        return item

    def _parse_remarks_raw(self, body: etree._Element, ns: dict) -> list:
        """Preserve Remark elements as raw XML for roundtrip."""
        from copy import deepcopy
        remarks = []
        for remark in body.findall("g:Remark", ns):
            remarks.append(deepcopy(remark))
        return remarks

    def _parse_description(self, desc_elem: etree._Element, ns: dict) -> ItemDescription:
        from copy import deepcopy
        desc = ItemDescription()
        desc.stl_no = self._text(desc_elem, "g:StLNo", ns)

        # STLBBau (preserve raw XML for roundtrip)
        stlb_bau = desc_elem.find("g:STLBBau", ns)
        if stlb_bau is not None:
            desc.stlb_bau_raw = deepcopy(stlb_bau)

        # PerfDescr (preserve raw XML for roundtrip)
        perf_descr = desc_elem.find("g:PerfDescr", ns)
        if perf_descr is not None:
            desc.perf_descr_raw = deepcopy(perf_descr)

        complete = desc_elem.find("g:CompleteText", ns)
        if complete is not None:
            # ComplTSA / ComplTSB
            desc.compl_tsa = self._text(complete, "g:ComplTSA", ns)
            desc.compl_tsb = self._text(complete, "g:ComplTSB", ns)

            detail_txt = complete.find("g:DetailTxt", ns)
            if detail_txt is not None:
                detail = detail_txt.find("g:Text", ns)
                if detail is not None:
                    desc.detail_text = extract_plain_text(detail)
                    desc.detail_html = extract_html(detail)

                # TextComplement (preserve raw XML for roundtrip)
                for tc in detail_txt.findall("g:TextComplement", ns):
                    desc.text_complements_raw.append(deepcopy(tc))

                # Preserve entire DetailTxt if it has interleaved Text/TextComplement
                children = list(detail_txt)
                if len(children) > 1:
                    desc.detail_txt_raw = deepcopy(detail_txt)

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
