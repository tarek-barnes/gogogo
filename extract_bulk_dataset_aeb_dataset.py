from datetime import datetime
from helper import (
    analyze_two_similar_games,
    count_moves_in_a_game,
    count_number_of_same_moves,
    get_game,
    get_matching_games,
    are_these_two_games_the_same
)

import math
import os
import re
import shutil

# Source of data: https://homepages.cwi.nl/~aeb/go/games/

# I created this w/ the following goals in mind:
# - for a game, are any moves missing?
# - for a game, how many total moves are the same? (currently only track until first diff)
# - for a game, get all pieces of metadata
# - for a game, give a % score on similarity to another game
# - for a dataset, tell me how many games are 100% the same

DESTINATION_DIR = "/Users/tarek/github/gogogo/staging"
MAX_MOVES_IN_A_GAME = 400
SOURCE_DIR = "/Users/tarek/github/gogogo/bulk_datasets/AEB/Cho_Chikun"
PRO_DIR = ["/Users/tarek/github/gogogo/pro_games/Cho Chikun"]

# specify no pro dir
# specify >1 pro dirs


    # Cho_Chikun
    # Dosaku
# Female Honinbo
    # Go_Seigen
# Gosei
# Honinbo
    # Honinbo_Jowa
# Ing
# Judan
# Kisei
# Meijin
# NHK
# Nakamura_Sumire
# Oza
# README.md
# Ryusei
    # Shusai
    # Shusaku
    # Takagawa
# Tengen

def get_sgf_filepaths_for_source_dir(source_dir=SOURCE_DIR):
    return [
        os.path.join(dirpath, filename)
        for dirpath, _, filenames in os.walk(source_dir)
        for filename in filenames
        if filename.endswith('.sgf')
    ]

# TODO: move to helper?
def get_game_metadata_dict(game_filepath: str) -> dict:
    metadata_dict = {}
    (metadata, _) = get_game(game_filepath)
    for entry in metadata:
        (key, val) = entry
        if key not in metadata_dict:
            metadata_dict[key] = val
        else:
            existing_val = metadata_dict[key]
            if type(existing_val) == list:
                metadata_dict[key].append(val)
            else:
                metadata_dict[key] = [existing_val, val]
    return metadata_dict

def remove_descriptives(raw_player_name: str) -> str:
    if "(" in raw_player_name:
        raw_player_name = raw_player_name.split("(")[0]
    return re.sub(r'[1-9]d', '', raw_player_name).strip()

def format_player_name(raw_player_name: str) -> tuple:
    """
    Want either:
     a) single name w/ space but w/o rank: Go Seigen.
     b) if multiple players: Team Go Seigen.

    Returns tuple (formatted_name: str, is_rengo: bool)
    """
    is_player_name_simple = all([(k.isalpha() or k == " ") for k in raw_player_name])
    conjunctions = [",", "&", "and"]
    is_multiple_players = any((c in raw_player_name for c in conjunctions))
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
        elif "&" in raw_player_name:
            raw_player_name = raw_player_name.split("&")[0]
            return (remove_descriptives(raw_player_name), True)
    else:
        return (remove_descriptives(raw_player_name), False)
    
def parse_published_date(published_date: str) -> tuple:
    """
    For older games, some date fields (usually DTX) start with 'Published'.
    This could be a year only, or a range of dates, or multiple other options.

    Covered examples:
    Published 20 Jan-2 Feb 1930
    Published 1936-09-07~20
    Published 1944-02-02~03-01
    Published 1981-08
    Published 1992
    Published in 1971-12 issue of Igo

    Return tuple: (year, month, day)
    """
    # Look for simplest patterns first: 1981-08, 1992, ..
    m = re.search(r"Published(?:\s+in)?\s+(\d{4})(?:-(\d{1,2}))?", published_date)
    if m:
        year = int(m.group(1))
        month = int(m.group(2)) if m.group(2) else None
        day = None
        return year, month, day

    # Look for a range
    year = int(re.search(r"\d{4}", published_date).group())

    # before range separator
    first_part = re.split(r"[~–—]", published_date)[0]

    # first date-like chunk
    date_part = re.search(
        r"\d{1,2}\s+[A-Za-z]{3}|\d{4}-\d{2}-\d{2}",
        first_part
    ).group()

    for fmt in ("%Y-%m-%d", "%d %b"):
        try:
            dt = datetime.strptime(date_part, fmt)
            break
        except ValueError:
            pass

    # backfill a year if necessary
    if dt.year == 1900:
        dt = dt.replace(year=year)

    return (dt.year, dt.month, dt.day)

def format_game_date(raw_date: str, delim: str = '-') -> str:
    """
    Want dates in format: YYYYMMDD. Probably a bad idea to overwrite `delim`.
    If there are multiple dates, reduce to first (The SGF file will contain all dates).
       >>> e.g. 1916-05-05..13 -> 19160505.
    If less is provided (e.g. only a year), that'll do.
    """
    # catch multiple dates being passed in even though it makes no sense
    if type(raw_date) == list:
        if len(raw_date) == 0:
            raw_date = ''
        elif len(raw_date) == 1:
            raw_date = raw_date[0]
        elif len(raw_date) == 2:
            (a, b) = raw_date
            if a in b: raw_date = b
            elif b in a: raw_date = a
            else: raw_date = sorted(raw_date, key=len, reverse=True)[0]  # assume bigger is better

    # special logic for tiny set of outliers (DTX property rather than standard DT property)
    if raw_date.startswith("Published"):
        try:
            (year, month_start, day_start) = parse_published_date(raw_date)
            return f"{year}{month_start}{day_start}"
        except Exception as e:
            print("ERROR: Something went wrong in format_game_date...setting date to UNKNOWN in filename")
            print(f"raw_date={raw_date}")
            print("Something went wrong in format_game_date...")
            raw_date = "UNKNOWNDATE"

    # this is trash, but so is the raw data
    clean_date = raw_date.replace(delim, "")
    if ".." in raw_date:
        clean_date = clean_date.split("..")[0]
    elif "," in raw_date:
        clean_date = clean_date.split(",")[0]
    return clean_date

def get_game_date(metadata_dict: dict) -> str:
    """Yes, the catch-all is necessary, ask me how I know."""
    if "DT" in metadata_dict:
        return format_game_date(metadata_dict["DT"])
    elif "DTX" in metadata_dict:
        return format_game_date(metadata_dict["DTX"])
    return "UNKNOWNDATE"

def get_new_filename(filepath):
    metadata_dict = get_game_metadata_dict(filepath)
    (black_player_name, is_rengo) = format_player_name(metadata_dict.get('PB'))
    (white_player_name, _) = format_player_name(metadata_dict.get('PW'))
    game_date = get_game_date(metadata_dict)
    if is_rengo:
        return f'{game_date}-RENGO-Team {black_player_name}-Team {white_player_name}.sgf'
    return f'{game_date}-{black_player_name}-{white_player_name}.sgf'

def get_new_filepath(filepath):
    return DESTINATION_DIR + "/" + get_new_filename(filepath)

# TODO: move to helper?
def get_game_similarity_score(filepath_a: str, filepath_b: str) -> int:
    """
    Ignores filename and metadata. Returns score 0-100 based on % match of moves until divergence.
    If A & B have all the same moves except for move #45, then only the first 44 moves will be counted as the same.
    """
    num_same_moves = count_number_of_same_moves(filepath_a, filepath_b)
    num_total_moves = max(count_moves_in_a_game(filepath_a), count_moves_in_a_game(filepath_b))
    if num_same_moves == 0:
        return 0
    elif num_same_moves == num_total_moves:
        return 100
    else:
        return math.floor((num_same_moves / num_total_moves) * 100)

# def process_new_file(filepath: str) -> dict:
#     """
#     Imports a new file from SOURCE_DIR and processes it into DESTINATION_DIR.

#     Processing does the following:
#         - Copy game from SOURCE_DIR and rename to standard convention
#         - Matches game on existing games by date
#         - Quantify similarity to existing games

#     Returns dict w/ fields:
#         `game_type`
#         `matching_game_record`
#         `similarity_score`
#     """
#     result_dict = {}
#     print(f"Processing: {filepath}")

#     is_this_a_new_game = False
#     is_this_an_existing_game = False
#     is_this_game_suspiciously_similar = False

#     # copy source -> staging
#     shutil.copy(filepath, get_new_filepath(filepath))
#     filepath = get_new_filepath(filepath)  # update pointer

#     if PRO_DIR:
#         # ai prediction network
#         potential_matches = get_matching_games(get_new_filepath(filepath), PRO_DIR)
#         # TODO: remove the break from this for loop - need functionality to inform user if multiple games are highly similar
#         for potential_match in potential_matches:
#             if are_these_two_games_the_same(filepath, potential_match, min_num_same_moves=15):
#                 similarity_score = get_game_similarity_score(filepath, potential_match)
#                 result_dict['matching_game_record'] = potential_match

#                 if similarity_score == 100:
#                     is_this_an_existing_game = True
#                 else:
#                     is_this_game_suspiciously_similar = True

#                 break  # this is temporarily fine, but needs to be removed eventually. if there are multiple similar games, the user should be informed

#         if not (is_this_an_existing_game or is_this_game_suspiciously_similar):
#             is_this_a_new_game = True
#             similarity_score = 0

#         if is_this_an_existing_game:
#             os.remove(filepath)

#         result_dict['game_type'] = (is_this_a_new_game,
#                                     is_this_an_existing_game,
#                                     is_this_game_suspiciously_similar)
#         result_dict['similarity_score'] = similarity_score
#     else:
#         result_dict['game_type'] = (is_this_a_new_game,
#                                     is_this_an_existing_game,
#                                     is_this_game_suspiciously_similar)
    
#     return result_dict

def run_ai_prediction_network(filepath: str, result_dict: dict) -> dict:
    """A bunch of if-statements. Shhhhh."""
    if PRO_DIR == [] or PRO_DIR == ['']:
        return (None, None)

    if 'matching_game_records' not in result_dict:
        result_dict['matching_game_records'] = []

    potential_matches = get_matching_games(get_new_filepath(filepath), PRO_DIR)
    for pm in potential_matches:
        if are_these_two_games_the_same(filepath, pm, min_num_same_moves=15):
            similarity_score = get_game_similarity_score(filepath, pm)
            result_dict['matching_game_records'].append((pm, similarity_score))

    return result_dict

def process_new_file(filepath: str) -> dict:
    """
    Imports a new file from SOURCE_DIR and processes it into DESTINATION_DIR.

    Processing does the following:
        - Copy game from SOURCE_DIR and rename to standard convention
        - Matches game on existing games by date
        - Quantify similarity to existing games

    Returns dict w/ fields:
        `game_type`
        `matching_game_record`
        `similarity_score`
    """
    result_dict = {}
    print(f"Processing: {filepath}")

    is_this_a_new_game = False
    is_this_an_existing_game = False
    is_this_game_suspiciously_similar = False

    # copy source -> staging
    shutil.copy(filepath, get_new_filepath(filepath))
    filepath = get_new_filepath(filepath)  # update pointer

    result_dict = run_ai_prediction_network(filepath, result_dict)

    if result_dict["matching_game_records"] == []:
        is_this_a_new_game = True
    else:
        matching_games = result_dict["matching_game_records"]
        for mg in matching_games:
            (_, score) = mg
            if score == 100:
                is_this_an_existing_game = True
        if not is_this_an_existing_game:
            is_this_game_suspiciously_similar = True
    
    result_dict['game_type'] = (is_this_a_new_game,
                            is_this_an_existing_game,
                            is_this_game_suspiciously_similar)
    return result_dict

def main():
    filepaths_to_process = get_sgf_filepaths_for_source_dir()
    (num_new_games, num_existing_games, num_similar_games) = (0, 0, 0)
    mapping_filename_to_file_status = {}
    # mapping_filename_to_similarity_score = {}
    mapping_filename_to_matching_games = {}

    print("\nWelcome. Beginning process.")
    print(f"Total games to process: {len(filepaths_to_process)}")

    for fp in filepaths_to_process:
        result_dict = process_new_file(fp)
        mapping_filename_to_file_status[fp] = result_dict['game_type']
        # mapping_filename_to_similarity_score[fp] = result_dict['similarity_score']
        mapping_filename_to_matching_games[fp] = result_dict['matching_game_records']
        (new, exi, sim) = result_dict['game_type']

        num_new_games += int(new)
        num_existing_games += int(exi)
        num_similar_games += int(sim)

    print("\nProcess complete. Found the following:")
    print(f">>> {num_new_games} new games.")
    print(f">>> {num_existing_games} games you already have.")
    print(f">>> {num_similar_games} games that are very similar but not 100% - please review them.")

    for fp in mapping_filename_to_file_status:
        matching_games = mapping_filename_to_matching_games[fp]
        scores = [k[1] for k in matching_games]
        if any([s > 0 and s < 100 for s in scores]):
            # matching_games = mapping_filename_to_matching_games[fp]
            analyze_two_similar_games(fp, matching_games)


if __name__ == '__main__':
    main()
