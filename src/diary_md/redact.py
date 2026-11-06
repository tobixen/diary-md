"""Produce the public version of a diary.

A diary names people, children included, and has sections nobody else should
read.  The public version is made by one pass over the parsed section tree, so
every exporter publishes the same thing:

* whole days after ``reviewed_up_to`` are left out: moving that date is the
  human review step, and it also keeps the current position off the web.
  Days before ``public_from``, if set, are left out too, so that the diary
  can be reviewed and published a period at a time.  A chapter that keeps
  some of its days keeps its own text too, and its ``__left_out__`` lists
  the sides (``before``, ``after``) where days were left out, so a reader
  can be told that more is to come; a chapter left with no days is dropped;
* only whitelisted 3rd-level sections are kept.  Blacklisted ones are dropped
  silently, anything unlisted is dropped *and* reported, so that it gets
  classified.  Unlisted means private, which keeps it fail-closed;
* paragraphs between ``<!-- private -->`` and ``<!-- /private -->`` are removed
  from the raw text before parsing, and so is every other HTML comment
  (:func:`public_text`);
* a day header without a valid date is an error, not a guess;
* names from the people registry are replaced according to each person's
  policy (:func:`redact_names`);
* every capitalised word left in the body text that is not known — a
  registered name, a pseudonym, an allowed word or phrase, a weekday — is
  reported (:attr:`RedactionReport.unknown_tokens`), neighbouring ones as one
  name, a registered name included.  The check reads the text before names
  are replaced.  Headers of any level are not checked (names in them are
  still replaced), and a single word starting a sentence is excused; mid-sentence, a capital letter means a name.  So a name not yet in
  the registry usually shows up there, but not always.  Names are matched as
  written, capitalised; a misspelt one is for the review to catch.

The pass is used by ``diary-digest export-web-json --public`` and
``check-public``; the other exporters do not redact.

The people registry is itself a list of real names, so it belongs outside any
published repository.
"""

import copy
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from diary_md.exceptions import DiaryParseError
from diary_md.models import DATE_FORMAT, SECTION_TO_CANONICAL, VALID_WEEKDAYS

POLICIES = ('public', 'pseudonym', 'initial', 'anonymous', 'child')

_FENCE_OPEN = re.compile(r'^\s*<!--\s*private\b(?:(?!-->).)*-->\s*$', re.IGNORECASE)
_FENCE_CLOSE = re.compile(r'^\s*<!--\s*/private\s*-->\s*$', re.IGNORECASE)
_FENCE_ANY = re.compile(r'<!--\s*/?private\b', re.IGNORECASE)
_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
_SENTENCE_START = re.compile(r'(?:^|[.!?:|\n])[\s"“«(\'*+#>~-]*$')
_DATE_IN_HEADER = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
_WORD = re.compile(r"[^\W\d_][\w'’-]*")
_QUOTES = '"“”«»„'

MONTHS_EN = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December')
ALWAYS_KNOWN = frozenset(VALID_WEEKDAYS + MONTHS_EN + ('I',))


@dataclass
class Person:
    """One entry in the people registry.

    ``aliases`` are further spellings (nicknames, irregular inflections).  The
    genitive forms ``-s``, ``-'s`` and ``-’s`` of the name and of every alias
    are handled without listing them.
    """

    name: str
    policy: str = 'pseudonym'
    aliases: list[str] = field(default_factory=list)
    pseudonym: str | None = None
    anonymous: str | None = None

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError(f"{self.name}: policy {self.policy!r} is not one of {', '.join(POLICIES)}")
        if self.policy == 'pseudonym' and not self.pseudonym:
            raise ValueError(f"{self.name}: policy 'pseudonym' needs a pseudonym")

    @property
    def replacement(self) -> str | None:
        """The unquoted text standing in for the name, or None if it is printed as written.

        :meth:`render` is what goes into the output.
        """
        if self.policy == 'public':
            return None
        if self.policy == 'pseudonym':
            return self.pseudonym
        if self.policy == 'initial':
            return self.name[0] + '.'
        if self.policy == 'child':
            return self.anonymous or 'a child'
        return self.anonymous or 'someone'

    def render(self, suffix: str = '', quoted: bool = False) -> str:
        """The replacement with a genitive ``suffix``.

        A pseudonym is put in quotes to show it is one, unless the name already
        stands in ``quoted`` text.
        """
        text = self.replacement + suffix
        return f'"{text}"' if self.policy == 'pseudonym' and not quoted else text


@dataclass
class PublicPolicy:
    """What may be published: people, sections, known words and the published period."""

    people: list[Person] = field(default_factory=list)
    public_sections: list[str] = field(default_factory=list)
    private_sections: list[str] = field(default_factory=list)
    allow_words: list[str] = field(default_factory=list)
    reviewed_up_to: datetime | None = None
    public_from: datetime | None = None

    @classmethod
    def load(cls, path: Path) -> 'PublicPolicy':
        """Load a policy from a JSON file with the same keys as the fields.

        ``reviewed_up_to`` and ``public_from`` are YYYY-MM-DD strings, ``people`` a list of
        objects with the fields of :class:`Person`.

        Any problem with the file is raised as ValueError naming the file.
        """
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            reviewed = data.get('reviewed_up_to')
            public_from = data.get('public_from')
            return cls(
                people=[Person(**p) for p in data.get('people', [])],
                public_sections=data.get('public_sections', []),
                private_sections=data.get('private_sections', []),
                allow_words=data.get('allow_words', []),
                reviewed_up_to=datetime.strptime(reviewed, DATE_FORMAT) if reviewed else None,
                public_from=datetime.strptime(public_from, DATE_FORMAT) if public_from else None,
            )
        except (ValueError, TypeError, AttributeError) as e:
            raise ValueError(f'{path}: {e}') from e


@dataclass
class RedactionReport:
    """What the redaction pass wants a human to look at."""

    unclassified_sections: Counter = field(default_factory=Counter)
    sections: Counter = field(default_factory=Counter)
    unknown_tokens: Counter = field(default_factory=Counter)
    child_mentions: list[str] = field(default_factory=list)

    def format(self) -> str:
        lines = []
        if self.unclassified_sections:
            lines.append('Sections neither public nor private (left out until classified):')
            lines += [f'  {name} ({n})' for name, n in self.unclassified_sections.most_common()]
        if self.child_mentions:
            lines.append('Days mentioning a child (check them for other identifying detail):')
            lines += [f'  {d}' for d in self.child_mentions]
        if self.unknown_tokens:
            lines.append('Unknown capitalised words (a name missing from the registry?):')
            lines += [f'  {w} ({n})' for w, n in sorted(self.unknown_tokens.items())]
        return '\n'.join(lines)


def strip_private_fences(text: str) -> str:
    """Remove every ``<!-- private -->`` … ``<!-- /private -->`` block from raw markdown.

    An unbalanced or nested fence raises :class:`DiaryParseError` rather than
    guessing where the private part ends.
    """
    out = []
    opened_at = None
    for lineno, line in enumerate(text.splitlines(keepends=True), start=1):
        if _FENCE_OPEN.match(line):
            if opened_at is not None:
                raise DiaryParseError(f'line {lineno}: private fence opened again, still open since line {opened_at}')
            opened_at = lineno
        elif _FENCE_CLOSE.match(line):
            if opened_at is None:
                raise DiaryParseError(f'line {lineno}: private fence closed but never opened')
            opened_at = None
        elif _FENCE_ANY.search(line):
            raise DiaryParseError(f'line {lineno}: a private marker must be a line of its own')
        elif opened_at is None:
            out.append(line)
    if opened_at is not None:
        raise DiaryParseError(f'line {opened_at}: private fence never closed')
    return ''.join(out)


def public_text(text: str) -> str:
    """Raw markdown with private fences and every other HTML comment removed."""
    return _COMMENT.sub('', strip_private_fences(text))


def _nfc(text: str) -> str:
    return unicodedata.normalize('NFC', text)


def _name_pattern(people: list[Person]) -> tuple[re.Pattern | None, dict[str, Person]]:
    forms: dict[str, Person] = {}
    for person in people:
        if person.replacement is None:
            continue
        for form in [person.name, *person.aliases]:
            forms[_nfc(form)] = person
    if not forms:
        return None, forms
    alternation = '|'.join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    return re.compile(rf"(?<!\w)({alternation})(['’]s|s)?(?!\w)"), forms


def redact_names(text: str, people: list[Person]) -> str:
    """Replace every registered name in ``text`` according to its person's policy."""
    pattern, forms = _name_pattern(people)
    if pattern is None:
        return text
    def replace(m: re.Match) -> str:
        before, after = m.string[m.start() - 1:m.start()], m.string[m.end():m.end() + 1]
        quoted = bool(before) and before in _QUOTES and bool(after) and after in _QUOTES
        return forms[m.group(1)].render(m.group(2) or '', quoted)

    return pattern.sub(replace, _nfc(text))


def _walk_strings(node, fn):
    """Apply ``fn`` to every string in a parsed tree, keys included, except file names."""
    if isinstance(node, dict):
        return {
            (k if k.startswith('__') else fn(k)): (v if k == '__file_name__' else _walk_strings(v, fn))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [_walk_strings(v, fn) for v in node]
    if isinstance(node, str):
        return fn(node)
    return node


def _redact_day(day: dict, policy: PublicPolicy, report: RedactionReport) -> dict:
    public = {SECTION_TO_CANONICAL.get(s, s) for s in policy.public_sections}
    private = {SECTION_TO_CANONICAL.get(s, s) for s in policy.private_sections}
    out = {}
    for key, value in day.items():
        if key.startswith('__'):
            out[key] = value
            continue
        report.sections[key] += 1
        canonical = SECTION_TO_CANONICAL.get(key, key)
        if canonical in public:
            out[key] = value
        elif canonical not in private:
            report.unclassified_sections[key] += 1
    return out


def _day_date(header: str) -> datetime | None:
    """The date of a day header, None if it has none; an invalid date is an error."""
    match = _DATE_IN_HEADER.search(header)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), DATE_FORMAT)
    except ValueError:
        raise DiaryParseError(f'invalid date in header: {header}') from None


def _redact_days(tree: dict, policy: PublicPolicy, report: RedactionReport, chapter: str | None) -> dict:
    """Keep the published days of one level; any other header there is an error."""
    out = {}
    for header, value in tree.items():
        if header.startswith('__') or not isinstance(value, dict):
            out[header] = value
            continue
        date = _day_date(header)
        if date is None:
            where = f' (in chapter {chapter})' if chapter else ''
            raise DiaryParseError(f'header without a date{where}: {header}')
        if date <= policy.reviewed_up_to and not (policy.public_from and date < policy.public_from):
            out[header] = _redact_day(value, policy, report)
    return out


def _is_chapter(value: dict) -> bool:
    days = [k for k, v in value.items() if not k.startswith('__') and isinstance(v, dict)]
    return bool(days) and all(_DATE_IN_HEADER.search(k) for k in days)


def _redact_level(tree: dict, policy: PublicPolicy, report: RedactionReport) -> dict:
    """Filter the top level: dated headers are days, undated ones are chapters holding only days.

    Anything else — a day header with no date, a chapter with undated
    children or none at all — is an error rather than a guess.
    """
    out = {}
    for header, value in tree.items():
        if header.startswith('__') or not isinstance(value, dict) or _day_date(header) is not None:
            out.update(_redact_days({header: value}, policy, report, None))
        elif _is_chapter(value):
            days = _redact_days(value, policy, report, header)
            if not any(not k.startswith('__') for k in days):
                continue
            dates = [_day_date(k) for k, v in value.items() if not k.startswith('__') and isinstance(v, dict)]
            left_out = [side for side, cut in (
                ('before', policy.public_from and min(dates) < policy.public_from),
                ('after', max(dates) > policy.reviewed_up_to),
            ) if cut]
            if left_out:
                days['__left_out__'] = left_out
            out[header] = days
        else:
            _redact_days(value, policy, report, header)  # raises on the first undated child
            raise DiaryParseError(f'header without a date, and no dated days under it: {header}')
    return out


def _child_days(tree: dict, pattern: re.Pattern, date: str | None = None) -> list[str]:
    found: list[str] = []
    for key, value in tree.items():
        if key.startswith('__'):
            continue
        match = _DATE_IN_HEADER.search(key)
        day = match.group(1) if match else date
        if pattern.search(key) or (
            isinstance(value, dict) and pattern.search(value.get('__content__', ''))
        ):
            if day and day not in found:
                found.append(day)
        if isinstance(value, dict):
            found += [d for d in _child_days(value, pattern, day) if d not in found]
    return found


def _contents(tree: dict):
    """The ``__content__`` texts of a parsed tree; headers are not included."""
    for key, value in tree.items():
        if key == '__content__':
            yield value
        elif not key.startswith('__') and isinstance(value, dict):
            yield from _contents(value)


def lower_case_words(tree: dict) -> set[str]:
    """Every word a diary uses in lower case somewhere — evidence that it is not a name."""
    return {w for text in _contents(tree) for w in _WORD.findall(text) if w.islower()}


def _capitalised_runs(text: str):
    """Runs of capitalised words separated by single spaces, as (start, words)."""
    run: list[str] = []
    start = end = 0
    for match in _WORD.finditer(text):
        word = match.group(0)
        capitalised = word[0].isupper() and not word.isupper() and not re.match(r"I['’]", word)
        if capitalised and run and text[end:match.start()] == ' ':
            run.append(word)
        else:
            if run:
                yield start, run
            run, start = ([word], match.start()) if capitalised else ([], 0)
        end = match.end()
    if run:
        yield start, run


def unknown_tokens(
    tree: dict, known: set[str], phrases: list[str] = (), lower_case: set[str] = frozenset(),
    names: set[str] = frozenset(),
) -> Counter:
    """Count capitalised words and names in ``tree`` that nobody vouched for.

    ``tree`` is the text before names are replaced.  Only body text is looked
    at: headers hold places, and section names are checked against a list of
    their own.  ``known`` and the registered ``names`` are compared
    case-insensitively; ``phrases`` (multi-word known names) are blanked out
    first.  Neighbouring capitalised words are one name ("Golden Sands"),
    reported whole once known words are trimmed off its ends; a registered
    name is not trimmed, as "Ingrid Zyxsen" may be another Ingrid.  A single
    word at the start of a sentence is excused, so an unregistered name there
    gets through.  A sentence's first word that the diary also uses in lower
    case (``lower_case``) is not part of a name ("Then Ola came").
    """
    phrase_re = (
        re.compile('|'.join(rf'(?<!\w){re.escape(p)}(?!\w)' for p in sorted(phrases, key=len, reverse=True)),
                   re.IGNORECASE)
        if phrases else None
    )

    def stem(word: str) -> str:
        return re.sub(r"(['’]s|['’])$", '', word)

    def is_in(word: str, words: set[str]) -> bool:
        return word.lower() in words or stem(word).lower() in words

    found: Counter = Counter()
    for text in _contents(tree):
        text = _nfc(text)
        if phrase_re:
            # a placeholder that neither starts a sentence nor joins a name
            text = phrase_re.sub('_', text)
        for start, run in _capitalised_runs(text):
            at_sentence_start = bool(_SENTENCE_START.search(text, 0, start))
            if at_sentence_start and len(run) > 1 and run[0].lower() in lower_case:
                run, at_sentence_start = run[1:], False
            while run and is_in(run[0], known):
                run, at_sentence_start = run[1:], False
            while run and is_in(run[-1], known):
                run = run[:-1]
            if all(is_in(w, names) for w in run) or (len(run) == 1 and at_sentence_start):
                continue
            found[stem(' '.join(run))] += 1
    return found


def redact_diary(
    md_dict: dict, policy: PublicPolicy, known_words: set[str] | None = None
) -> tuple[dict, RedactionReport]:
    """Return the public version of a parsed diary, and what needs a human's attention.

    ``md_dict`` is the output of :func:`diary_md.parser.markdown_to_dict` and is
    not modified.  ``known_words`` adds to the policy's ``allow_words`` — place
    names, for instance.  Private fences and comments have to be stripped from
    the raw text before parsing; see :func:`public_text`.  A day header without
    a valid date raises :class:`DiaryParseError`.
    """
    if policy.reviewed_up_to is None:
        raise ValueError('the policy has no reviewed_up_to date; nothing can be published before review')
    if policy.public_from and policy.public_from > policy.reviewed_up_to:
        raise ValueError('public_from is after reviewed_up_to; nothing would be published')
    report = RedactionReport()
    filtered = _redact_level(copy.deepcopy(md_dict), policy, report)

    children = [p for p in policy.people if p.policy == 'child']
    if children:
        child_pattern, _ = _name_pattern(children)
        report.child_mentions = _child_days(filtered, child_pattern)

    public = _walk_strings(filtered, lambda s: redact_names(s, policy.people))

    known = set(ALWAYS_KNOWN) | set(policy.allow_words) | set(known_words or ())
    names = {_nfc(n) for person in policy.people for n in (person.name, *person.aliases)}
    phrases = [w for w in known | names if len(_WORD.findall(w)) > 1]
    known = {w.lower() for w in known if len(_WORD.findall(w)) == 1}
    names = {w.lower() for w in names if len(_WORD.findall(w)) == 1}
    report.unknown_tokens = unknown_tokens(filtered, known, phrases, lower_case_words(md_dict), names)
    return public, report
