"""Tests for the markdown-it-py adapter module."""
from diary_md import md_adapter


class TestParseMarkdownString:
    """Tests for parse_markdown_string function."""

    def test_simple_structure(self):
        """Test parsing simple heading structure."""
        content = """# Main

## Sub1

Content here.

## Sub2

More content.
"""
        sections = md_adapter.parse_markdown_string(content)

        assert len(sections) == 1
        assert sections[0].heading == 'Main'
        assert len(sections[0].subsections) == 2
        assert sections[0].subsections[0].heading == 'Sub1'
        assert sections[0].subsections[1].heading == 'Sub2'

    def test_paragraphs(self):
        """Test paragraph extraction."""
        content = """# Section

First paragraph.

Second paragraph.
"""
        sections = md_adapter.parse_markdown_string(content)

        assert sections[0].paragraphs == ['First paragraph.', 'Second paragraph.']

    def test_list_items(self):
        """Test list item extraction."""
        content = """# Section

* Item 1
* Item 2
* Item 3
"""
        sections = md_adapter.parse_markdown_string(content)

        assert len(sections[0].list_items) == 3
        assert sections[0].list_items[0]['text'] == 'Item 1'
        assert sections[0].list_items[1]['text'] == 'Item 2'
        assert sections[0].list_items[2]['text'] == 'Item 3'

    def test_nested_lists(self):
        """Test nested list item extraction."""
        content = """# Section

* Main item
  * Nested item 1
  * Nested item 2
* Another main item
"""
        sections = md_adapter.parse_markdown_string(content)

        assert len(sections[0].list_items) == 2
        assert sections[0].list_items[0]['text'] == 'Main item'
        assert len(sections[0].list_items[0]['nested']) == 2
        assert sections[0].list_items[0]['nested'][0]['text'] == 'Nested item 1'

    def test_mixed_content(self):
        """Test mixed paragraphs and lists."""
        content = """# Section

First paragraph.

* Item 1
* Item 2

Second paragraph.

* Item 3
"""
        sections = md_adapter.parse_markdown_string(content)

        assert len(sections[0].paragraphs) == 2
        assert sections[0].paragraphs[0] == 'First paragraph.'
        assert sections[0].paragraphs[1] == 'Second paragraph.'
        assert len(sections[0].list_items) == 3

    def test_diary_structure(self):
        """Test parsing typical diary structure."""
        content = """# Summer Trip 2026

## Monday 2026-01-20 - Oslo

### Expenses

* EUR 15.72 - groceries - Lidl
* EUR 8.50 - transport - bus

### Notes

Had a great day.
"""
        sections = md_adapter.parse_markdown_string(content)

        assert len(sections) == 1
        trip = sections[0]
        assert trip.heading == 'Summer Trip 2026'
        assert len(trip.subsections) == 1

        day = trip.subsections[0]
        assert 'Monday 2026-01-20' in day.heading
        assert len(day.subsections) == 2

        expenses = day.subsections[0]
        assert expenses.heading == 'Expenses'
        assert len(expenses.list_items) == 2
        assert 'EUR 15.72' in expenses.list_items[0]['text']


class TestIterAllSections:
    """Tests for iter_all_sections function."""

    def test_flattens_hierarchy(self):
        """Test that sections are flattened correctly."""
        content = """# A

## B

### C

## D
"""
        sections = md_adapter.parse_markdown_string(content)
        all_sections = md_adapter.iter_all_sections(sections)

        headings = [s.heading for s in all_sections]
        assert headings == ['A', 'B', 'C', 'D']


class TestFindSection:
    """Tests for find_section function."""

    def test_finds_by_partial_match(self):
        """Test finding section by partial heading match."""
        content = """# Trip

## Monday 2026-01-20 - Oslo

Content
"""
        sections = md_adapter.parse_markdown_string(content)
        found = md_adapter.find_section(sections, '2026-01-20')

        assert found is not None
        assert '2026-01-20' in found.heading

    def test_case_insensitive(self):
        """Test case-insensitive search."""
        content = """# MySection

Content
"""
        sections = md_adapter.parse_markdown_string(content)
        found = md_adapter.find_section(sections, 'mysection')

        assert found is not None
        assert found.heading == 'MySection'


class TestGetAllListItems:
    """Tests for get_all_list_items function."""

    def test_gets_expense_lines(self):
        """Test getting expense lines from diary section."""
        content = """# Trip

## Monday 2026-01-20

### Expenses

* EUR 15.72 - groceries - Lidl
* EUR 8.50 - transport - bus
"""
        sections = md_adapter.parse_markdown_string(content)
        expenses_section = md_adapter.find_section(sections, 'Expenses')

        items = md_adapter.get_all_list_items(expenses_section)
        assert len(items) == 2
        assert 'EUR 15.72' in items[0]
        assert 'EUR 8.50' in items[1]


class TestSectionToContentString:
    """Tests for section_to_content_string function."""

    def test_recreates_content_format(self):
        """Test that content string matches original format."""
        content = """# Section

Some paragraph.

* Item 1
* Item 2
"""
        sections = md_adapter.parse_markdown_string(content)
        content_str = md_adapter.section_to_content_string(sections[0])

        assert 'Some paragraph.' in content_str
        assert '* Item 1' in content_str
        assert '* Item 2' in content_str
