"""Numeración nativa multinivel sin alterar las definiciones del original."""

from docx.opc.constants import CONTENT_TYPE as CT, RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.parts.numbering import NumberingPart


def _value_element(name, value):
    element = OxmlElement(name)
    element.set(qn("w:val"), str(value))
    return element


def _numbering_root(document):
    part = document.part
    try:
        return part.numbering_part.element
    except NotImplementedError:
        # python-docx no implementa NumberingPart.new() para paquetes sin esta parte.
        package = part.package
        name = PackURI("/word/numbering.xml")
        if any(item.partname == name for item in package.parts):
            name = package.next_partname("/word/numbering%d.xml")
        numbering = NumberingPart(name, CT.WML_NUMBERING, OxmlElement("w:numbering"), package)
        part.relate_to(numbering, RT.NUMBERING)
        return numbering.element


class NativeLists:
    def __init__(self, document):
        self.document = document
        self._root = None
        self._abstract_ids = {}
        self._levels = {}

    def reset(self):
        self._levels.clear()

    @property
    def root(self):
        if self._root is None:
            self._root = _numbering_root(self.document)
        return self._root

    def _abstract_id(self, ordered):
        if ordered in self._abstract_ids:
            return self._abstract_ids[ordered]
        fmt = "decimal" if ordered else "bullet"
        for abstract in self.root.findall(qn("w:abstractNum")):
            levels = {int(level.get(qn("w:ilvl"))): level for level in abstract.findall(qn("w:lvl"))}
            if all(
                index in levels and levels[index].find(qn("w:numFmt")) is not None
                and levels[index].find(qn("w:numFmt")).get(qn("w:val")) == fmt
                for index in range(9)
            ):
                abstract_id = int(abstract.get(qn("w:abstractNumId")))
                self._abstract_ids[ordered] = abstract_id
                return abstract_id

        abstract_id = 1 + max(
            (int(item.get(qn("w:abstractNumId"))) for item in self.root.findall(qn("w:abstractNum"))),
            default=-1,
        )
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abstract_id))
        abstract.append(_value_element("w:multiLevelType", "multilevel"))
        for index in range(9):
            level = OxmlElement("w:lvl")
            level.set(qn("w:ilvl"), str(index))
            level.append(_value_element("w:start", 1))
            level.append(_value_element("w:numFmt", fmt))
            level.append(_value_element("w:lvlText", f"%{index + 1}." if ordered else ("•", "◦", "▪")[index % 3]))
            level.append(_value_element("w:lvlJc", "left"))
            properties = OxmlElement("w:pPr")
            indent = OxmlElement("w:ind")
            indent.set(qn("w:left"), str(720 * (index + 1)))
            indent.set(qn("w:hanging"), "360")
            properties.append(indent)
            level.append(properties)
            abstract.append(level)
        before = next((child for child in self.root if child.tag in {qn("w:num"), qn("w:numIdMacAtCleanup")}), None)
        if before is None:
            self.root.append(abstract)
        else:
            before.addprevious(abstract)
        self._abstract_ids[ordered] = abstract_id
        return abstract_id

    def _new_num(self, ordered):
        num = self.root.add_num(self._abstract_id(ordered))
        if ordered:
            for level in range(9):
                num.add_lvlOverride(ilvl=level).add_startOverride(1)
        return num.numId

    def apply(self, paragraph, block):
        level, ordered = block.level, block.is_numbered
        self._levels = {key: value for key, value in self._levels.items() if key <= level}
        state = self._levels.get(level)
        key = (ordered, block.list_id)
        if block.restart or state is None or state[:2] != key:
            parent = self._levels[max(self._levels)] if state is None and self._levels else None
            num_id = parent[2] if parent and parent[:2] == key and not block.restart else self._new_num(ordered)
            state = (*key, num_id)
            self._levels[level] = state
        properties = paragraph._p.get_or_add_pPr().get_or_add_numPr()
        properties.get_or_add_ilvl().val = level
        properties.get_or_add_numId().val = state[2]
