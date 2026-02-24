"""
Tests for birthday DB access and date parsing logic.
Uses an in-memory SQLite database so the real DB is never touched.
Run with: python -m pytest tests/ or python -m unittest tests/test_birthdays.py
"""
import unittest
from datetime import datetime, date, timezone
from sqlalchemy import create_engine, extract
from sqlalchemy.orm import Session

from database.tbnbotdatabase import Base, TbnMember

DISCORD_ID = 186222231125360641  # 64-bit Discord snowflake
BIRTHDAY_INPUT_FORMAT = "%d/%m/%Y"


def parse_birthday(birthday_str: str) -> datetime:
    """Mirrors the parsing logic in Birthdays.set_birthday."""
    if len(birthday_str) == 5:
        return datetime.strptime(birthday_str + "/1900", BIRTHDAY_INPUT_FORMAT)
    elif len(birthday_str) == 10:
        return datetime.strptime(birthday_str, BIRTHDAY_INPUT_FORMAT)
    raise ValueError("Invalid date format")


class TestBirthdayDB(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.session = Session(engine)

    def tearDown(self):
        self.session.close()

    def test_set_and_retrieve_birthday(self):
        birthday = date(1995, 6, 15)
        self.session.merge(TbnMember(DISCORD_ID, birthday))
        self.session.commit()

        result = self.session.query(TbnMember).filter(TbnMember.id == DISCORD_ID).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.birthday, birthday)

    def test_discord_snowflake_id_round_trips(self):
        """Ensures 64-bit Discord IDs aren't truncated by the Integer column."""
        self.session.merge(TbnMember(DISCORD_ID, date(2000, 1, 1)))
        self.session.commit()

        result = self.session.query(TbnMember).filter(TbnMember.id == DISCORD_ID).first()
        self.assertEqual(result.id, DISCORD_ID)

    def test_today_birthday_query_finds_match(self):
        """The extract(month/day) query used by notify_birthdays finds today's birthday."""
        today = datetime.now(timezone.utc)
        self.session.merge(TbnMember(DISCORD_ID, date(1990, today.month, today.day)))
        self.session.commit()

        results = self.session.query(TbnMember).filter(
            extract("month", TbnMember.birthday) == today.month,
            extract("day", TbnMember.birthday) == today.day,
        ).all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, DISCORD_ID)

    def test_today_birthday_query_excludes_other_days(self):
        today = datetime.now(timezone.utc)
        other_month = (today.month % 12) + 1
        self.session.merge(TbnMember(DISCORD_ID, date(1990, other_month, today.day)))
        self.session.commit()

        results = self.session.query(TbnMember).filter(
            extract("month", TbnMember.birthday) == today.month,
            extract("day", TbnMember.birthday) == today.day,
        ).all()

        self.assertEqual(results, [])

    def test_remove_birthday_excludes_from_query(self):
        today = datetime.now(timezone.utc)
        self.session.merge(TbnMember(DISCORD_ID, date(1990, today.month, today.day)))
        self.session.commit()

        member = self.session.query(TbnMember).filter(TbnMember.id == DISCORD_ID).first()
        member.birthday = None
        self.session.commit()

        results = self.session.query(TbnMember).filter(
            extract("month", TbnMember.birthday) == today.month,
            extract("day", TbnMember.birthday) == today.day,
        ).all()

        self.assertEqual(results, [])

    def test_member_with_no_birthday_returns_none(self):
        self.session.merge(TbnMember(DISCORD_ID))
        self.session.commit()

        result = self.session.query(TbnMember).filter(TbnMember.id == DISCORD_ID).first()
        self.assertIsNone(result.birthday)

    def test_unknown_member_returns_none(self):
        result = self.session.query(TbnMember).filter(TbnMember.id == DISCORD_ID).first()
        self.assertIsNone(result)


class TestBirthdayParsing(unittest.TestCase):
    def test_day_month_format_uses_year_1900(self):
        result = parse_birthday("24/02")
        self.assertEqual(result.year, 1900)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 24)

    def test_full_date_format(self):
        result = parse_birthday("24/02/1995")
        self.assertEqual(result.year, 1995)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 24)

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            parse_birthday("2024-02-24")


if __name__ == "__main__":
    unittest.main()
