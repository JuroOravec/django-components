import os
from pathlib import Path
from typing import Dict, NamedTuple, Literal, Optional

from django_components.util.loader import ComponentFileEntry

from django_vue.utils.vue_alpine2django import alpine2django_normalize
from django_vue.utils.vue_vue2alpine import vue2alpine_normalize


VueEntryStyleKind = Literal["scoped", "module", "regular"]


class VueEntrySection(NamedTuple):
    content: Optional[str]
    src: Optional[str]
    src_abs: Optional[str]
    lang: Optional[str]


class VueEntry(NamedTuple):
    name: str
    dot_path: str
    filepath: Path
    template: Optional[VueEntrySection]
    script: Optional[VueEntrySection]
    styles: Dict[VueEntryStyleKind, VueEntrySection]
    server: Optional[VueEntrySection]


def parse_vue_file(module: "ComponentFileEntry", vue_dir: Path) -> VueEntry:
    from selectolax.lexbor import parse_fragment

    filepath = module.filepath
    content = module.filepath.read_text()

    tree = parse_fragment(content)

    template: Optional[VueEntrySection] = None
    script: Optional[VueEntrySection] = None
    server: Optional[VueEntrySection] = None
    styles: Dict[VueEntryStyleKind, VueEntrySection] = {}

    for node in tree:
        if not node.tag:
            raise ValueError(f"Invalid HTML in {filepath}")

        # Skip comments
        if node.tag.startswith("-"):
            continue

        if node.tag == "template":
            if template is not None:
                raise ValueError(f"Multiple <{node.tag}> tags found in {filepath}")

            template_html = _process_html_template(node.html or "")

            src = node.attributes.get("src")
            lang = node.attributes.get("lang")

            template = VueEntrySection(
                src=_rel_src(module, src, vue_dir) if src else None,
                src_abs=_abs_src(module, src) if src else None,
                content=template_html if not src else None,
                lang=lang,
            )
            continue

        elif node.tag == "script":
            if script is not None:
                raise ValueError(f"Multiple <{node.tag}> tags found in {filepath}")

            src = node.attributes.get("src")
            lang = node.attributes.get("lang")

            script = VueEntrySection(
                src=_rel_src(module, src, vue_dir) if src else None,
                src_abs=_abs_src(module, src) if src else None,
                content=node.text(deep=True) if not src else None,
                lang=lang,
            )
            continue

        elif node.tag == "server":
            if server is not None:
                raise ValueError(f"Multiple <{node.tag}> tags found in {filepath}")

            src = node.attributes.get("src")
            lang = node.attributes.get("lang")

            server = VueEntrySection(
                src=_rel_src(module, src, vue_dir) if src else None,
                src_abs=_abs_src(module, src) if src else None,
                content=node.text(deep=True) if not src else None,
                lang=lang,
            )
            continue
    
        elif node.tag == "style":
            src = node.attributes.get("src")
            lang = node.attributes.get("lang")

            if "module" in node.attributes and "scoped" in node.attributes:
                raise ValueError(f"Single <style> tag cannot be both scoped and module at the same time in {filepath}")
            elif "module" in node.attributes:
                kind: VueEntryStyleKind = "module"
            elif "scoped" in node.attributes:
                kind = "scoped"
            else:
                kind = "regular"

            if kind in styles:
                raise ValueError(f"Multiple <style> tags of kind {kind} found in {filepath}")

            styles[kind] = VueEntrySection(
                content=node.text(deep=True) if not src else None,
                lang=lang,
                src=_rel_src(module, src, vue_dir) if src else None,
                src_abs=_abs_src(module, src) if src else None,
            )
            continue

        else:
            raise ValueError(f"Invalid tag {node.tag} in {filepath}. Additional tags are currently not supported.")
        
    return VueEntry(
        name=filepath.stem,
        dot_path=module.dot_path,
        filepath=filepath,
        template=template,
        script=script,
        styles=styles,
        server=server,
    )


def _process_html_template(template_html: str) -> str:
    # TODO
    from django_vue.utils.html_parser import Tag, parse_html
    def on_tag(html: str, tag: Tag) -> str:
        # TODO
        if tag.open_tag_start_index == 0:
            html = tag.unwrap(html)
        return html

    template_html = parse_html(template_html, on_tag, convert_interpolation=False, expand_shorthand_tags=False)

    template_html = vue2alpine_normalize(template_html)
    template_html = alpine2django_normalize(template_html)
    return template_html


def _rel_src(module: "ComponentFileEntry", src: str, vue_dir: Path) -> str:
    abs_path = _abs_src(module, src)
    rel_path = os.path.relpath(abs_path, vue_dir)
    return rel_path


def _abs_src(module: "ComponentFileEntry", src: str) -> str:
    if not (src.startswith("./") or src.startswith("../")):
        raise NotImplementedError(
            "Currently only relative paths are supported. Relative paths must start with './' or '../'"
        )
    return str((module.filepath.parent / src).resolve())
