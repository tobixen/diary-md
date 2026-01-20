# diary-md

Tools for managing markdown-based diary entries.

## History

At some point I started writing the "captains log" - and in the aftermath I'm very greatful for this, I have one source of truth where I can look up where I've been, what I've been doing, how the money and time was spent as well as personal notes.  There are lots of memories in this diary, and it's easy to edit it by a text editor.  As the diary grew, some few scripts grew around it ... one script for parsing the file and summing up the expenses recorded, validate the records and filter out a specific section, another script for reconciliate the expenses I've written down in the diary with account statements from my credit card providers, yet another script for automatically injecting expenses into the report.  I decided to refactor everything and consolidate all the scripts.  While I don't really expect anyone else than myself to use this package, it's in my nature to publish it as open source!

# AI-generated docs belong

## Installation

```bash
pip install -e ~/diary-md
```

## Commands

### diary-digest

Analyze and extract information from markdown diary files.

```bash
# Summarize expenses
diary-digest --diary ~/solveig/diary-2026.md expenses

# Extract specific sections
diary-digest --diary ~/solveig/diary-2026.md select-subsection --section Maintenance

# Filter by date range
diary-digest --diary ~/solveig/diary-2026.md --from 2026-01-01 --to 2026-01-31 expenses
```

### diary-update

Add entries to diary files.

```bash
# Add an expense
diary-update --line "EUR 7.10 - groceries - Lidl (milk, bread)"

# Add expense with structured options
diary-update --amount 7.10 --description "Lidl (milk, bread)"

# Add to a different section
diary-update --section maintenance --line "Fixed the rudder bearing"

# Add for a specific date
diary-update --date 2026-01-20 --amount 50 --type fuel --description "diesel"

# Commit changes to git
diary-update --amount 7.10 --description "Lidl" --commit
```

### diary-reconcile

Reconcile bank expenses with diary entries.

```bash
# Reconcile N26 CSV export
diary-reconcile ~/tmp/n26.csv

# Specify format
diary-reconcile --format wise ~/tmp/wise.csv

# Dry run to see matches
diary-reconcile --dry-run ~/tmp/n26.csv

# Use specific diary file
diary-reconcile --diary ~/solveig/diary-2026.md ~/tmp/n26.csv
```

## Supported Bank Formats

- `n26`: N26 CSV export
- `wise`: Wise (TransferWise) CSV export
- `banknorwegian`: Bank Norwegian XLSX export
- `remember`: Remember credit card JSON export

## Development

```bash
# Install with dev dependencies
pip install -e "~/diary-md[dev]"

# Run tests
pytest ~/diary-md/tests/
```
