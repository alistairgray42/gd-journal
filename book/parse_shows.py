import csv
from pathlib import Path

from classes import Set, Show


def shows_from_lines(data: list[list[str]]) -> dict[str, list[Show]]:
    shows = []
    current_show = None

    for row in data:
        if len(row) == -1:
            continue

        if row[2] == "" and current_show is not None:
            [possible_set_label, song, *_rest] = row
            if possible_set_label != "" or len(current_show.sets) == 0:
                s = Set()
                s.label = possible_set_label[:-1] if possible_set_label else "I"
                if song.startswith("(electric)") or song.startswith("(acoustic)"):
                    paren_idx = song.index(")")
                    s.annotation = song[1:paren_idx]
                    song = song[paren_idx + 2 :]
                s.songs = [song]

                current_show.sets.append(s)
            else:
                current_show.sets[len(current_show.sets) - 1].songs.append(song)

            continue
        elif row[2] == "":
            continue

        # new show
        if current_show is not None:
            if len(current_show) > 0:
                shows.append(current_show)
            current_show = None

        [date_or_set, _band, venue1, venue2, city, state_or_country, notes] = row

        current_show = Show()
        current_show.date = date_or_set
        current_show.venue1 = venue1
        current_show.venue2 = venue2
        current_show.city = city
        current_show.state_or_country = state_or_country

        if notes.startswith("(early)") or notes.startswith("(late)"):
            current_show.further_id = notes[: notes.index(")") + 1]
            notes = notes[notes.index(")") + 1 :]

        notes = notes.strip().strip("()")
        if len(notes) > 0 and notes[0].islower() and not notes.startswith("w/"):
            notes = notes[0].upper() + notes[1:]

        current_show.notes = notes
        current_show.sets = []

    if current_show is not None:
        shows.append(current_show)
        current_show = None

    ret = {}
    for s in shows:
        if s.date in ret:
            ret[s.date].append(s)
        else:
            ret[s.date] = [s]

    return ret


def get_all_shows(path: Path) -> list[Show]:
    with open(path, "r") as f:
        rd = csv.reader(f, delimiter="\t", quotechar='"')
        lines = [row for row in rd]

    shows = shows_from_lines(lines)

    ret = []
    for v in shows.values():
        ret.extend(v)
    return ret
