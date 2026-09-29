"""Produce the public version of a diary.

A diary names people, children included, and has sections nobody else should
read.  The public version is made by one pass over the parsed section tree, so
every exporter publishes the same thing:

* whole days after ``reviewed_up_to`` are left out: moving that date is the
  human review step, and it also keeps the current position off the web;
* only whitelisted 3rd-level sections are kept.  Blacklisted ones are dropped
  silently, anything unlisted is dropped *and* reported, so that it gets
  classified.  Unlisted means private, which keeps it fail-closed;
* paragraphs between ``<!-- private -->`` and ``<!-- /private -->`` are removed
  from the raw text before parsing, and so is every other HTML comment
  (:func:`public_text`);
* a day header without a valid date is an error, not a guess;
* names from the people registry are replaced according to each person's
  policy (:func:`redact_names`);
* every capitalised word left in the output that is not known — a registered
  name, a pseudonym, an allowed word or phrase, a weekday — is reported
  (:attr:`RedactionReport.unknown_tokens`).  At the start of a sentence, a
  word the diary also uses in lower case is excused; mid-sentence, a capital
  letter means a name.  That is the fail-closed part of the name handling: a
  name not yet in the registry shows up there.  Names are matched as written,
  capitalised; a misspelt one is for the review to catch.

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
_SENTENCE_START = re.compile(r'(?:^|[.!?:\n])[\s"“«(\'*#>-]*$')
_DATE_IN_HEADER = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
_WORD = re.compile(r"[^\W\d_][\w'’-]*")

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
        """The text standing in for the name, or None if it is printed as written."""
        if self.policy == 'public':
            return None
        if self.policy == 'pseudonym':
            return self.pseudonym
        if self.policy == 'initial':
            return self.name[0] + '.'
        if self.policy == 'child':
            return self.anonymous or 'a child'
        return self.anonymous or 'someone'


@dataclass
class PublicPolicy:
    """What may be published: people, sections, known words and the review date."""

    people: list[Person] = field(default_factory=list)
    public_sections: list[str] = field(default_factory=list)
    private_sections: list[str] = field(default_factory=list)
    allow_words: list[str] = field(default_factory=list)
    reviewed_up_to: datetime | None = None

    @classmethod
    def load(cls, path: Path) -> 'PublicPolicy':
        """Load a policy from a JSON file with the same keys as the fields.

        ``reviewed_up_to`` is a YYYY-MM-DD string, ``people`` a list of
        objects with the fields of :class:`Person`.

        Any problem with the file is raised as ValueError naming the file.
        """
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            reviewed = data.get('reviewed_up_to')
            return cls(
                people=[Person(**p) for p in data.get('people', [])],
                public_sections=data.get('public_sections', []),
                private_sections=data.get('private_sections', []),
                allow_words=data.get('allow_words', []),
                reviewed_up_to=datetime.strptime(reviewed, DATE_FORMAT) if reviewed else None,
            )
        except (ValueError, TypeError, AttributeError) as e:
            raise ValueError(f'{path}: {e}') from e


@dataclass
class RedactionReport:
    """What the redaction pass wants a human to look at."""

    unclassified_sections: Counter = field(default_factory=Counter)
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
    return pattern.sub(lambda m: forms[m.group(1)].replacement + (m.group(2) or ''), _nfc(text))


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
    """Keep the reviewed days of one level; any other header there is an error."""
    out = {}
    for header, value in tree.items():
        if header.startswith('__') or not isinstance(value, dict):
            out[header] = value
            continue
        date = _day_date(header)
        if date is None:
            where = f' (in chapter {chapter})' if chapter else ''
            raise DiaryParseError(f'header without a date{where}: {header}')
        if date <= policy.reviewed_up_to:
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
            out[header] = _redact_days(value, policy, report, header)
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


def _texts(tree: dict):
    """Headers and ``__content__`` of a parsed tree: the text an exporter prints."""
    for key, value in tree.items():
        if key == '__content__':
            yield value
        elif not key.startswith('__'):
            yield key
            if isinstance(value, dict):
                yield from _texts(value)


def lower_case_words(tree: dict) -> set[str]:
    """Every word a diary uses in lower case somewhere — evidence that it is not a name."""
    return {w for text in _texts(tree) for w in _WORD.findall(text) if w.islower()}


def unknown_tokens(
    tree: dict, known: set[str], lower_case: set[str], phrases: list[str] = ()
) -> Counter:
    """Count capitalised words in ``tree`` that nobody vouched for.

    ``known`` is compared case-insensitively; ``phrases`` (multi-word allowed
    names) are blanked out before words are looked at.  A word also used in
    lower case (``lower_case``) is excused at the start of a sentence only.
    """
    phrase_re = (
        re.compile('|'.join(rf'(?<!\w){re.escape(p)}(?!\w)' for p in sorted(phrases, key=len, reverse=True)),
                   re.IGNORECASE)
        if phrases else None
    )
    found: Counter = Counter()
    for text in _texts(tree):
        if phrase_re:
            text = phrase_re.sub(' ', text)
        for match in _WORD.finditer(text):
            word = match.group(0)
            if not word[0].isupper() or word.isupper() or re.match(r"I['’]", word):
                continue
            stem = re.sub(r"(['’]s|['’])$", '', word)
            if stem.lower() in known or word.lower() in known:
                continue
            if stem.lower() in lower_case and _SENTENCE_START.search(text, 0, match.start()):
                continue
            found[stem] += 1
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
    report = RedactionReport()
    filtered = _redact_level(copy.deepcopy(md_dict), policy, report)

    children = [p for p in policy.people if p.policy == 'child']
    if children:
        child_pattern, _ = _name_pattern(children)
        report.child_mentions = _child_days(filtered, child_pattern)

    public = _walk_strings(filtered, lambda s: redact_names(s, policy.people))

    known = set(ALWAYS_KNOWN) | set(policy.allow_words) | set(known_words or ())
    for person in policy.people:
        if person.replacement is None:
            known |= {person.name, *person.aliases}
        elif person.policy == 'pseudonym':
            known.add(person.pseudonym)
    phrases = [w for w in known if len(_WORD.findall(w)) > 1]
    known = {w.lower() for w in known if len(_WORD.findall(w)) == 1}
    report.unknown_tokens = unknown_tokens(public, known, lower_case_words(md_dict), phrases)
    return public, report
