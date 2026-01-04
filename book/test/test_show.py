import unittest

from book.classes import Set, Show


class TestShow(unittest.TestCase):
    def test_groupings_1993_05_27(self):
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
            date="1993/5/27",
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

    def test_groupings_1976_10_10(self):
        set1 = Set(
            label="I",
            songs=[
                "Might As Well",
                "Mama Tried",
                "Ramble On Rose",
                "Cassidy",
                "Deal",
                "El Paso",
                "Loser",
                "Promised Land",
                "Friend Of The Devil",
                "Dancin' In The Streets",
                "> Wharf Rat",
                "> Dancin' In The Streets",
            ],
        )
        set2 = Set(
            label="II",
            songs=[
                "Samson & Delilah",
                "Brown-Eyed Women",
                "Playin' In The Band",
                "> Drums",
                "> The Wheel",
                "> Jam",
                "> The Other One",
                "> Stella Blue",
                "> Playin' Reprise",
                "> Sugar Magnolia",
            ],
        )

        encore = Set(label="E", songs=["Johnny B. Goode"])

        show = Show(
            date="1976/10/10",
            venue1="Oakland Coliseum Stadium",
            city="Oakland",
            state_or_country="CA",
            notes="Opened for The Who; released as Dick's Picks v. 33",
            sets=[set1, set2, encore],
        )

        groupings = show.to_page_friendly_set_groupings()
        assert len(groupings) == 2
        assert len(groupings[0]) == 1
        assert len(groupings[1]) == 2
