# Diary Web Viewer

Static HTML viewer for browsing and searching your markdown diary.

## Quick Start

1. **Generate JSON from your diary:**
   ```bash
   diary-digest --diary ~/diary-2026.md export-web-json > diary.json
   ```

2. **Open the viewer:**
   - Simply open `diary-viewer.html` in your web browser
   - Or use a local HTTP server to avoid CORS issues:
     ```bash
     python -m http.server 8000
     # Then open http://localhost:8000/diary-viewer.html
     ```

## Files

- `diary-viewer.html` - Main viewer (standalone, no build required)
- `md-viewer-common.js` - Shared library (synced from inventory-md)
- `aliases.json` - Place name aliases for multi-language search
- `diary.json` - Your diary data (generated from markdown)

## Features

### 🔍 Search
- Real-time text search across all content
- Multi-language place names via `aliases.json`
- Example: Searching "Moscow" also finds "Москва" and "Moskva"

### 📅 Date Filtering
- Filter by date range (from/to)
- Automatically parses dates from entry headers

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

## Offline Usage

The viewer works completely offline:

1. Generate `diary.json` from your markdown
2. Open `diary-viewer.html` in any web browser
3. No internet connection required

**Note:** Some browsers block `fetch()` from `file://` URLs. If you see errors, use a local HTTP server:

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

### Shared Code

`md-viewer-common.js` is shared with [inventory-md](https://github.com/tobixen/inventory-md).

**Source of truth:** inventory-md
**Sync:** Automatic via git hook

See `../docs/SHARED_CODE.md` for details.

### Modifying the Viewer

To modify the viewer:

1. Edit `diary-viewer.html`
2. Test locally
3. Commit changes

To modify shared code:

1. Make changes in inventory-md
2. Commit there (auto-syncs to diary-md)

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
