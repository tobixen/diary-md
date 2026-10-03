"""
Adapter for markdown-it-py library.

Provides structured access to markdown content with proper handling of mixed content
(text + lists). Unlike markdown-to-json, this adapter preserves the distinction
between paragraphs and list items.

A section's ``content`` is its source text, verbatim, so nothing the parser
does not model (tables, code blocks, HTML, deep lists) is lost or reordered.
``paragraphs`` and ``list_items`` are a structured view of the common cases on
top of that.  Only ATX headings (``# ...``) at the top level start a section:
a setext underline (``---`` under a line of text) is a rule, not a heading.
"""
from dataclasses import dataclass, field
from typing import Any

from markdown_it import MarkdownIt


@dataclass
class MarkdownSection:
    """
    Represents a section of a markdown document (under a heading).

    Attributes:
        heading: The heading text (without # markers)
        level: Heading level (1 for H1, 2 for H2, etc.)
        content: Source text between the heading and the next heading, stripped
        paragraphs: Top-level paragraphs, in order
        list_items: Items of top-level lists, bullet or ordered (each a dict with
            'text', its paragraphs joined by a blank line, and a 'nested' list)
        subsections: Nested sections under this heading
        parent: Parent section (None for top-level)
    """
    heading: str
    level: int
    content: str = ''
    paragraphs: list[str] = field(default_factory=list)
    list_items: list[dict[str, Any]] = field(default_factory=list)
    subsections: list['MarkdownSection'] = field(default_factory=list)
    parent: 'MarkdownSection | None' = None


def parse_markdown_string(content: str) -> list[MarkdownSection]:
    """
    Parse a markdown string into structured sections.

    Args:
        content: Markdown content as string

    Returns:
        List of top-level MarkdownSection objects
    """
    md = MarkdownIt().disable('lheading')
    tokens = md.parse(content)
    # Split on \n only, as markdown-it does: str.splitlines() also breaks on
    # form feeds, U+2028 and the like, which would shift every token.map after them
    lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    sections: list[MarkdownSection] = []
    section_stack: list[MarkdownSection] = []
    # The section whose body is being read, and the line that body starts on
    current: MarkdownSection | None = None
    body_start = 0

    def close_body(end: int) -> None:
        if current is not None:
            body = lines[body_start:end]
            while body and not body[0].strip():
                body.pop(0)
            while body and not body[-1].strip():
                body.pop()
            current.content = '\n'.join(body)

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.type == 'heading_open' and token.level == 0:
            close_body(token.map[0])
            level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
            heading_text = ''
            if i + 1 < len(tokens) and tokens[i + 1].type == 'inline':
                heading_text = tokens[i + 1].content
                i += 1

            new_section = MarkdownSection(heading=heading_text, level=level)

            # Find appropriate parent based on heading level
            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()

            if section_stack:
                new_section.parent = section_stack[-1]
                section_stack[-1].subsections.append(new_section)
            else:
                sections.append(new_section)

            section_stack.append(new_section)
            current, body_start = new_section, token.map[1]

        elif token.type == 'paragraph_open' and token.level == 0:
            if i + 1 < len(tokens) and tokens[i + 1].type == 'inline':
                para_text = tokens[i + 1].content
                if section_stack:
                    section_stack[-1].paragraphs.append(para_text)
                i += 1

        elif token.type in _LIST_OPEN and token.level == 0:
            list_items, end_i = _parse_list(tokens, i)
            if section_stack:
                section_stack[-1].list_items.extend(list_items)
            i = end_i

        i += 1

    close_body(len(lines))
    return sections


_LIST_OPEN = ('bullet_list_open', 'ordered_list_open')


def _parse_list(tokens: list, start_i: int) -> tuple[list[dict[str, Any]], int]:
    """
    Parse a bullet or ordered list starting at start_i.

    Blocks in an item other than paragraphs and lists (code, HTML) are left
    out here; they are in the section's ``content``.

    Returns:
        Tuple of (list of item dicts, index of the list_close token)
    """
    items = []
    close = tokens[start_i].type.replace('_open', '_close')
    i = start_i + 1

    while i < len(tokens) and tokens[i].type != close:
        token = tokens[i]

        if token.type == 'list_item_open':
            item: dict[str, Any] = {'text': '', 'nested': []}
            paragraphs = []
            i += 1

            while i < len(tokens) and tokens[i].type != 'list_item_close':
                if tokens[i].type == 'paragraph_open':
                    if i + 1 < len(tokens) and tokens[i + 1].type == 'inline':
                        paragraphs.append(tokens[i + 1].content)
                        i += 1
                elif tokens[i].type in _LIST_OPEN:
                    nested_items, end_i = _parse_list(tokens, i)
                    item['nested'].extend(nested_items)
                    i = end_i
                i += 1

            item['text'] = '\n\n'.join(paragraphs)
            items.append(item)
        else:
            i += 1

    return items, i


def iter_all_sections(sections: list[MarkdownSection]) -> list[MarkdownSection]:
    """
    Flatten sections into a list of all sections (depth-first).

    Args:
        sections: List of top-level sections

    Returns:
        Flat list of all sections including nested ones
    """
    result = []
    for section in sections:
        result.append(section)
        result.extend(iter_all_sections(section.subsections))
    return result


def find_section(sections: list[MarkdownSection], heading: str) -> MarkdownSection | None:
    """
    Find a section by heading text (case-insensitive partial match).

    Args:
        sections: List of sections to search
        heading: Heading text to find

    Returns:
        MarkdownSection if found, None otherwise
    """
    heading_lower = heading.lower()
    for section in iter_all_sections(sections):
        if heading_lower in section.heading.lower():
            return section
    return None


def get_all_list_items(section: MarkdownSection, include_nested: bool = True) -> list[str]:
    """
    Get all list item texts from a section.

    Args:
        section: The section to extract items from
        include_nested: Whether to include nested list items

    Returns:
        List of item text strings
    """
    return _item_texts(section.list_items, include_nested)


def _item_texts(items: list[dict[str, Any]], include_nested: bool) -> list[str]:
    texts = []
    for item in items:
        texts.append(item['text'])
        if include_nested:
            texts.extend(_item_texts(item.get('nested', []), include_nested))
    return texts


def section_to_content_string(section: MarkdownSection) -> str:
    """
    A section's content as it stands in the source, without its subsections.

    Args:
        section: The section to convert

    Returns:
        The section's ``content``
    """
    return section.content
