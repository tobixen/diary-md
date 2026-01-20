# diary-md

Tools for managing markdown-based diary entries.  Used for my "captains log" where I write about the life on board my sail boat, as well as my personal Oslo diary from when I'm on land.

The practical usage guides are AI-written and found further below.  I will perhaps reorganize this file a bit one day.

## History

At some point I started writing the "captains log" - and in the aftermath I'm very greatful for this, I have one source of truth where I can look up where I've been, what I've been doing, how the money and time was spent as well as personal notes.  Maintenance ... when was this equipment replaced/serviced last time, it's useful to be able to look itup.  There are also lots of memories in this diary, and it's easy to edit it by a text editor.  I recently decided to create another diary also for my life on land in Oslo.

As the diaries have been growing, some few scripts grew around it ... one script for parsing the file and summing up the expenses recorded, validate the records and filter out a specific section, another script for reconciliate the expenses I've written down in the diary with account statements from my credit card providers, yet another script for automatically injecting expenses into the report.  I decided to refactor everything and consolidate all the scripts.  While I don't really expect anyone else than myself to use this package, it's in my nature to publish it as open source!  (there may still be some hard coded paths etc in the source code, but I'll get to it ... one day).

## Diary format

### Top-level headline(s)

Every file has one or more top-level headlines.  Think of it as a chapter title of your life.  Like "Selling the house", "Sailing from Spain to Greece", etc.  My `diary-202401.md` starts with `# Fist trip to Greece`.  It's perfectly fine to write some brief summary on what the section includes right after the headline.

* The 2nd level section titles starts with a date mark.  It doesn't always fit my rythm ... sometimes an "event" extends beyond several days (like a multi-day sailing voyage without stops) and certainly it often crosses the midnight border.  In the "Captains log" the day section header also contains the destinations.  The date marks also contains the weekday.  So my `diary-202401.md` continues with `## Monday 2024-01-01 Dubrovnik old harbour (old town) - Cavtatska luka - Cavtat - Adriatic`.  We arrived to Greece at 2024-01-03, so for 2024-01-02 the section title is simply `## Tuesday 2024-01-02 Adriatic`.

* After the 2nd level section title, I do have some free text explanation of the day.  Here is from 2024-01-01:

> We were out at the street by midnight, when the fireworks were over we went back to the boat.  We were sitting in the boat for an hour, eating the panettone and tasting the local alcohol I bought earlier in the day (only one small shots glass), before we left.  The panettone was too big for us, and I was like "this is nothing to save, let's finish it up", so I ate a lot of it - too much.

> Only six nautical miles from the old harbour to our Cavtat anchorage, but it had become quite windy.  We had checked the wind forecast for getting to Dubrovnik carefully, and the rain forecast for the hours we were going to stay there (promised rain from 22 ... but no rain observed!), but we hadn't studied the wind forecast for the return.  It was windy and choppy.  With all the panettone and the small shot of alcohol, it was sufficient that I felt a bit sea sick.

> Six small nautic miles, headwind, low power on the batteries, not much hot water on the hot water tank, relatively cold boat, crew that hadn't slept for 20 hours, the best option would probably have been to go by engine on relatively high RPM.  But the crew wanted to sail and do tacking, and who am I to deny them that, so that's what we got.  I think the final tack eventually would have gotten us into calmer water, but no ... at that point the crew was fed up tacking and started the engine.  We arrived at around five ... I was dead tired and only wanted to sleep ... and still I spent half an hour hacking on my anchor drifting alarm system after our arrival.

> After sleeping a bit (a bit more than planned), we decided go back to Cavtat for a final visit to Croatian civilisation - throwing garbage and such - and then we headed out into the Adriatic - first tack going like 90 degrees out from the coast.  Wind direction changed a bit and wanted to push us north, so we tacked.

* After that, multiple 3rd level sections may follow.  They follow a pattern, the same 3rd-level sections may appear on any day.  For the Captain's Log I have one section for maintenance, another for expenses, sometimes I have "Meters and measurements" (manual readings of various meters) and "Times and positions" (automatically added based on my tracking scripts)

## Other thoughts on how to arrange the diary

### Multi-file approach

The package is designed to be able to process multiple files.  It's useful both for **rolling big files** and for **keeping different domains in different files**.

I started with the file name format `diary-yyyydd.md`, but I've eventually settled on `diary-yyyy.md`.   I didn't think much about it back when I created the first file, but there are some practical considerations when it comes to rolling the logs.  Probably, the biggest concern is that handling a file that is many megabytes big in an editor is sub-optimal, so it must be rolled some times.  Another concern is that one may want to change the diary format itself (my firs files ends with `.txt`).  I don't like rolling the files too often, because having the data spread over lots of different files may make it harder to access old information.  I'm against having firm rules on *when* it should be rolled - if one happens to be in the middle of a new-years party at the new years eve, then that's one event - it makes no sense to log the activities before and after midnight into two separate files.

The other dimension to it, is having multiple domains or multiple permissions.  Like, my diaries started with the "captains log".  Although it has grown into more of a personal diary than the ships logbook, I still want it to be sharable.  If I leave the boat with crew or family on board, I would like somebody else to take over updating the diary.  If I want to journal some very private thoughts that cannot be posted on the Internet, then I should write than in another file.  (I thought about this some decades ago, I also wanted to write a journal back then, but then I was considering to use tags to mark out what's private and make it possible to extract a public blog using scripts.  Well.  Everything considered, it's probably better to keep those things in different files).  Now I'm having a separate diary for my life on land, when I'm not on the boat.

The year/month in the filename *indicates* the start of the file - there is no obligation to wrap it up and start with a new diary file just because the month/year changes.  My `diary-202401.md` file was wrapped up by the end of 2025 because of the bloated size of it.  My diary-2026.md starts at 2025-12-31.  I consider it more appropriate to do the rolling when a new "life chapter" opens up than at specific timestamps.

### Automatically added information

I've been pushing some automatically updated data into the diary from time to time - like information created by a script parsing GPS-coordinates from the tracker.  It may make sense to have a single source of relevant information.  However, if the source data is the authorative source of truth, then I think it's best not to duplicate data.  I think some conditions should be fulfilled before it makes sense to automatically add data to the diary
 * It must not be too much of it, it should not be overwhelming - if it's too much information, it's better to save it to a separate file.
 * The data mus tbe suitable to be amended/curated.  For credit card transactions I choose what transactions are relevant, I add descriptions and I categorize them.  For the script checking my GPS coordinates and deducting where I've been stopping and for how long, I remove data if it's wrong ("I didn't stop in the middle of the sea, it was just the wind stopping blowing"), and I add place names.  In those cases the information in the diary becomes the "single source of truth".  If the source data is always correct and equally relevant, it makes no point copying it, then it's better to keep the source as the "single source of truth".
 
In my "captains log" entry for 2024-01-01, I have this section included - it's generated by my script, but clearly hand-edited:

```
* 2024-01-01T001424 UTC: departed from mooring after 3:35:00
* 2024-01-01T001444 UTC: moved for 2:36:53, line distance 5.8nm, sailed distance 9.4nm (-14.56%), avg speed 3.589506267011826, vmg 2.2 kts
* 2024-01-01T025137 UTC: stop or standstill (anchor chain got jammed) at 42.581381666666665,18.214623333333332 for 0:03:01
* 2024-01-01T025438 UTC: drifted for 0:17:41, line distance 398m, vmg 0.7 kts
* 2024-01-01T031219 UTC: stop or standstill (resolved anchor chain problems) at 42.58323166666667,18.210108333333334) for 0:02:00
* 2024-01-01T031419 UTC: moved for 0:16:02, line distance 443m, vmg 0.9 kts
* 2024-01-01T033021 UTC: arrived at anchorage 42.581135,18.213775 (Cavtat, Cavtatska luka)
* 2024-01-01T104615 UTC: departed from anchorage after 7:15:54
* 2024-01-01T104615 UTC: moved for 0:03:30, line distance 209m, vmg 1.9 kts
* 2024-01-01T104945 UTC: arrived at mooring 42.581806666666665,18.21660333333333 (Cavtat, taxi quay)
* 2024-01-01T112527 UTC: departed from mooring after 0:35:42
* 2024-01-01T112547 UTC: moved for 1 day, 19:09:58, line distance 165.0nm, sailed distance 184.5nm (+-0.36%), avg speed 4.2 kts, vmg 3.8 kts
```

# AI-generated docs follows

I will look through all this and incorporate it in the docs above in the near future.

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
