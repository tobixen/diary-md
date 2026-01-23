# Static Web Viewer Implementation Plan

## Problem with Previous Approach

The initial plan created a Python server (`diary-serve`), but this doesn't match the inventory-md pattern. Inventory-md uses:
- Static `search.html` file
- Fetches JSON data via `fetch()`
- Works offline - just open HTML in browser
- No server required

## Revised Approach: Static HTML Viewer

### Architecture

```
diary-md/
  viewer/
    diary-viewer.html          # Main HTML file (standalone)
    diary-viewer.js            # Shared diary-specific JS
    md-viewer-common.js        # Shared with inventory-md
    aliases.json               # Place name aliases

  example/
    diary.md                   # Example diary
    diary.json                 # Generated from markdown
    diary-viewer.html          # Copy of viewer (self-contained demo)
```

### Data Flow

```
1. User runs: diary-digest --diary diary.md export-json > diary.json
2. User opens diary-viewer.html in browser
3. JavaScript fetches diary.json
4. JavaScript fetches aliases.json (optional)
5. Renders interactive viewer
```

### Common Code Analysis

#### Comparing inventory-md and diary-md viewers:

**Shared Functionality:**
1. **Search with aliases** - Multi-language search using aliases.json
2. **Text filtering** - Real-time search across content
3. **Collapsible sections** - Expand/collapse hierarchies
4. **Export functionality** - Export filtered results
5. **Highlight search terms** - Visual feedback
6. **Responsive UI** - Mobile-friendly design

**Inventory-specific:**
- Tag filtering
- Image gallery
- Shopping list integration
- Container hierarchy

**Diary-specific:**
- Date range filtering
- Subsection filtering (Expenses, Notes, etc.)
- Expense summaries
- Date parsing from headers

**Proposed Shared Library: `md-viewer-common.js`**

```javascript
// md-viewer-common.js - Shared code for both projects

class MarkdownViewerBase {
    constructor(dataUrl, aliasesUrl) {
        this.dataUrl = dataUrl;
        this.aliasesUrl = aliasesUrl;
        this.data = null;
        this.aliases = {};
    }

    async loadData() {
        // Fetch JSON data
        const response = await fetch(this.dataUrl);
        this.data = await response.json();
    }

    async loadAliases() {
        // Fetch aliases (optional)
        try {
            const response = await fetch(this.aliasesUrl);
            this.aliases = await response.json();
        } catch (e) {
            console.log('No aliases file found, continuing without');
        }
    }

    getSearchTerms(query) {
        // Expand query with aliases
        const terms = [query.toLowerCase()];
        const aliasMatches = this.aliases[query.toLowerCase()];
        if (aliasMatches) {
            terms.push(...aliasMatches);
        }
        return terms;
    }

    highlightText(text, searchTerms) {
        // Highlight matching terms in text
        let highlighted = text;
        searchTerms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi');
            highlighted = highlighted.replace(regex, '<span class="highlight">$1</span>');
        });
        return highlighted;
    }

    exportResults(content, filename) {
        // Export content to file
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    // Collapsible section helpers
    initCollapsible(containerSelector) {
        document.querySelectorAll(`${containerSelector} .collapsible-header`).forEach(header => {
            header.addEventListener('click', () => this.toggleCollapse(header));
        });
    }

    toggleCollapse(headerElement) {
        headerElement.classList.toggle('collapsed');
        const content = headerElement.nextElementSibling;
        content.classList.toggle('collapsed');
    }
}

// CSS utilities
const commonStyles = `
    .highlight {
        background-color: #ffeb3b;
        padding: 2px 4px;
        border-radius: 2px;
    }

    .collapsible-header {
        cursor: pointer;
        user-select: none;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .collapsible-header:hover {
        color: #3498db;
    }

    .collapse-icon {
        transition: transform 0.3s;
        font-size: 12px;
    }

    .collapsible-header.collapsed .collapse-icon {
        transform: rotate(-90deg);
    }

    .collapsible-content {
        overflow: hidden;
        transition: max-height 0.3s ease-out;
    }

    .collapsible-content.collapsed {
        max-height: 0;
    }

    /* ... more shared styles ... */
`;
```

### Implementation Steps

#### Phase 1: Extract Common Code (Week 1)
- [ ] Create `md-viewer-common.js` library
- [ ] Extract shared search functionality
- [ ] Extract collapsible section logic
- [ ] Extract highlight and export functions
- [ ] Add comprehensive JSDoc comments
- [ ] Test in isolation

#### Phase 2: Update inventory-md (Week 1-2)
- [ ] Refactor search.html to use md-viewer-common.js
- [ ] Remove duplicate code
- [ ] Test all functionality still works
- [ ] Commit changes

#### Phase 3: Create diary-viewer.html (Week 2-3)
- [ ] Create standalone diary-viewer.html
- [ ] Extend MarkdownViewerBase for diary-specific features
- [ ] Implement date range filtering
- [ ] Implement subsection filtering
- [ ] Implement expense summary
- [ ] Add collapsible trip/date/section hierarchy

#### Phase 4: CLI Integration (Week 3)
- [ ] Add `export-json` subcommand to diary-digest
- [ ] Generate diary.json from markdown
- [ ] Copy viewer.html to output directory
- [ ] Test workflow end-to-end

#### Phase 5: Documentation (Week 4)
- [ ] User guide for diary-viewer
- [ ] Developer guide for md-viewer-common.js
- [ ] Update README with viewer instructions
- [ ] Create demo/example directory

## Detailed Specifications

### diary.json Format

```json
{
  "trips": [
    {
      "title": "Trip to Norway",
      "dates": [
        {
          "date": "2026-01-21",
          "dateString": "Tuesday 2026-01-21",
          "sections": {
            "Expenses": "- Coffee EUR:3.50\n- Train EUR:25.00",
            "Notes": "Had a great day"
          }
        }
      ]
    }
  ],
  "metadata": {
    "allSubsections": ["Expenses", "Notes", "Weather", "Maintenance"],
    "dateRange": {
      "start": "2026-01-21",
      "end": "2026-12-31"
    }
  }
}
```

### diary-viewer.html Features

**Search:**
- Real-time text search
- Multi-language via aliases.json
- Search across all content or specific sections
- Fuzzy matching (optional)

**Filters:**
- Date range picker (from/to)
- Subsection checkboxes (Expenses, Notes, etc.)
- Trip/event filter
- Combined filters (AND logic)

**View Modes:**
- Full: All content visible
- Headers: Show trip + date headers only
- Collapsed: All sections collapsed
- Custom: Expand only specific sections

**Expense Summary:**
- Parse EUR/USD/NOK/SEK/GBP amounts
- Sum by currency
- Show breakdown by category (if tagged)
- Filter by date range

**Export:**
- Export filtered results as Markdown
- Export as JSON
- Export expense summary as CSV

### CLI Commands

```bash
# Generate JSON for web viewer
diary-digest --diary diary.md export-json > diary.json

# Generate viewer with embedded data (single file)
diary-digest --diary diary.md export-viewer > diary-viewer.html

# Create viewer directory with all files
diary-digest --diary diary.md export-viewer-bundle -o viewer/
# Creates:
#   viewer/
#     index.html
#     diary.json
#     aliases.json
#     md-viewer-common.js
```

## File Organization

### Option A: Shared Library in Each Project
```
diary-md/
  viewer/
    md-viewer-common.js  # Copied from inventory-md
    diary-viewer.html
    diary-viewer.js

inventory-md/
  templates/
    md-viewer-common.js  # Original
    search.html
    search.js
```

**Pros:** Self-contained, no external dependencies
**Cons:** Code duplication, manual sync needed

### Option B: Separate NPM Package
```
md-viewer-common/
  package.json
  src/
    md-viewer-common.js
  dist/
    md-viewer-common.min.js
```

**Pros:** Single source of truth, versioned
**Cons:** Requires NPM, adds complexity

### Option C: CDN/Github Pages
```
Host md-viewer-common.js on GitHub Pages
Both projects fetch from:
https://tobixen.github.io/md-viewer/md-viewer-common.js
```

**Pros:** Always latest version, no duplication
**Cons:** Requires internet connection

**Recommendation**: Start with **Option A** (vendored), migrate to **Option B** if library grows.

## Testing Strategy

### Unit Tests (JavaScript)
- Test search with aliases
- Test collapsible functionality
- Test export functions
- Test highlight logic

### Integration Tests
- Test diary.json loading
- Test full viewer workflow
- Test all filters combined
- Test expense parsing

### Manual Testing
- Browser compatibility (Chrome, Firefox, Safari, Edge)
- Mobile responsiveness
- Offline functionality
- Large diary files (performance)

## Migration Path

1. Create md-viewer-common.js from inventory-md code
2. Test md-viewer-common.js in isolation
3. Update inventory-md to use it
4. Create diary-viewer.html using it
5. Add CLI export commands
6. Documentation and examples

## Success Criteria

- [ ] Works offline (file:// protocol)
- [ ] No server required
- [ ] Fast search (<100ms for 1000 entries)
- [ ] Mobile-responsive
- [ ] < 5s load time for typical diary
- [ ] Shared code between projects
- [ ] Browser compatibility (modern browsers)

## Open Questions

1. Should md-viewer-common.js use vanilla JS or a framework?
   - **Recommendation**: Vanilla JS to match inventory-md
2. How to handle very large diaries (10,000+ entries)?
   - **Recommendation**: Virtual scrolling, lazy loading
3. Should we support embedding diary content directly in HTML?
   - **Recommendation**: Yes, for single-file distribution
4. How to version the shared library?
   - **Recommendation**: Git submodule or simple copy with version tag

## Next Steps

1. Review this plan with user
2. Create md-viewer-common.js skeleton
3. Extract common code from inventory-md
4. Implement diary-viewer.html
5. Add export-json command

---

**Created**: 2026-01-23
**Status**: Draft for review
**Dependencies**: inventory-md refactor to markdown-it
