* ✅ I'd like a web interface (javascript?) - **DONE**
  * ✅ Searchable with multi-language aliases (aliases.json)
  * ✅ Find unique subsections, filter by section type, expense summaries
  * ✅ Expand/collapse sections (3 levels: Trip → Date → Section)
  * ✅ Uses md-viewer-common.js (inventory-md's search.html duplicates parts of it inline)
  * ✅ Static HTML - no server required
  * See: viewer/README.md for usage

## Future Improvements

* Consider using markdown-it for rendering in the web viewer (currently uses simple converter)
* Add photo support in web viewer (like inventory-md)
* Export to PDF functionality
* Dark mode toggle
* Save filter preferences to localStorage

## Known bugs

* The web viewer has no fenced-code support: `#` lines inside a code block
  render as headings.  (HTML in the diary is shown as text since 2026-11-06.)
