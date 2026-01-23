# Web Interface Implementation Plan for diary-md

## Executive Summary

This document outlines a plan to create a JavaScript-based web interface for diary-md with search, filtering, and collapsible section capabilities, leveraging code and patterns from the inventory-md project.

## Research Findings

### 1. Existing JavaScript Markdown Libraries (2026)

#### Top Candidates:

**[Marked](https://github.com/markedjs/marked)** (32.1k ⭐)
- Most popular Markdown parser for JavaScript
- GitHub-flavored Markdown support
- Fast, lightweight, extensible
- **Recommendation**: Use for parsing markdown to HTML

**[markdown-it](https://github.com/markdown-it/markdown-it)** (17.4k ⭐)
- CommonMark specification compliant
- Extensive plugin ecosystem
- `markdown-it-collapsible` plugin available for native collapse syntax
- More features but heavier than Marked

**Decision**: Use **Marked** for simplicity and performance. Collapsible sections can be handled via HTML `<details>` tags or custom JavaScript.

### 2. Inventory-md Project Analysis

**Location**: `/home/tobias/inventory-system` (GitHub: tobixen/inventory-md)

**Key Learnings**:

#### Shared Components Identified:

1. **Markdown Parser** (`parser.py` - 782 lines)
   - Parses markdown with metadata (key:value format)
   - Hierarchical structure support
   - Image/photo discovery
   - Tag parsing and expansion

2. **Alias System** (`aliases.json`)
   - Multi-language search support
   - Bidirectional mappings (Göteborg ↔ Gothenburg ↔ Gøteborg)
   - Perfect for place names in diary entries

3. **Web Interface** (`search.html` - 2,421 lines)
   - Vanilla JavaScript (no framework dependencies)
   - Real-time search and filtering
   - Collapsible sections
   - Tag-based filtering
   - Image gallery support
   - Mobile-responsive design

#### Architecture Pattern:
```
Markdown file → Python parser → JSON → Static HTML + JavaScript → Interactive UI
```

## Proposed Architecture for diary-md Web Interface

### Phase 1: Core Infrastructure (Reusable md2json Library)

Create a shared library that both projects can use:

**Package name**: `md2json` or `markdown-utils`

**Core features**:
- Generic markdown parser with metadata support
- Configurable section/subsection extraction
- Hierarchical structure handling
- Alias/translation system
- Output to JSON format

**Structure**:
```python
# md2json/
#   __init__.py
#   parser.py        # Core markdown parsing logic
#   metadata.py      # Metadata (key:value) extraction
#   aliases.py       # Alias system for multi-language support
#   hierarchical.py  # Hierarchy management (headers/subheaders)
#   cli.py          # CLI for converting md → json
```

**Benefits**:
- DRY: Don't Repeat Yourself
- Both diary-md and inventory-md can use it
- Easier to maintain and test
- Can be published to PyPI separately

### Phase 2: Diary-Specific Parser Extension

Extend md2json for diary-specific features:

```python
# In diary_md/web.py or similar:
from md2json import MarkdownParser

class DiaryParser(MarkdownParser):
    """Diary-specific markdown parser"""

    def parse_date_headers(self):
        """Extract date-based headers (## Tuesday 2026-01-20)"""
        pass

    def parse_subsections(self):
        """Extract 3rd level headers (### Expenses, ### Notes)"""
        pass

    def parse_expenses(self):
        """Extract expense metadata (EUR 15.50, category:groceries)"""
        pass

    def to_web_json(self):
        """Generate JSON optimized for web interface"""
        pass
```

### Phase 3: Web Interface

#### Technology Stack:

- **No build system required** - Vanilla HTML/CSS/JavaScript
- **Marked.js** - Markdown rendering
- **Optional**: Fuse.js for fuzzy search
- **Optional**: DOMPurify for XSS protection if rendering user markdown

#### File Structure:
```
diary-md/
  src/diary_md/
    templates/
      search.html      # Main web interface
      assets/
        styles.css     # CSS (can be inline or separate)
        app.js         # Main application logic
        search.js      # Search and filter logic
        aliases.json   # Place name aliases
```

#### Features Breakdown:

**1. Search Functionality**
- Real-time text search across all diary entries
- Search in multiple languages using aliases
- Fuzzy matching for typos
- Search within specific subsections only
- Date range filtering

**2. Filtering**
- Filter by subsection type (Expenses, Notes, Weather, etc.)
- Filter by date/date range
- Filter by trip/event name (level 1 headers)
- Tag-based filtering (if tags are added)

**3. Collapsible Sections**
```javascript
// Expansion levels:
// - Collapsed: Show only level 1 headers (trip names)
// - Level 2: Show trip + date headers
// - Level 3: Show trip + dates + subsections
// - Expanded: Show all content

// Click handlers for each header level
```

**4. Expense Summaries**
- Clickable "Show Expenses" button
- Displays expense totals by currency
- Expense breakdown by category
- Date range selection for expense period

**5. Export Options**
- Export filtered/searched results as markdown
- Export as JSON
- Export expense summary as CSV

#### UI Mockup:

```
┌─────────────────────────────────────────────────┐
│  📔 Diary-MD Viewer                             │
├─────────────────────────────────────────────────┤
│  🔍 Search: [___________________________] 🔎    │
│  📅 From: [2026-01-01] To: [2026-12-31]        │
│  🏷️  Sections: [Expenses] [Notes] [Weather]    │
│  ⚙️  View: [●Collapsed ○Headers ○Full]          │
├─────────────────────────────────────────────────┤
│  📊 [Show Expense Summary]                      │
├─────────────────────────────────────────────────┤
│  ▶ Trip to Norway (Jan 2026)                    │
│    ▶ Tuesday 2026-01-21                         │
│      ▶ Expenses: EUR 45.50                      │
│      ▶ Notes: Hotel check-in at 3pm             │
│    ▶ Wednesday 2026-01-22                       │
│      ...                                         │
│  ▶ Summer Vacation (July 2026)                  │
│    ...                                           │
└─────────────────────────────────────────────────┘
```

### Phase 4: CLI Integration

Add web server capabilities to diary-md CLI:

```python
# In diary_md/cli/serve.py
import http.server
from pathlib import Path

@cli.command()
@click.option('--port', default=8000, help='Port to serve on')
@click.option('--diary', type=click.Path(exists=True), help='Path to diary markdown file')
def serve(port, diary):
    """Start local web server for diary viewer"""
    # 1. Parse diary to JSON
    # 2. Copy search.html to temp directory
    # 3. Inject JSON data into page
    # 4. Start HTTP server
    # 5. Open browser automatically
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Create md2json library structure
- [ ] Port common parsing logic from inventory-md
- [ ] Implement alias system
- [ ] Add tests for parser
- [ ] Publish md2json to PyPI

### Phase 2: Diary Parser (Week 2-3)
- [ ] Extend md2json for diary-specific features
- [ ] Parse date headers correctly
- [ ] Extract subsections
- [ ] Parse expense metadata
- [ ] Generate web-optimized JSON format
- [ ] Add tests

### Phase 3: Web Interface (Week 3-5)
- [ ] Create base HTML template (adapt from inventory-md)
- [ ] Implement search functionality
  - [ ] Text search
  - [ ] Multi-language with aliases
  - [ ] Date filtering
  - [ ] Section filtering
- [ ] Implement collapsible sections
  - [ ] Multiple expansion levels
  - [ ] Smooth animations
  - [ ] Remember state in localStorage
- [ ] Add expense summary view
- [ ] Mobile-responsive design
- [ ] Add export functionality

### Phase 4: CLI Integration (Week 5-6)
- [ ] Add `diary-md serve` command
- [ ] Auto-generate JSON on serve
- [ ] Add file watcher for live reload (optional)
- [ ] Add `--export-json` option
- [ ] Add `--generate-html` option for static site

### Phase 5: Polish & Documentation (Week 6-7)
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Accessibility (WCAG compliance)
- [ ] Documentation
  - [ ] User guide
  - [ ] Developer guide for md2json
  - [ ] API documentation
- [ ] Screenshot/demo video

## Shared Code Strategy

### Option A: Separate md2json Package
```
# Three separate packages:
pip install md2json         # Shared core
pip install diary-md        # Depends on md2json
pip install inventory-md    # Depends on md2json
```

**Pros**:
- Clean separation
- Each project stays lightweight
- Easy to version independently

**Cons**:
- More overhead to maintain
- Another package to publish

### Option B: Vendored Shared Code
```
# Copy shared code between projects
diary-md/src/diary_md/shared/
inventory-md/src/inventory_md/shared/
```

**Pros**:
- Self-contained projects
- No external dependency

**Cons**:
- Code duplication
- Changes need to be synced manually

**Recommendation**: **Option A** - The overhead is worth it for long-term maintainability.

## Alias System for Place Names

Based on inventory-md's `aliases.json`, create `place_aliases.json`:

```json
{
  "göteborg": ["gothenburg", "gøteborg", "goteborg"],
  "gothenburg": ["göteborg", "gøteborg"],
  "царево": ["tsarevo", "tzarevo", "carevo"],
  "tsarevo": ["царево", "tzarevo", "carevo"],
  "москва": ["moscow", "moskva"],
  "moscow": ["москва", "moskva"],
  "københavn": ["copenhagen", "kobenhavn"],
  "copenhagen": ["københavn", "kobenhavn"]
}
```

**Usage**: When searching for "Moscow", also match entries containing "Москва" or "Moskva".

## Technical Considerations

### Performance
- For large diaries (>1000 entries), implement:
  - Lazy loading of content
  - Virtual scrolling for long lists
  - Web Workers for search indexing
  - IndexedDB caching

### Security
- If allowing user markdown input:
  - Use DOMPurify to sanitize HTML
  - Implement CSP headers
- For file serving:
  - Restrict to specific directories
  - Validate file paths

### Accessibility
- Keyboard navigation
- ARIA labels for screen readers
- High contrast mode
- Font size controls

## Migration Path from Inventory-md

1. Extract common code from inventory-md
2. Create md2json package
3. Update inventory-md to use md2json
4. Implement diary-md web interface using md2json
5. Share improvements back to both projects

## Success Metrics

- [ ] Can search diary entries in <100ms (for typical diary size)
- [ ] Supports multi-language place name search
- [ ] Works offline (static HTML + JSON)
- [ ] Mobile-responsive
- [ ] <5 second load time for typical diary
- [ ] Passes WCAG 2.1 AA accessibility
- [ ] Test coverage >80%

## Next Steps

1. **User Validation**: Confirm this plan aligns with your needs
2. **Prioritization**: Decide which features are MVP vs nice-to-have
3. **Timeline**: Adjust phases based on available time
4. **Resources**: Determine if you want to work on this or delegate

## Questions to Resolve

1. Should md2json be a separate package or vendored code?
2. What's the priority: search, expenses, or collapsible sections?
3. Do you need editing capabilities in the web UI? (inventory-md has this)
4. Should the web UI work offline or require a server?
5. Any specific design preferences or examples you like?

---

**Created**: 2026-01-23
**Status**: Draft for review
**Next Action**: Review with user and adjust based on feedback
