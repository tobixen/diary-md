# Diary Web Viewer

Static HTML viewer for browsing and searching your markdown diary.

## Quick Start

1. **Install the viewer into a directory** (it comes with the package):
   ```bash
   diary-install-viewer ~/diary-site      # --page index.html to name the page
   cd ~/diary-site
   ```

2. **Generate JSON from your diary:**
   ```bash
   diary-digest --diary ~/diary-2026.md export-web-json > diary.json
   ```

3. **Open the viewer** through a local HTTP server (browsers do not let a page
   opened as a file fetch `diary.json`):
   ```bash
   python -m http.server 8000
   # Then open http://localhost:8000/diary-viewer.html (or the --page name)
   ```

## Files

The viewer itself lives in the package, `src/diary_md/viewer/`, and
`diary-install-viewer` copies it out:

- `diary-viewer.html` - Main viewer (standalone, no build required)
- `md-viewer-common.js` - Common viewer library (markdown, search, collapsing)

This directory holds examples to put beside it:

- `aliases.json` - Place name aliases for multi-language search
- `diary.json` - Diary data (generated from markdown), from `sample-diary.md`

## Features

### 🔍 Search
- Real-time text search across all content
- Multi-language place names via `aliases.json`
- Example: Searching "Moscow" also finds "Москва" and "Moskva"

### 📅 Date Filtering
- Filter by date range (from/to)
- Automatically parses dates from entry headers
- Link to a day with `diary-viewer.html#2026-01-21`: it is opened, highlighted and
  scrolled to

### 🏷️ Section Filtering
- Filter by subsection type (Expenses, Notes, Weather, etc.)
- Automatically detects all unique subsections
- Multiple sections can be selected

### 👁️ View Modes
- **Full**: All content visible
- **Headers Only**: Show trip and date headers, collapse sections
- **Collapsed**: Everything collapsed for quick overview

### 💰 Expense Summary
- Automatically parses expense amounts
- Supports: EUR, USD, NOK, SEK, GBP
- Shows totals by currency
- Example format: `EUR:15.50` or `SEK 350`

### 📤 Export
- Export filtered results to text file
- Preserves current filters and search

### 📊 Statistics
- Total entries count
- Visible entries (after filtering)
- All unique subsections found

## Generating diary.json

### Basic usage:
```bash
diary-digest --diary diary.md export-web-json > diary.json
```

### Pretty-printed (for debugging):
```bash
diary-digest --diary diary.md export-web-json --pretty > diary.json
```

### Expected diary format:
```markdown
# Trip to Norway

## Tuesday 2026-01-21

### Expenses
- Coffee EUR:3.50
- Train EUR:25.00

### Notes
Had a great day!

## Wednesday 2026-01-22

### Expenses
- Lunch EUR:15.00
```

## Customizing Aliases

Edit `aliases.json` to add your own place name aliases:

```json
{
  "göteborg": ["gothenburg", "gøteborg"],
  "царево": ["tsarevo", "tzarevo", "carevo"]
}
```

## Output Format

The viewer expects JSON in this format:

```json
{
  "trips": [
    {
      "title": "Trip to Norway",
      "intro": "Optional: the chapter's text before its first day.",
      "leftOut": ["before", "after"],
      "dates": [
        {
          "date": "2026-01-21",
          "dateString": "Tuesday 2026-01-21",
          "sections": {
            "Expenses": "- Coffee EUR:3.50\n- Train EUR:25.00",
            "Notes": "Had a great day!"
          }
        }
      ]
    }
  ]
}
```

`leftOut` appears only in a public export (`--public`), and names the sides
where days were left out as not yet reviewed; the viewer shows a note there.

## Offline Usage

The viewer works completely offline:

1. Generate `diary.json` from your markdown
2. Serve the directory locally and open `diary-viewer.html` from it
3. No internet connection required

**Note:** Browsers block `fetch()` from `file://` URLs, so open it through a local HTTP server:

```bash
# Python 3
python -m http.server 8000

# or using npm
npx http-server
```

## Browser Compatibility

Tested on:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

Requires ES6+ support (all modern browsers).

## Development

### Common Code

`md-viewer-common.js` started out shared with
[inventory-md](https://github.com/tobixen/inventory-md), but is now
maintained here only; inventory-md's `search.html` carries its own
inline copies of some of its functions.

### Modifying the Viewer

To modify the viewer:

1. Edit `src/diary_md/viewer/diary-viewer.html` or `md-viewer-common.js`
2. Test locally (`node tests/js/viewer_escape.test.js` covers the escaping)
3. Commit changes

## Troubleshooting

### "Failed to load diary.json"
- Make sure `diary.json` is in the same directory as `diary-viewer.html`
- Or use a local HTTP server to avoid CORS issues

### Search not working with aliases
- Check that `aliases.json` exists and is valid JSON
- Viewer works without aliases, they're optional

### Expenses not showing
- Check expense format: `EUR:15.50` or `EUR 15.50` or `15.50 EUR`
- Must be in a section named "Expenses" (case-sensitive)

### Collapsible sections not working
- Make sure JavaScript is enabled in your browser
- Check browser console for errors

## License

AGPL-3.0-or-later (same as diary-md)

## Related Projects

- [diary-md](https://github.com/tobixen/diary-md) - Markdown diary CLI tools
- [inventory-md](https://github.com/tobixen/inventory-md) - Markdown inventory system
