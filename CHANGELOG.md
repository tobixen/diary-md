# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- The web viewer is installed with the package: `diary-install-viewer DIR`
  copies it into a directory (`--page index.html` to name the page)

## [0.2.0] - 2026-11-06

### Added
- A static web viewer (`viewer/diary-viewer.html`), fed by the new
  `diary-digest export-web-json`: search with multi-language place aliases,
  date and section filters, collapsible chapters, days and sections, an
  expense summary, and links to a single day (`diary-viewer.html#2026-10-15`).
  HTML in the diary is shown as text, and links only go to http(s), mailto
  and relative URLs.  The viewer is not installed with the package; take it
  from the source repository (or the sdist).
- Public export: `diary-digest export-web-json --public POLICY` leaves out
  unreviewed days (after `reviewed_up_to` or before `public_from`),
  non-whitelisted sections and `<!-- private -->` fenced paragraphs, and
  replaces names from a people registry with quoted pseudonyms ("Alex"); a
  chapter keeps its intro, and the viewer says where it has entries not
  published yet.
  `diary-digest check-public` reports unclassified sections, sections
  missing from `allowable_subsections`, and unknown capitalised words and
  names in the body text
- Section names in another language count as the same section
  (`### Kostnader` as `### Expenses`, `### Vedlikehold` as `### Maintenance`)
- `diary-update` writes to Norwegian diaries too, and takes `--directory`
- Shell tab completion: `make install-completion`

### Changed
- `diary-update` writes to the `diary*.md` file in the current directory
  (or `--directory`) that covers the date, else `diary-YYYY.md` for the
  date's year, instead of always `~/solveig/diary-<current year>.md`
- `diary-reconcile` reads the `diary*.md` files in the current directory by
  default instead of a fixed list of the author's diaries
- `diary-digest --help` documents that the diary is read from stdin by default
- Diaries are parsed with markdown-it-py (new dependency): `#` lines in
  fenced code are no longer headings, a skipped heading level is no longer
  an error, and `export-json` sections carry `__paragraphs__` and
  `__list_items__` but no `__file_position__`

### Fixed
- `diary-update` no longer writes back-dated entries into the current
  year's file
- `diary-digest expenses` accepts `-` and `+` bullets as well as `*`
- `diary-digest find-all-subsections` no longer aborts on a malformed date
  header
- `diary-digest` reports diary parse errors as a message instead of a traceback

## [0.1.1] - 2026-01-22

### Fixed
- The release workflow fetches the full git history, so hatch-vcs finds
  the version and the package can be published

## [0.1.0] - 2026-01-22

### Added
- Initial release
- `diary-digest` command for generating digest summaries
- `diary-update` command for updating diary entries
- `diary-reconcile` command for reconciling entries
