import uuid
from copy import deepcopy
from datetime import date, time

from lxml import etree

from lvgenerator.constants import GAEBPhase, GAEB_DEFAULT_VERSION
from lvgenerator.gaeb.namespaces import get_namespace
from lvgenerator.gaeb.phase_rules import get_rules
from lvgenerator.gaeb.text_parser import build_text_element
from lvgenerator.models.boq import BoQ, BoQBkdn, BoQInfo, Catalog, Totals
from lvgenerator.models.category import BoQCategory
from lvgenerator.models.item import Item
from lvgenerator.models.project import GAEBProject
from lvgenerator.models.text_types import AddText


class GAEBWriter:

    def write(self, project: GAEBProject, file_path: str,
              version: str = GAEB_DEFAULT_VERSION) -> None:
        # Use the project's own version if available to avoid namespace mismatch
        effective_version = project.gaeb_info.version or version
        ns_uri = get_namespace(project.phase, effective_version)
        nsmap = {None: ns_uri}

        root = etree.Element(f"{{{ns_uri}}}GAEB", nsmap=nsmap)
        self._write_gaeb_info(root, project.gaeb_info, ns_uri)
        self._write_prj_info(root, project.prj_info, ns_uri)
        self._write_award(root, project, ns_uri)

        # GAEB-level AddTexts (Schlussbemerkungen)
        self._write_add_texts(root, project.gaeb_add_texts, ns_uri)

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
        if info.currency:
            self._sub(pi, "Cur", ns, info.currency)
        if info.currency_label:
            self._sub(pi, "CurLbl", ns, info.currency_label)
        if info.bid_comm_perm:
            self._sub(pi, "BidCommPerm", ns, "Yes")

    def _write_award(self, root: etree._Element, project: GAEBProject, ns: str) -> None:
        award = self._sub(root, "Award", ns)
        self._sub(award, "DP", ns, str(project.phase.dp_value))

        ai = self._sub(award, "AwardInfo", ns)
        if project.award_info.cat:
            self._sub(ai, "Cat", ns, project.award_info.cat)
        if project.award_info.boq_id:
            self._sub(ai, "BoQID", ns, project.award_info.boq_id)
        self._sub(ai, "Cur", ns, project.award_info.currency)
        self._sub(ai, "CurLbl", ns, project.award_info.currency_label)
        if project.award_info.open_date:
            self._sub(ai, "OpenDate", ns, project.award_info.open_date)
        if project.award_info.open_time:
            self._sub(ai, "OpenTime", ns, project.award_info.open_time)
        if project.award_info.eval_end:
            self._sub(ai, "EvalEnd", ns, project.award_info.eval_end)
        if project.award_info.subm_loc:
            self._sub(ai, "SubmLoc", ns, project.award_info.subm_loc)
        if project.award_info.cnst_start:
            self._sub(ai, "CnstStart", ns, project.award_info.cnst_start)
        if project.award_info.cnst_end:
            self._sub(ai, "CnstEnd", ns, project.award_info.cnst_end)
        if project.award_info.contr_no:
            self._sub(ai, "ContrNo", ns, project.award_info.contr_no)
        if project.award_info.contr_date:
            self._sub(ai, "ContrDate", ns, project.award_info.contr_date)
        if project.award_info.accept_type:
            self._sub(ai, "AcceptType", ns, project.award_info.accept_type)
        if project.award_info.warr_dur:
            self._sub(ai, "WarrDur", ns, project.award_info.warr_dur)
        if project.award_info.warr_unit:
            self._sub(ai, "WarrUnit", ns, project.award_info.warr_unit)

        if project.owner:
            own = self._sub(award, "OWN", ns)
            self._write_address(own, project.owner, ns)
            if project.award_info.award_no:
                self._sub(own, "AwardNo", ns, project.award_info.award_no)

        # CTR (Contractor/Bidder)
        if project.contractor:
            ctr = self._sub(award, "CTR", ns)
            if project.contractor.address:
                self._write_address(ctr, project.contractor.address, ns)
            if project.contractor.has_dp_no:
                self._sub(ctr, "DPNo", ns, project.contractor.dp_no or None)
            if project.contractor.has_award_no:
                self._sub(ctr, "AwardNo", ns, project.contractor.award_no or None)
            if project.contractor.has_accts_pay_no:
                self._sub(ctr, "AcctsPayNo", ns, project.contractor.accts_pay_no or None)

        # Award-level AddTexts
        self._write_add_texts(award, project.award_add_texts, ns)

        if project.boq:
            self._write_boq(award, project.boq, project.phase, ns)

    def _write_address(self, parent: etree._Element, address, ns: str) -> None:
        addr = self._sub(parent, "Address", ns)
        if address.name1:
            self._sub(addr, "Name1", ns, address.name1)
        if address.name2:
            self._sub(addr, "Name2", ns, address.name2)
        if address.name3:
            self._sub(addr, "Name3", ns, address.name3)
        if address.name4:
            self._sub(addr, "Name4", ns, address.name4)
        if address.street:
            self._sub(addr, "Street", ns, address.street)
        if address.pcode:
            self._sub(addr, "PCode", ns, address.pcode)
        if address.city:
            self._sub(addr, "City", ns, address.city)
        if address.country:
            self._sub(addr, "Country", ns, address.country)
        if address.contact:
            self._sub(addr, "Contact", ns, address.contact)
        if address.phone:
            self._sub(addr, "Phone", ns, address.phone)
        if address.fax:
            self._sub(addr, "Fax", ns, address.fax)
        if address.email:
            self._sub(addr, "Email", ns, address.email)

    def _write_boq(self, parent: etree._Element, boq: BoQ,
                   phase: GAEBPhase, ns: str) -> None:
        boq_id = boq.id or str(uuid.uuid4())
        boq_elem = self._sub(parent, "BoQ", ns)
        boq_elem.set("ID", boq_id)

        self._write_boq_info(boq_elem, boq.info, phase, ns)

        if boq.categories or boq.remarks_raw:
            body = self._sub(boq_elem, "BoQBody", ns)
            for remark in boq.remarks_raw:
                body.append(deepcopy(remark))
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
        if info.outline_complete:
            self._sub(bi, "OutlCompl", ns, info.outline_complete)

        for bkdn in info.breakdowns:
            self._write_breakdown(bi, bkdn, ns)

        # UP Component labels
        if info.no_up_comps:
            self._sub(bi, "NoUPComps", ns, str(info.no_up_comps))
        for i in range(1, 7):
            if i in info.up_comp_labels:
                lbl_elem = self._sub(bi, f"LblUPComp{i}", ns, info.up_comp_labels[i])
                if i in info.up_comp_types:
                    lbl_elem.set("Type", info.up_comp_types[i])

        rules = get_rules(phase)
        if rules.has_totals and info.totals:
            self._write_totals(bi, info.totals, ns)

        # Kataloge
        for ctlg in info.catalogs:
            self._write_catalog(bi, ctlg, ns)

        self._write_add_texts(bi, info.add_texts, ns)

    def _write_breakdown(self, parent: etree._Element, bkdn: BoQBkdn, ns: str) -> None:
        b = self._sub(parent, "BoQBkdn", ns)
        self._sub(b, "Type", ns, bkdn.type)
        if bkdn.label:
            self._sub(b, "LblBoQBkdn", ns, bkdn.label)
        self._sub(b, "Length", ns, str(bkdn.length))
        self._sub(b, "Num", ns, "Yes" if bkdn.numeric else "No")
        if bkdn.alignment:
            self._sub(b, "Alignment", ns, bkdn.alignment)

    def _write_catalog(self, parent: etree._Element, ctlg: Catalog, ns: str) -> None:
        c = self._sub(parent, "Ctlg", ns)
        if ctlg.ctlg_id:
            self._sub(c, "CtlgID", ns, ctlg.ctlg_id)
        if ctlg.ctlg_type:
            self._sub(c, "CtlgType", ns, ctlg.ctlg_type)
        if ctlg.ctlg_name:
            self._sub(c, "CtlgName", ns, ctlg.ctlg_name)

    def _write_totals(self, parent: etree._Element, totals: Totals, ns: str) -> None:
        t = self._sub(parent, "Totals", ns)
        self._sub(t, "Total", ns, str(totals.total))
        if totals.discount_pcnt is not None:
            self._sub(t, "DiscountPcnt", ns, str(totals.discount_pcnt))
        if totals.discount_amt is not None:
            self._sub(t, "DiscountAmt", ns, str(totals.discount_amt))
        if totals.tot_after_disc is not None:
            self._sub(t, "TotAfterDisc", ns, str(totals.tot_after_disc))
        if totals.total_net is not None:
            self._sub(t, "TotalNet", ns, str(totals.total_net))
        if totals.vat is not None:
            self._sub(t, "VAT", ns, str(totals.vat))
        if totals.vat_amount is not None:
            self._sub(t, "VATAmount", ns, str(totals.vat_amount))
        if totals.total_gross is not None:
            self._sub(t, "TotalGross", ns, str(totals.total_gross))
        if totals.total_lsum is not None:
            self._sub(t, "TotalLSUM", ns, str(totals.total_lsum))

    def _write_category(self, parent: etree._Element, cat: BoQCategory,
                        phase: GAEBPhase, ns: str) -> None:
        ctgy = self._sub(parent, "BoQCtgy", ns)
        if cat.id:
            ctgy.set("ID", cat.id)
        if cat.rno_part:
            ctgy.set("RNoPart", cat.rno_part)

        if cat.label:
            lbl = self._sub(ctgy, "LblTx", ns)
            if cat.label_html:
                self._write_raw_html(lbl, cat.label_html, ns)
            else:
                p = etree.SubElement(lbl, f"{{{ns}}}p")
                span = etree.SubElement(p, f"{{{ns}}}span")
                span.text = cat.label

        # Grund-/Wahlgruppen auf Kategorieebene
        if cat.aln_b_group_no:
            self._sub(ctgy, "ALNBGroupNo", ns, cat.aln_b_group_no)
        if cat.aln_b_ser_no:
            self._sub(ctgy, "ALNBSerNo", ns, cat.aln_b_ser_no)

        if cat.exec_descr:
            ed = self._sub(ctgy, "ExecDescr", ns)
            text_elem = self._sub(ed, "Text", ns)
            for line in cat.exec_descr.split("\n"):
                p = etree.SubElement(text_elem, f"{{{ns}}}p")
                span = etree.SubElement(p, f"{{{ns}}}span")
                span.text = line

        if cat.subcategories or cat.items or cat.remarks_raw:
            body = self._sub(ctgy, "BoQBody", ns)
            for remark in cat.remarks_raw:
                body.append(deepcopy(remark))
            for subcat in cat.subcategories:
                self._write_category(body, subcat, phase, ns)
            if cat.items or cat.itemlist_remarks_raw or cat.perf_descrs_raw:
                itemlist = self._sub(body, "Itemlist", ns)
                for remark in cat.itemlist_remarks_raw:
                    itemlist.append(deepcopy(remark))
                for item in cat.items:
                    if item.is_markup_item:
                        self._write_markup_item(itemlist, item, phase, ns)
                    else:
                        self._write_item(itemlist, item, phase, ns)
                for pd in cat.perf_descrs_raw:
                    itemlist.append(deepcopy(pd))

        if cat.totals is not None:
            self._write_totals(ctgy, cat.totals, ns)

        self._write_add_texts(ctgy, cat.add_texts, ns)

    def _write_item(self, parent: etree._Element, item: Item,
                    phase: GAEBPhase, ns: str) -> None:
        """Write an Item element with children in XSD-conformant order."""
        rules = get_rules(phase)
        item_elem = self._sub(parent, "Item", ns)
        item_id = item.id or str(uuid.uuid4())
        item_elem.set("ID", item_id)
        if item.rno_part:
            item_elem.set("RNoPart", item.rno_part)

        # --- XSD sequence order ---
        # 1. ALNGroupNo, ALNSerNo
        if item.aln_group_no:
            self._sub(item_elem, "ALNGroupNo", ns, item.aln_group_no)
        if item.aln_ser_no:
            self._sub(item_elem, "ALNSerNo", ns, item.aln_ser_no)

        # 2. Provis
        if item.provis:
            self._sub(item_elem, "Provis", ns, item.provis)

        # 3. LumpSumItem
        if item.lump_sum_item:
            self._sub(item_elem, "LumpSumItem", ns, "Yes")

        # 4. NotAppl
        if item.not_appl:
            self._sub(item_elem, "NotAppl", ns, "Yes")

        # 5. NotOffered
        if rules.allows_not_offered and item.not_offered:
            self._sub(item_elem, "NotOffered", ns, "Yes")

        # 6. HourIt
        if item.hour_it:
            self._sub(item_elem, "HourIt", ns, "Yes")

        # 7. KeyIt
        if item.key_it:
            self._sub(item_elem, "KeyIt", ns, "Yes")

        # 8. FreeQty
        if item.free_qty:
            self._sub(item_elem, "FreeQty", ns, "Yes")

        # 9. UPBkdn (value must be "Yes" or "No")
        if item.up_bkdn:
            self._sub(item_elem, "UPBkdn", ns, "Yes")

        # 10. MarkupIt
        if item.markup_it:
            self._sub(item_elem, "MarkupIt", ns, "Yes")

        # 11. Zuschlag (AddPlIT)
        if item.surcharge_type:
            add_pl_it = self._sub(item_elem, "AddPlIT", ns)
            self._sub(add_pl_it, "SurchargeType", ns, item.surcharge_type)
            for ref in item.surcharge_refs:
                grp = self._sub(add_pl_it, "AddPlITGrp", ns)
                self._sub(grp, "RNoPart", ns, ref)

        # 12. RefDescr (value must be "Ref" or "Rep")
        if item.ref_descr:
            self._sub(item_elem, "RefDescr", ns, item.ref_descr)

        # 13. RefRNo / RefPerfNo
        if item.ref_rno or item.ref_rno_idref:
            el = self._sub(item_elem, "RefRNo", ns, item.ref_rno or None)
            if item.ref_rno_idref:
                el.set("IDRef", item.ref_rno_idref)
        if item.ref_perf_no or item.ref_perf_no_idref:
            el = self._sub(item_elem, "RefPerfNo", ns, item.ref_perf_no or None)
            if item.ref_perf_no_idref:
                el.set("IDRef", item.ref_perf_no_idref)

        # 14. QtyTBD / Qty
        effective_qty = item.get_effective_qty()
        if item.qty_tbd:
            self._sub(item_elem, "QtyTBD", ns, "Yes")
        if effective_qty is not None:
            self._sub(item_elem, "Qty", ns, str(effective_qty))

        # 15. QtySplit
        for split in item.qty_splits:
            qs = self._sub(item_elem, "QtySplit", ns)
            if "qty" in split:
                self._sub(qs, "Qty", ns, str(split["qty"]))
            if "ctlg_assigns" in split:
                for assign in split["ctlg_assigns"]:
                    ca = self._sub(qs, "CtlgAssign", ns)
                    self._sub(ca, "CtlgID", ns, assign["ctlg_id"])
                    if assign.get("ctlg_code"):
                        self._sub(ca, "CtlgCode", ns, assign["ctlg_code"])
            elif "ctlg_id" in split:
                ca = self._sub(qs, "CtlgAssign", ns)
                self._sub(ca, "CtlgID", ns, split["ctlg_id"])
                if "ctlg_code" in split:
                    self._sub(ca, "CtlgCode", ns, split["ctlg_code"])

        # 16. PredQty
        if item.pred_qty is not None:
            self._sub(item_elem, "PredQty", ns, str(item.pred_qty))

        # 17. QU
        if item.qu:
            self._sub(item_elem, "QU", ns, item.qu)

        # 18. CtlgAssign (before UP!)
        for ca in item.ctlg_assignments:
            ca_elem = self._sub(item_elem, "CtlgAssign", ns)
            if ca.ctlg_id:
                self._sub(ca_elem, "CtlgID", ns, ca.ctlg_id)
            if ca.ctlg_code:
                self._sub(ca_elem, "CtlgCode", ns, ca.ctlg_code)

        # 19. UP, UPComp1-6, DiscountPcnt
        if rules.has_prices:
            if item.up is not None:
                self._sub(item_elem, "UP", ns, str(item.up))
            for i in range(1, 7):
                if i in item.up_components:
                    self._sub(item_elem, f"UPComp{i}", ns, str(item.up_components[i]))
            if item.discount_pcnt is not None:
                self._sub(item_elem, "DiscountPcnt", ns, str(item.discount_pcnt))

        # 20. IT
        if rules.has_totals and item.it is not None:
            self._sub(item_elem, "IT", ns, str(item.it))

        # 21. VAT
        if item.vat is not None:
            self._sub(item_elem, "VAT", ns, str(item.vat))

        # 22. Description
        self._write_description(item_elem, item.description, ns)

        # 23. BidComm, TextCompl (nach Description)
        if rules.has_bid_comments:
            for comment in item.bid_comments:
                bc = self._sub(item_elem, "BidComm", ns)
                text_elem = self._sub(bc, "Text", ns)
                for line in comment.split("\n"):
                    p = etree.SubElement(text_elem, f"{{{ns}}}p")
                    span = etree.SubElement(p, f"{{{ns}}}span")
                    span.text = line
            for compl in item.text_compls:
                tc = self._sub(item_elem, "TextCompl", ns)
                text_elem = self._sub(tc, "Text", ns)
                for line in compl.split("\n"):
                    p = etree.SubElement(text_elem, f"{{{ns}}}p")
                    span = etree.SubElement(p, f"{{{ns}}}span")
                    span.text = line

        # 24. SumDescr (nach Description, value must be "Yes")
        if item.sum_descr:
            self._sub(item_elem, "SumDescr", ns, "Yes")

        # 25. SubDescr (nach SumDescr, XSD order: SubDNo, Description, QtySpec, Qty, QU)
        for sd in item.sub_descriptions:
            sd_elem = self._sub(item_elem, "SubDescr", ns)
            if sd.sub_d_no:
                self._sub(sd_elem, "SubDNo", ns, sd.sub_d_no)
            if sd.description is not None:
                self._write_description(sd_elem, sd.description, ns)
            if sd.qty_spec:
                self._sub(sd_elem, "QtySpec", ns, sd.qty_spec)
            if sd.qty is not None:
                self._sub(sd_elem, "Qty", ns, str(sd.qty))
            if sd.qu:
                self._sub(sd_elem, "QU", ns, sd.qu)

        # 26. Zusatztexte
        self._write_add_texts(item_elem, item.add_texts, ns)

    def _write_markup_item(self, parent: etree._Element, item: Item,
                           phase: GAEBPhase, ns: str) -> None:
        """Write a MarkupItem (Zuschlagsposition) element in XSD-conformant order."""
        rules = get_rules(phase)
        mi_elem = self._sub(parent, "MarkupItem", ns)
        mi_id = item.id or str(uuid.uuid4())
        mi_elem.set("ID", mi_id)
        if item.rno_part:
            mi_elem.set("RNoPart", item.rno_part)

        # --- XSD sequence order for MarkupItem ---
        # 1. RefDescr (value must be "Ref" or "Rep")
        if item.ref_descr:
            self._sub(mi_elem, "RefDescr", ns, item.ref_descr)
        if item.ref_rno or item.ref_rno_idref:
            el = self._sub(mi_elem, "RefRNo", ns, item.ref_rno or None)
            if item.ref_rno_idref:
                el.set("IDRef", item.ref_rno_idref)
        if item.ref_perf_no or item.ref_perf_no_idref:
            el = self._sub(mi_elem, "RefPerfNo", ns, item.ref_perf_no or None)
            if item.ref_perf_no_idref:
                el.set("IDRef", item.ref_perf_no_idref)

        # 2. MarkupType
        if item.markup_type:
            self._sub(mi_elem, "MarkupType", ns, item.markup_type)

        # 3. MarkupSubQty
        if item.markup_sub_qty_refs:
            msq = self._sub(mi_elem, "MarkupSubQty", ns)
            for ref_id in item.markup_sub_qty_refs:
                ref_elem = self._sub(msq, "RefItem", ns)
                ref_elem.set("IDRef", ref_id)

        # 4. Qty, PredQty, QU
        effective_qty = item.get_effective_qty()
        if effective_qty is not None:
            self._sub(mi_elem, "Qty", ns, str(effective_qty))
        if item.pred_qty is not None:
            self._sub(mi_elem, "PredQty", ns, str(item.pred_qty))
        if item.qu:
            self._sub(mi_elem, "QU", ns, item.qu)

        # 5. ITMarkup
        if item.it_markup is not None:
            self._sub(mi_elem, "ITMarkup", ns, str(item.it_markup))

        # 6. Markup (must be decimal value, not empty)
        if item.has_markup and item.markup_value is not None:
            self._sub(mi_elem, "Markup", ns, str(item.markup_value))

        # 7. UP
        if rules.has_prices and item.up is not None:
            self._sub(mi_elem, "UP", ns, str(item.up))

        # 8. IT
        if rules.has_totals and item.it is not None:
            self._sub(mi_elem, "IT", ns, str(item.it))

        # 9. Description
        self._write_description(mi_elem, item.description, ns)

        # 10. CtlgAssign (after Description for MarkupItem)
        for ca in item.ctlg_assignments:
            ca_elem = self._sub(mi_elem, "CtlgAssign", ns)
            if ca.ctlg_id:
                self._sub(ca_elem, "CtlgID", ns, ca.ctlg_id)
            if ca.ctlg_code:
                self._sub(ca_elem, "CtlgCode", ns, ca.ctlg_code)

        self._write_add_texts(mi_elem, item.add_texts, ns)

    def _write_description(self, parent: etree._Element, desc, ns: str) -> None:
        has_content = (desc.outline_text or desc.detail_text or desc.stl_no
                       or desc.stlb_bau_raw is not None
                       or desc.perf_descr_raw is not None
                       or desc.detail_txt_raw is not None
                       or desc.text_complements_raw)
        if not has_content:
            return

        description = self._sub(parent, "Description", ns)

        if desc.stl_no:
            self._sub(description, "StLNo", ns, desc.stl_no)

        # STLBBau (roundtrip from raw XML)
        if desc.stlb_bau_raw is not None:
            description.append(deepcopy(desc.stlb_bau_raw))

        # PerfDescr (roundtrip from raw XML)
        if desc.perf_descr_raw is not None:
            description.append(deepcopy(desc.perf_descr_raw))

        if (desc.detail_text or desc.outline_text or desc.compl_tsa
                or desc.compl_tsb or desc.text_complements_raw):
            complete = self._sub(description, "CompleteText", ns)

            if desc.compl_tsa:
                self._sub(complete, "ComplTSA", ns, desc.compl_tsa)
            if desc.compl_tsb:
                self._sub(complete, "ComplTSB", ns, desc.compl_tsb)

            if desc.detail_text or desc.text_complements_raw:
                if desc.detail_txt_raw is not None:
                    # Roundtrip: preserve entire DetailTxt with interleaved Text/TextComplement
                    complete.append(deepcopy(desc.detail_txt_raw))
                else:
                    detail_txt = self._sub(complete, "DetailTxt", ns)
                    if desc.detail_text:
                        if desc.detail_html:
                            self._write_raw_html(detail_txt, desc.detail_html, ns)
                        else:
                            text_elem = self._sub(detail_txt, "Text", ns)
                            for line in desc.detail_text.split("\n"):
                                p = etree.SubElement(text_elem, f"{{{ns}}}p")
                                span = etree.SubElement(p, f"{{{ns}}}span")
                                span.text = line
                    # TextComplement (roundtrip inside DetailTxt)
                    for tc in desc.text_complements_raw:
                        detail_txt.append(deepcopy(tc))

            if desc.outline_text:
                outline = self._sub(complete, "OutlineText", ns)
                outl_txt = self._sub(outline, "OutlTxt", ns)
                if desc.outline_html:
                    self._write_raw_html(outl_txt, desc.outline_html, ns)
                else:
                    text_outl = self._sub(outl_txt, "TextOutlTxt", ns)
                    for line in desc.outline_text.split("\n"):
                        p = etree.SubElement(text_outl, f"{{{ns}}}p")
                        span = etree.SubElement(p, f"{{{ns}}}span")
                        span.text = line

    def _write_raw_html(self, parent: etree._Element, html: str, ns: str) -> None:
        """Write preserved HTML back into the XML tree.

        If the parsed HTML root tag matches the parent tag, append children
        instead of the element itself to avoid double-wrapping.
        """
        try:
            fragment = etree.fromstring(html)
            parent_local = parent.tag.split("}")[-1] if "}" in parent.tag else parent.tag
            frag_local = fragment.tag.split("}")[-1] if "}" in fragment.tag else fragment.tag
            if parent_local == frag_local:
                # Avoid double-wrapping: copy text and children
                if fragment.text:
                    parent.text = fragment.text
                for child in fragment:
                    parent.append(child)
            else:
                parent.append(fragment)
        except etree.XMLSyntaxError:
            # Fallback: wrap in Text element
            text_elem = self._sub(parent, "Text", ns)
            text_elem.text = html

    def _write_add_texts(self, parent: etree._Element,
                         add_texts: list[AddText], ns: str) -> None:
        for at in add_texts:
            at_elem = self._sub(parent, "AddText", ns)
            if at.outline_text:
                if at.outline_html:
                    oat = self._sub(at_elem, "OutlineAddText", ns)
                    self._write_raw_html(oat, at.outline_html, ns)
                else:
                    oat = self._sub(at_elem, "OutlineAddText", ns)
                    outl_txt = self._sub(oat, "OutlTxt", ns)
                    text_outl = self._sub(outl_txt, "TextOutlTxt", ns)
                    for line in at.outline_text.split("\n"):
                        p = etree.SubElement(text_outl, f"{{{ns}}}p")
                        span = etree.SubElement(p, f"{{{ns}}}span")
                        span.text = line
            if at.detail_text:
                if at.detail_html:
                    dat = self._sub(at_elem, "DetailAddText", ns)
                    self._write_raw_html(dat, at.detail_html, ns)
                else:
                    dat = self._sub(at_elem, "DetailAddText", ns)
                    text_elem = self._sub(dat, "Text", ns)
                    for line in at.detail_text.split("\n"):
                        p = etree.SubElement(text_elem, f"{{{ns}}}p")
                        span = etree.SubElement(p, f"{{{ns}}}span")
                        span.text = line
