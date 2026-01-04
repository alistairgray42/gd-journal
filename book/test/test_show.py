import unittest

from book.classes import Set, Show


class TestShow(unittest.TestCase):
    def test_groupings(self):
        # 5/27/1993
        set1 = Set(
            label="1",
            songs=[
                "Shakedown Street",
                "The Same Thing",
                "Dire Wolf",
                "Beat It On Down The Line",
                "High Time",
                "When I Paint My Masterpiece",
                "Cumberland Blues",
                "Promised Land",
            ],
        )

        set2 = Set(
            label="2",
            songs=[
                "Picasso Moon",
                "> Fire On The Mountain",
                "> Wave To The Wind",
                "Cassidy",
                "> Uncle John's Band",
                "> Cassidy",
                "> Drums",
                "> Space",
                "> The Other One",
                "> Wharf Rat",
                "> Sugar Magnolia",
            ],
        )

        encore = Set(label="E", songs=["Gloria"])

        show = Show(
            date="5/27/1993",
            venue1="Cal Expo Amphitheatre",
            city="Sacramento",
            state_or_country="CA",
            notes="Rex Foundation benefit; portions released as Road Trips v. 2 no. 4",
            sets=[set1, set2, encore],
        )

        groupings = show.to_page_friendly_set_groupings()
        assert len(groupings) == 2
        assert len(groupings[0]) == 1
        assert len(groupings[1]) == 2
