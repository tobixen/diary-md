"""Tests for diary_md.redact: producing the public version of a diary.

All names here are made up — the fixtures are as public as the package.
"""

import json
import re
import unicodedata
from datetime import datetime
from io import StringIO

import pytest

from diary_md.exceptions import DiaryParseError
from diary_md.parser import markdown_to_dict
from diary_md.redact import (
    Person,
    PublicPolicy,
    public_text,
    redact_diary,
    redact_names,
    strip_private_fences,
)

DIARY = """\
# Fake Voyage

A summer with Ingrid and Bjarne on board.

## Monday 2026-06-01 - Harbourtown - Fishbay

Ingrid and Bjarne arrived.  Ingrid's bag was lost.  Petra came by for coffee.

Little Ola played on deck.

### Maintenance

Bjarne fixed the bilge pump.

### Expenses

* EUR 10.00 - groceries - bread

### Private

Something nobody should read.

### Mystery section

Unclassified stuff.

## Tuesday 2026-06-02 - Fishbay

Too recent to be reviewed.
"""


@pytest.fixture
def policy():
    return PublicPolicy(
        people=[
            Person(name='Ingrid', policy='pseudonym', pseudonym='Astrid'),
            Person(name='Bjarne', policy='initial', aliases=['Bjarnes']),
            Person(name='Petra', policy='public'),
            Person(name='Ola', policy='child', anonymous='a child'),
        ],
        public_sections=['Maintenance'],
        private_sections=['Private'],
        reviewed_up_to=datetime(2026, 6, 1),
    )


def parse(text):
    return markdown_to_dict(StringIO(text))


class TestStripPrivateFences:
    def test_removes_fenced_paragraphs(self):
        text = "Public.\n\n<!-- private -->\nSecret.\n<!-- /private -->\n\nAlso public.\n"
        out = strip_private_fences(text)
        assert 'Secret' not in out
        assert 'Public.' in out
        assert 'Also public.' in out

    def test_unbalanced_open_fails(self):
        with pytest.raises(DiaryParseError, match='line 1'):
            strip_private_fences("<!-- private -->\nSecret forever\n")

    def test_unbalanced_close_fails(self):
        with pytest.raises(DiaryParseError):
            strip_private_fences("text\n<!-- /private -->\n")

    def test_nested_fails(self):
        with pytest.raises(DiaryParseError):
            strip_private_fences("<!-- private -->\n<!-- private -->\nx\n<!-- /private -->\n<!-- /private -->\n")


class TestPublicText:
    def test_fence_case_and_annotation(self):
        out = public_text("a\n<!-- PRIVATE: medical -->\nsecret\n<!-- /Private -->\nb\n")
        assert 'secret' not in out

    def test_malformed_private_marker_fails(self):
        with pytest.raises(DiaryParseError, match='line 1'):
            public_text("Inline <!-- private -->secret<!-- /private --> text\n")

    def test_other_comments_removed(self):
        assert public_text("a <!-- note to self --> b\n<!--\nmulti\n-->\n") == "a  b\n\n"


class TestRedactNames:
    def test_pseudonym_with_genitive(self, policy):
        assert redact_names("Ingrid's bag and Ingrids hat", policy.people) == '"Astrid\'s" bag and "Astrids" hat'

    @pytest.mark.parametrize(('text', 'expected'), [
        ('"Ingrid" said', '"Astrid" said'),
        ('“Ingrid”', '“Astrid”'),
        ('<a title="Ingrid">x</a>', '<a title="Astrid">x</a>'),
    ])
    def test_pseudonym_already_quoted(self, policy, text, expected):
        assert redact_names(text, policy.people) == expected

    def test_initial(self, policy):
        assert redact_names("Bjarne slept", policy.people) == "B. slept"

    def test_alias(self, policy):
        assert redact_names("Bjarnes boat", policy.people) == "B. boat"

    def test_public_untouched(self, policy):
        assert redact_names("Petra waved", policy.people) == "Petra waved"

    def test_child_anonymous(self, policy):
        assert redact_names("Little Ola played", policy.people) == "Little a child played"

    def test_word_boundaries(self, policy):
        assert redact_names("Olaf and Ingridsen", policy.people) == "Olaf and Ingridsen"

    def test_pseudonym_required(self):
        with pytest.raises(ValueError, match='Ingrid'):
            Person(name='Ingrid', policy='pseudonym')

    def test_unknown_policy_rejected(self):
        with pytest.raises(ValueError, match='sometimes'):
            Person(name='Ingrid', policy='sometimes')


class TestRedactDiary:
    def test_sections_whitelisted(self, policy):
        out, report = redact_diary(parse(DIARY), policy)
        day = out['Fake Voyage']['Monday 2026-06-01 - Harbourtown - Fishbay']
        assert 'Maintenance' in day
        assert 'Private' not in day
        assert 'Expenses' not in day
        assert 'Mystery section' not in day
        # unlisted sections are reported so they get classified; blacklisted are not
        assert set(report.unclassified_sections) == {'Expenses', 'Mystery section'}

    def test_section_aliases(self, policy):
        text = "## Monday 2026-06-01\n\n### Vedlikehold\n\nSmurte vinsjen.\n"
        out, _ = redact_diary(parse(text), policy)
        assert 'Vedlikehold' in out['Monday 2026-06-01']

    def test_review_lag(self, policy):
        out, _ = redact_diary(parse(DIARY), policy)
        assert [k for k in out['Fake Voyage'] if not k.startswith('__')] == [
            'Monday 2026-06-01 - Harbourtown - Fishbay'
        ]

    def test_public_from_lower_bound(self, policy):
        policy.reviewed_up_to = datetime(2026, 6, 2)
        policy.public_from = datetime(2026, 6, 2)
        out, report = redact_diary(parse(DIARY), policy)
        assert [k for k in out['Fake Voyage'] if not k.startswith('__')] == ['Tuesday 2026-06-02 - Fishbay']
        # sections of days left out are not reported
        assert not report.unclassified_sections
        # a cut chapter keeps its intro, and says which side was left out
        assert 'on board' in out['Fake Voyage']['__content__']
        assert out['Fake Voyage']['__left_out__'] == ['before']

    def test_left_out_after_review_date(self, policy):
        out, _ = redact_diary(parse(DIARY), policy)
        assert out['Fake Voyage']['__left_out__'] == ['after']

    def test_left_out_both_sides(self, policy):
        text = DIARY + "\n## Wednesday 2026-06-03\n\nLater.\n"
        policy.reviewed_up_to = datetime(2026, 6, 2)
        policy.public_from = datetime(2026, 6, 2)
        out, _ = redact_diary(parse(text), policy)
        assert out['Fake Voyage']['__left_out__'] == ['before', 'after']

    def test_nothing_left_out(self, policy):
        policy.reviewed_up_to = datetime(2026, 6, 2)
        out, _ = redact_diary(parse(DIARY), policy)
        assert '__left_out__' not in out['Fake Voyage']

    def test_chapter_without_published_days_left_out(self, policy):
        # the chapter's own text belongs to a period nobody reviewed
        text = DIARY + "\n# Fake Autumn\n\nIngrid left.\n\n## Monday 2026-09-07\n\nRain.\n"
        out, report = redact_diary(parse(text), policy)
        assert 'Fake Autumn' not in out
        assert ' left.' not in json.dumps(out)
        policy.reviewed_up_to = datetime(2026, 9, 7)
        policy.public_from = datetime(2026, 9, 1)
        out, _ = redact_diary(parse(text), policy)
        assert [k for k in out if not k.startswith('__')] == ['Fake Autumn']
        assert out['Fake Autumn']['__content__'] == '"Astrid" left.'
        assert 'Monday 2026-09-07' in out['Fake Autumn']

    def test_public_from_after_review_date_rejected(self, policy):
        policy.public_from = datetime(2026, 6, 2)
        with pytest.raises(ValueError, match='public_from'):
            redact_diary(parse(DIARY), policy)

    def test_review_date_required(self, policy):
        policy.reviewed_up_to = None
        with pytest.raises(ValueError, match='reviewed'):
            redact_diary(parse(DIARY), policy)

    def test_names_redacted_everywhere(self, policy):
        out, _ = redact_diary(parse(DIARY), policy)
        dumped = json.dumps(out)
        assert 'Ingrid' not in dumped
        assert 'Bjarne' not in dumped
        assert not re.search(r'\bOla', dumped)
        assert '\\"Astrid\\"' in dumped
        assert 'Petra' in dumped

    def test_child_mentions_reported(self, policy):
        _, report = redact_diary(parse(DIARY), policy)
        assert report.child_mentions == ['2026-06-01']

    def test_undated_leaf_is_an_error(self, policy):
        with pytest.raises(DiaryParseError, match='Someday soon'):
            redact_diary(parse("## Someday soon\n\nIngrid was here.\n"), policy)

    def test_undated_day_with_sections_is_an_error(self, policy):
        text = ("# Fake Voyage\n\n## 15 July - Harbour\n\nSecret day.\n\n"
                "### Expenses\n\n#### Detail\n\nMore.\n")
        with pytest.raises(DiaryParseError, match='15 July'):
            redact_diary(parse(text), policy)

    def test_invalid_date_is_an_error(self, policy):
        with pytest.raises(DiaryParseError, match='2026-02-30'):
            redact_diary(parse("## Monday 2026-02-30\n\nx\n"), policy)

    def test_chapter_without_days_is_an_error(self, policy):
        with pytest.raises(DiaryParseError, match='TODO'):
            redact_diary(parse(DIARY + "\n# TODO\n\n## Fix the winch\n\nSoon.\n"), policy)

    def test_nfc_normalised(self):
        people = [Person(name='José', policy='pseudonym', pseudonym='Pedro')]
        assert redact_names(unicodedata.normalize('NFD', 'José came'), people) == '"Pedro" came'

    def test_capitalised_mid_sentence_is_reported_despite_lower_case_use(self, policy):
        text = ("## Monday 2026-06-01\n\n"
                "Then we paid 5 EUR per day, and then Per came by.  Per left early.\n")
        _, report = redact_diary(parse(text), policy)
        # 'Per' at a sentence start is excused, mid-sentence it is not
        assert report.unknown_tokens == {'Per': 1}

    def test_multi_word_allow_words_are_phrases(self, policy):
        policy.allow_words = ['Santa Maria']
        text = "## Monday 2026-06-01\n\nWe anchored at Santa Maria, and we met Maria there.\n"
        _, report = redact_diary(parse(text), policy)
        assert set(report.unknown_tokens) == {'Maria'}

    def test_unknown_tokens(self, policy):
        text = ("## Monday 2026-06-01 - Harbourtown\n\n"
                "Ingrid met Zyxwort at the quay.  The quay was wet, so we left.  "
                "We bought EUR at the Seabank.\n")
        _, report = redact_diary(parse(text), policy, known_words={'Seabank', 'Harbourtown'})
        # Zyxwort is unknown; "The" and "We" start sentences;
        # Astrid is a pseudonym, hence known; EUR is an acronym
        assert set(report.unknown_tokens) == {'Zyxwort'}

    def test_sentence_start_excused_even_if_never_lower_case(self, policy):
        text = "## Monday 2026-06-01\n\nZyxwort joined.  Rainy day!\n\n* Qwerty came\n"
        _, report = redact_diary(parse(text), policy)
        assert not report.unknown_tokens

    def test_known_phrase_at_sentence_start_does_not_excuse_next_word(self, policy):
        policy.allow_words = ['Golden Sands']
        text = "## Monday 2026-06-01\n\nGolden Sands Qwerty was crowded.\n"
        _, report = redact_diary(parse(text), policy)
        assert set(report.unknown_tokens) == {'Qwerty'}

    def test_chapter_intro_is_checked(self, policy):
        text = "# Trip\n\nwith Zyxwort.\n\n## Monday 2026-06-01\n\nok.\n"
        _, report = redact_diary(parse(text), policy)
        assert set(report.unknown_tokens) == {'Zyxwort'}

    def test_deeper_headers_redacted_not_checked(self, policy):
        text = "## Monday 2026-06-01\n\n### Maintenance\n\nx\n\n#### Visit from Qwertyman and Ingrid\n\ny\n"
        out, report = redact_diary(parse(text), policy)
        assert not report.unknown_tokens
        assert 'Visit from Qwertyman and "Astrid"' in out['Monday 2026-06-01']['Maintenance']

    def test_headers_not_checked(self, policy):
        text = "# Trip to Zyxland\n\n## Monday 2026-06-01 - Qwertyport\n\nok.\n"
        _, report = redact_diary(parse(text), policy)
        assert not report.unknown_tokens

    def test_registered_name_in_header_still_redacted(self, policy):
        text = "## Monday 2026-06-01 - Ingrid's place\n\nok.\n"
        out, _ = redact_diary(parse(text), policy)
        assert list(out) == ['Monday 2026-06-01 - "Astrid\'s" place']

    @pytest.mark.parametrize(('text', 'expected'), [
        ('We hiked in the Golden Sands forest with Kim André.', {'Golden Sands', 'Kim André'}),
        ('Golden Sands was crowded.', {'Golden Sands'}),
        ('so on Monday Zyxwort came.', {'Zyxwort'}),
        ('then the boat.  Then Zyxwort came.', {'Zyxwort'}),
        ('we met King Haakon and Ingrid Zyx there.', {'King Haakon', 'Ingrid Zyx'}),
        ('we met Bjarne Zyxsen at the quay.', {'Bjarne Zyxsen'}),
        ('Ingrid Zyxsen arrived.', {'Ingrid Zyxsen'}),
        ('so Ingrid and Bjarne Petra came.', set()),
    ])
    def test_multi_word_names_reported_whole(self, policy, text, expected):
        _, report = redact_diary(parse(f"## Monday 2026-06-01\n\n{text}\n"), policy)
        assert set(report.unknown_tokens) == expected

    def test_contractions_of_i_known(self, policy):
        text = "## Monday 2026-06-01\n\nI've been, I'll go, I’d stay.\n"
        _, report = redact_diary(parse(text), policy)
        assert not report.unknown_tokens

    def test_input_not_modified(self, policy):
        md = parse(DIARY)
        before = json.dumps(md)
        redact_diary(md, policy)
        assert json.dumps(md) == before


class TestPolicyFile:
    def test_load(self, tmp_path):
        f = tmp_path / 'public.json'
        f.write_text(json.dumps({
            'reviewed_up_to': '2026-06-01',
            'public_sections': ['Maintenance'],
            'private_sections': ['Private'],
            'allow_words': ['Harbourtown'],
            'people': [
                {'name': 'Ingrid', 'policy': 'pseudonym', 'pseudonym': 'Astrid'},
                {'name': 'Ola', 'policy': 'child'},
            ],
        }))
        policy = PublicPolicy.load(f)
        assert policy.reviewed_up_to == datetime(2026, 6, 1)
        assert policy.public_from is None
        assert policy.people[1].replacement == 'a child'
        assert policy.allow_words == ['Harbourtown']


    def test_load_public_from(self, tmp_path):
        f = tmp_path / 'public.json'
        f.write_text(json.dumps({'reviewed_up_to': '2026-11-01', 'public_from': '2026-10-01'}))
        assert PublicPolicy.load(f).public_from == datetime(2026, 10, 1)


class TestVerbatimContent:
    """Section text is the source verbatim; the redaction pass must still hold."""

    @pytest.mark.parametrize('breaker', ['\x0c', '\x0b', '\x85', ' ', ' ', '\x1c'])
    def test_private_text_stays_in_its_section(self, policy, breaker):
        text = ("## Monday 2026-06-01\n\n### Private\n\n"
                f"one{breaker}two\n\nsecret line\n\n### Maintenance\n\nGreased the winch.\n")
        out, _ = redact_diary(parse(text), policy)
        maintenance = out['Monday 2026-06-01']['Maintenance']['__content__']
        assert maintenance == 'Greased the winch.'

    def test_html_block_in_public_section_is_redacted_and_checked(self, policy):
        text = ("## Monday 2026-06-01\n\n### Maintenance\n\n"
                "<div>Ingrid and Zyxwort</div>\n")
        out, report = redact_diary(parse(text), policy)
        assert out['Monday 2026-06-01']['Maintenance']['__content__'] == '<div>"Astrid" and Zyxwort</div>'
        assert 'Zyxwort' in report.unknown_tokens

    @pytest.mark.parametrize('line', ['+ Quay was wet.', '| Quay | wet |', '* ~~Quay painted~~'])
    def test_plus_bullet_and_table_cell_start_a_sentence(self, policy, line):
        text = f"## Monday 2026-06-01\n\nthe quay was dry.\n\n{line}\n"
        _, report = redact_diary(parse(text), policy)
        assert 'Quay' not in report.unknown_tokens
