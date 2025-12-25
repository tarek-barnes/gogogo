from datetime import datetime
from helper import (
    count_moves_in_a_game,
    is_sgf_file_formatted_in_the_expected_way,
    fix_badly_formatted_sgf_file,
    get_game_record_as_string
)

import os
import re
import shutil

# Source of data: https://homepages.cwi.nl/~aeb/go/games/

DESTINATION_DIR = "/Users/tarek/github/gogogo/destination"
SOURCE_DIR = "/Users/tarek/Downloads/Shusai/"

def get_sgf_filepaths_for_source_dir():
    return [
        os.path.join(dirpath, filename)
        for dirpath, _, filenames in os.walk(SOURCE_DIR)
        for filename in filenames
        if filename.endswith('.sgf')
    ]

def get_game_metadata(game_filepath) -> dict:
    game = get_game_record_as_string(game_filepath)
    game = game.split('\n')
    game = [k for k in game if k]
    game = [k.split(';') for k in game]
    game = [j for k in game for j in k if j]

    metadata_clean = []
    metadata = [k for k in game if not (k.startswith('B[') or k.startswith('W['))]
    for entry in metadata:
        metadata_clean += [chunk + ']' for chunk in entry.split(']') if chunk]
    
    metadata_clean = [k for k in metadata_clean if '[' in k and ']' in k]
    metadata_dict = {k: v[:-1] for k, v in (item.split('[', 1) for item in metadata_clean)}
    return metadata_dict

def remove_descriptives(raw_player_name: str) -> str:
    if "(" in raw_player_name:
        raw_player_name = raw_player_name.split("(")[0]
    return re.sub(r'[1-9]d', '', raw_player_name).strip()

def format_player_name(raw_player_name: str) -> tuple:
    """
    Want either:
     a) single name w/ space but w/o rank: Go Seigen.
     b) if multiple players: ???

    Returns tuple (formatted_name: str, is_rengo: bool)
    """
    is_player_name_simple = all([(k.isalpha() or k == " ") for k in raw_player_name])
    is_multiple_players = ("," in raw_player_name or "and" in raw_player_name)
    if is_player_name_simple:
        return (raw_player_name.strip(), False)
    elif is_multiple_players:
        if "," in raw_player_name and "and" in raw_player_name:
            first_comma = raw_player_name.index(",")
            first_and = raw_player_name.index("and")
            delimiter = raw_player_name[min(first_comma, first_and)]
            raw_player_name = raw_player_name.split(delimiter)[0]
            return (remove_descriptives(raw_player_name), True)
        elif "," in raw_player_name:
            raw_player_name = raw_player_name.split(",")[0]
            return (remove_descriptives(raw_player_name), True)
        elif "and" in raw_player_name:
            raw_player_name = raw_player_name.split("and")[0]
            return (remove_descriptives(raw_player_name), True)
    else:
        return (remove_descriptives(raw_player_name), False)

def format_game_date(raw_date: str, delim: str = '-') -> str:
    """
    Want dates in format: YYYYMMDD.
    If there are multiple dates, reduce to first (The SGF file will contain all dates).
       >>> e.g. 1916-05-05..13 -> 19160505.
    If less is provided (e.g. only a year), that'll do.
    """
    # special logic for tiny set of outliers (DTX property rather than standard DT property)
    #   e.g. Published 20 Jan-2 Feb 1930
    if raw_date.startswith("Published"):
        year = raw_date.split(" ")[-1]
        (monthday_start, monthday_end) = raw_date.replace("Published on", "").replace("Published", "").replace(year, "").strip().split("-")
        (day_start, month_start) = monthday_start.split(" ")
        if month_start.isalpha():
            month_start = datetime.strptime(month_start, "%b")
        month_start = str(month_start)
        month_start = "0"+month_start if len(month_start) == 1 else month_start
        return f"{year}{month_start}{day_start}"

    # normal logic
    clean_date = raw_date.replace(delim, "")
    
    if ".." in raw_date:
        clean_date = clean_date.split("..")[0]
    elif "," in raw_date:
        clean_date = clean_date.split(",")[0]
    return clean_date

def get_game_date(metadata_dict: dict) -> str:
    # shusai-701.sgf legit has no date
    if "DT" in metadata_dict:
        return format_game_date(metadata_dict["DT"])
    elif "DTX" in metadata_dict:
        return format_game_date(metadata_dict["DTX"])
    return "UNKNOWNDATE"

def get_new_filename(filepath):
    metadata_dict = get_game_metadata(filepath)
    (black_player_name, is_rengo) = format_player_name(metadata_dict.get('PB'))
    (white_player_name, _) = format_player_name(metadata_dict.get('PW'))
    game_date = get_game_date(metadata_dict)
    if is_rengo:
        return f'{game_date}-RENGO-Team {black_player_name}-Team {white_player_name}.sgf'
    return f'{game_date}-{black_player_name}-{white_player_name}.sgf'

def get_new_filepath(filepath):
    return DESTINATION_DIR + "/" + get_new_filename(filepath)

def main():
    filepaths_to_process = get_sgf_filepaths_for_source_dir()
    print(f"num filepaths = {len(filepaths_to_process)}")
    for fp in filepaths_to_process:
        print(f"Processing filepath: '{fp}'")
        # count the number of moves, if >400, validate game
        # check if the date already exists in the source of truth list of games
        # if so, also check number of moves match
        # ... and of course, the opponent name
        shutil.copy(fp, get_new_filepath(fp))

if __name__ == '__main__':
    main()

