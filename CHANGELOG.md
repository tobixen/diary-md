# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Public export: `diary-digest export-web-json --public POLICY` leaves out
  unreviewed days (after `reviewed_up_to` or before `public_from`),
  non-whitelisted sections and `<!-- private -->` fenced paragraphs, and
  replaces names from a people registry; the viewer says where a chapter
  has entries not published yet.  `diary-digest check-public` reports
  unclassified sections, sections missing from `allowable_subsections`, and
  unknown capitalised words and names in the body text
- `export-web-json` exports a chapter's intro, and the viewer shows it

### Fixed
- The web viewer shows HTML in the diary as text instead of interpreting it,
  links only to http(s), mailto and relative URLs, and search highlighting no longer
  breaks the page when the search term matches markup ("class")
- `diary-update` falls back to the target date's year file (`diary-YYYY.md`)
  rather than the current year's when no diary file covers the date
- `diary-digest expenses` accepts `-` and `+` bullets as well as `*`
- `diary-digest find-all-subsections` and `export-web-json` no longer abort on a
  malformed date header; date parsing is now deferred to the commands needing it
- `diary-digest` reports diary parse errors as a message instead of a traceback

### Changed
- `diary-digest --help` now documents that the diary is read from stdin by default
- Migrated build system from setuptools to Hatch with hatch-vcs
- Added ruff for linting
- Added pre-commit hooks
- Added GitHub Actions for CI/CD

## [0.1.0] - 2025-01-20

### Added
- Initial release
- `diary-digest` command for generating digest summaries
- `diary-update` command for updating diary entries
- `diary-reconcile` command for reconciling entries
