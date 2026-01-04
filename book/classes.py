from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class LayoutType(Enum):
    SINGLE = "single"
    SPREAD = "spread"


@dataclass
class Set:
    label: str = ""
    annotation: Optional[str] = None
    songs: list = field(default_factory=list)

    @property
    def display_label(self) -> str:
        if self.label == "E":
            return "Encore"
        return f"Set {self.label}"

    def __len__(self) -> int:
        return len(self.songs)


@dataclass
class Show:
    date: str = ""
    further_id: str = ""
    venue1: str = ""
    venue2: Optional[str] = None
    city: str = ""
    state_or_country: str = ""
    notes: Optional[str] = None
    sets: list = field(default_factory=list)

    @property
    def year(self) -> int:
        return int(self.date.split("/")[0])

    @property
    def month(self) -> int:
        return int(self.date.split("/")[1])

    @property
    def day(self) -> int:
        return int(self.date.split("/")[2])

    @property
    def formatted_date(self) -> str:
        """Convert YYYY/MM/DD to a readable format"""
        parts = self.date.split("/")
        if len(parts) == 3:
            date = datetime(int(parts[0]), int(parts[1]), int(parts[2])).strftime(
                "%B %d, %Y"
            )
        else:
            date = self.date

        if self.further_id:
            date += f" {self.further_id}"
        return date

    @property
    def venue_display(self) -> str:
        if self.venue2:
            return f"{self.venue1}, {self.venue2}"
        return self.venue1

    @property
    def location_display(self) -> str:
        return f"{self.city}, {self.state_or_country}"

    def __len__(self) -> int:
        return sum(len(s) for s in self.sets)

    def to_page_friendly_set_groupings(self) -> list[list[Set]]:
        num_pages = 1
        curr_lines = 0
        for s in self.sets:
            if curr_lines + len(s) >= 20:
                num_pages += 1
                curr_lines = len(s)
            else:
                curr_lines += len(s)

        if num_pages == 1:
            return [self.sets]

        # try to divide as evenly as possible
        num_songs = sum(len(s) for s in self.sets)
        songs_per_page = (num_songs + 1) // num_pages

        ret = []
        curr_songs = 0
        next = 0

        for curr_page in range(1, num_pages + 1):
            if next >= len(self.sets):
                break

            ret.append([self.sets[next]])
            curr_songs += len(self.sets[next])

            next += 1

            while (songs_per_page * curr_page) > curr_songs + 5:
                if next >= len(self.sets):
                    break

                # eek!
                if sum(len(s) for s in ret[-1]) + len(self.sets[next]) > 20:
                    break

                ret[-1].append(self.sets[next])
                curr_songs += len(self.sets[next])
                next += 1

        while next < len(self.sets):
            if len(ret) < num_pages:
                ret.append([])
            ret[-1].append(self.sets[next])
            next += 1

        return ret

    def classify_layout(self) -> LayoutType:
        groupings = self.to_page_friendly_set_groupings()
        return LayoutType.SPREAD if len(groupings) > 1 else LayoutType.SINGLE
