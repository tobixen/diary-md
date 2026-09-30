* ✅ I'd like a web interface (javascript?) - **DONE**
  * ✅ Searchable with multi-language aliases (aliases.json)
  * ✅ Find unique subsections, filter by section type, expense summaries
  * ✅ Expand/collapse sections (3 levels: Trip → Date → Section)
  * ✅ Uses md-viewer-common.js shared with inventory-md
  * ✅ Static HTML - no server required
  * See: viewer/README.md for usage

## Future Improvements

* Consider using markdown-it for rendering in the web viewer (currently uses simple converter)
* Add photo support in web viewer (like inventory-md)
* Export to PDF functionality
* Dark mode toggle
* Save filter preferences to localStorage

## Known bugs

* The web viewer inserts diary text as raw HTML: `markdownToHtml` passes HTML
  and `javascript:` links through, section names and titles are interpolated
  unescaped, and search highlighting runs regexes over the finished markup
  (searching for "class" breaks it).  Escape before the markdown transforms,
  allow only http(s)/relative links, highlight text nodes only.
* The markdown-it adapter drops content: code blocks, tables and HTML blocks,
  all but the last paragraph of a multi-paragraph list item, lists nested
  deeper than two levels; paragraph/list order is lost, and a setext `---`
  underline makes a heading.  Capture the other block types (or raise).
* `diary-update` falls back to the current year's diary file when no file
  matches the target date; it should use the target date's year.
