from collections import Counter
from datetime import datetime
from helper import (
    analyze_two_similar_games,
    count_moves_in_a_game,
    count_number_of_same_moves,
    get_game,
    get_list_of_pro_filepaths,
    get_matching_games,
    are_these_two_games_the_same
)

import math
import os
import re
import shutil

# Source of data: https://homepages.cwi.nl/~aeb/go/games/

# I created this w/ the following goals in mind (added generalized funcs to helper.py):
# - for a game, are any moves missing?
# - for a game, how many total moves are the same? (currently only track until first diff)
# - for a game, get all pieces of metadata
# - for a game, give a % score on similarity to another game
# - for a dataset, tell me how many games are 100% the same

DESTINATION_DIR = "/Users/tarek/github/gogogo/staging"
PRO_DIR_ROOT = "/Users/tarek/github/gogogo/pro_games"

MAX_MOVES_IN_A_GAME = 400
SOURCE_DIR = "/Users/tarek/github/gogogo/bulk_datasets/AEB/Cho_Chikun"
PRO_DIR = ["/Users/tarek/github/gogogo/pro_games/Cho Chikun"]


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


def run_ai_prediction_network(filepath: str, list_of_existing_pro_filepaths: list, result_dict: dict) -> dict:
    """A bunch of if-statements. Shhhhh."""
    if list_of_existing_pro_filepaths == [] or list_of_existing_pro_filepaths == ['']:
        # return (None, None)
        result_dict['matching_game_records'] = []
        return result_dict

    if 'matching_game_records' not in result_dict:
        result_dict['matching_game_records'] = []

    potential_matches = get_matching_games(get_new_filepath(filepath), list_of_existing_pro_filepaths)
    for pm in potential_matches:
        if are_these_two_games_the_same(filepath, pm, min_num_same_moves=15):
            similarity_score = get_game_similarity_score(filepath, pm)
            result_dict['matching_game_records'].append((pm, similarity_score))

    return result_dict


def import_new_game(filepath: str, list_of_existing_pro_filepaths: list) -> dict:
    """
    Import a new game from SOURCE_DIR and process it into DESTINATION_DIR.

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
    is_this_a_new_game = False
    is_this_an_existing_game = False
    is_this_game_suspiciously_similar = False

    # copy to staging dir
    shutil.copy(filepath, get_new_filepath(filepath))
    filepath = get_new_filepath(filepath)  # update pointer

    result_dict = run_ai_prediction_network(filepath, list_of_existing_pro_filepaths, result_dict)

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


def collate_new_games_for_user_review(filepaths_to_process: list, list_of_existing_pro_filepaths: list, limit_n_games: int = 0) -> tuple:
    mapping_filename_to_file_status = {}
    mapping_filename_to_matching_games = {}

    limit_n_games = len(filepaths_to_process) if limit_n_games == 0 else limit_n_games
    print(f"Total games to process: {limit_n_games}")

    for fp in filepaths_to_process:
        try:
            result_dict = import_new_game(fp, list_of_existing_pro_filepaths)
            mapping_filename_to_file_status[get_new_filepath(fp)] = result_dict['game_type']
            mapping_filename_to_matching_games[get_new_filepath(fp)] = result_dict['matching_game_records']
        except Exception as e:
            print(f"we dun broke - skipping '{fp}'")
            # breakpoint()
            print(e)
            continue

    game_stats = Counter(mapping_filename_to_file_status.values())
    num_new = game_stats[(1, 0, 0)]
    num_existing = game_stats[(0, 1, 0)]
    num_similar = game_stats[(0, 0, 1)]

    print("Import complete:")
    print(f">>> {num_new} new games.")
    print(f">>> {num_existing} games you already have.")
    print(f">>> {num_similar} games that are very similar but not 100%.")

    return (mapping_filename_to_file_status, mapping_filename_to_matching_games)


def get_mapping_bulk_dataset_filepath_to_existing_pro_filepath():
    base_dataset = '/Users/tarek/github/gogogo/bulk_datasets/AEB'
    return {f'{base_dataset}/Shusaku': [f'{PRO_DIR_ROOT}/Honinbo Shusaku'],
            f'{base_dataset}/Cho_Chikun': [f'{PRO_DIR_ROOT}/Cho Chikun'],
            f'{base_dataset}/Gosei': [],
            f'{base_dataset}/Kisei': [],
            f'{base_dataset}/Female Honinbo': [],
            f'{base_dataset}/Meijin': [],
            f'{base_dataset}/Honinbo_Jowa': [f'{PRO_DIR_ROOT}/Honinbo Jowa'],
            f'{base_dataset}/Tengen': [],
            f'{base_dataset}/Go_Seigen': [f'{PRO_DIR_ROOT}/Go Seigen'],
            f'{base_dataset}/Ing': [],
            f'{base_dataset}/Honinbo': [],
            f'{base_dataset}/Ryusei': [],
            f'{base_dataset}/Judan': [],
            f'{base_dataset}/Oza': [],
            f'{base_dataset}/Shusai': [f'{PRO_DIR_ROOT}/Honinbo Shusai'],
            f'{base_dataset}/Dosaku': [f'{PRO_DIR_ROOT}/Honinbo Dosaku'],
            f'{base_dataset}/NHK': [],
            f'{base_dataset}/Nakamura_Sumire': [],
            f'{base_dataset}/Takagawa': [f'{PRO_DIR_ROOT}/Takagawa Kaku', f'{PRO_DIR_ROOT}/Takagawa Shukaku']}


def process_existing_games(aeb_pro: str, existing_games: list, list_of_existing_pro_filepaths: list):
    if len(existing_games) == 0:
        return

    matching_pro = list_of_existing_pro_filepaths[0].split('/')[-1]
    os.mkdir(f"{DESTINATION_DIR}/{matching_pro} - DUPLICATE")
    print(f"Created directory in STAGING: '{matching_pro} - DUPLICATE'")

    for eg in existing_games:
        eg_filename = eg.split("/")[-1]
        shutil.move(eg, f"{DESTINATION_DIR}/{matching_pro} - DUPLICATE/{eg_filename}")


def process_similar_games(aeb_pro: str, similar_games: list, list_of_existing_pro_filepaths: list, mapping_filename_to_matching_games: dict):
    if len(similar_games) == 0:
        return

    matching_pro = list_of_existing_pro_filepaths[0].split('/')[-1]
    os.mkdir(f"{DESTINATION_DIR}/{matching_pro} - SIMILAR BUT NOT DUPLICATE")
    print(f"Created directory in STAGING: '{matching_pro} - SIMILAR BUT NOT DUPLICATE'")

    # to do - improve analysis specificity:
    # case 1:
    #  len(game_a) > len(game_b) and 100% of game_b in game_a (or visa versa)
    #
    # case 2:
    #  1 move delta b/w game_a and game_b
    print(">>> Here's some analysis:")
    for sg in similar_games:
        matching_games = mapping_filename_to_matching_games[sg]
        analyze_two_similar_games(sg, matching_games)

        sg_filename = sg.split("/")[-1]
        shutil.move(sg, f"{DESTINATION_DIR}/{matching_pro} - SIMILAR BUT NOT DUPLICATE/{sg_filename}")


def process_new_games(aeb_pro: str, new_games: list, list_of_existing_pro_filepaths: list):
    if len(new_games) == 0:
        return

    if len(list_of_existing_pro_filepaths) == 0 or list_of_existing_pro_filepaths == [""]:
        print("It seems like you don't have a collection for this pro yet... using AEB naming convention")
        aeb_pro_name = aeb_pro.split("/")[-1]
        os.mkdir(f"{DESTINATION_DIR}/{aeb_pro_name}")

        for ng in new_games:
            ng_filename = ng.split("/")[-1]
            shutil.move(ng, f"{DESTINATION_DIR}/{aeb_pro_name}/{ng_filename}")

    elif len(list_of_existing_pro_filepaths) > 1:
        print("This pro has multiple collections... using AEB naming convention")
        aeb_pro_name = aeb_pro.split("/")[-1]
        os.mkdir(f"{DESTINATION_DIR}/{aeb_pro_name}")
        for ng in new_games:
            ng_filename = ng.split("/")[-1]
            shutil.move(ng, f"{DESTINATION_DIR}/{aeb_pro_name}/{ng_filename}")

    elif len(list_of_existing_pro_filepaths) == 1:
        collection_filepath = list_of_existing_pro_filepaths[0]
        matching_pro = list_of_existing_pro_filepaths[0].split('/')[-1]
        os.mkdir(f"{DESTINATION_DIR}/{matching_pro} - NEW")
        print(f"Created directory in STAGING: '{matching_pro}'")

        for ng in new_games:
            ng_filename = ng.split("/")[-1]
            shutil.move(ng, f"{DESTINATION_DIR}/{matching_pro} - NEW/{ng_filename}")


def pretty_print_enumerated_list(enumerated_list: list):
    for (i, thing) in enumerated_list:
        print(f">>> #{i}: {thing}")


def is_user_response__a_number(user_response: str) -> bool:
    return all([k.isdigit() for k in user_response])


def get_user_input__enumerated_list(enumerated_list: list, query_text: str = "which one would you like to use? > ") -> int:
    pretty_print_enumerated_list(enumerated_list)
    while True:
        user_answer = input(f"{query_text}").lower().strip()
        is_answer_an_acceptable_number = user_answer in [str(k[0]) for k in enumerated_list]
        is_answer_an_acceptable_choice = user_answer in [k[1].lower() for k in enumerated_list]
        if user_answer == "":
            print("Please answer")
        elif is_answer_an_acceptable_number:
            return [n for (i, n) in enumerated_list if i == user_answer][0].title()
        elif is_answer_an_acceptable_choice:
            return user_answer.title()
        elif is_user_response__a_number(user_answer) and not is_answer_an_acceptable_number:
            print("Pick a number in the list you idiot")
        elif not is_answer_an_acceptable_choice:
            print("Pick a valid entry you dumbshit")
        else:
            print("Invalid response, try again")


def get_user_input__yes_or_no(query_text: str = "what would you like to do? > ") -> int:
    while True:
        user_answer = input(f"{query_text}").lower().strip()
        if user_answer == "":
            print("Please answer")
        elif user_answer == 'y': return 1
        elif user_answer == 'n': return 0
        else:
            print("Invalid response, try again")


def get_user_input(query_text: str = "what would you like to do? > ") -> str:
    while True:
        user_answer = input(f"{query_text}").lower().strip()
        if user_answer == "":
            print("Please answer")
        return user_answer


def main():
    print("Welcome. Beginning process.")

    mapping_aeb_to_existing_pros = get_mapping_bulk_dataset_filepath_to_existing_pro_filepath()
    aeb_pros = sorted(mapping_aeb_to_existing_pros.keys())

    for aeb_pro in aeb_pros:
        list_of_existing_pro_filepaths = mapping_aeb_to_existing_pros[aeb_pro]
        filepaths_to_process = get_sgf_filepaths_for_source_dir(aeb_pro)

        # breakpoint()

        print(f"\nImporting '{'/'.join(aeb_pro.split('/')[-2:])}'...")
        new_games_for_user = collate_new_games_for_user_review(
                                filepaths_to_process,
                                list_of_existing_pro_filepaths)
        (mapping_filename_to_file_status, mapping_filename_to_matching_games) = new_games_for_user

        # to do: check raw count of pro games matches in source file compared to outputs
        # to do: check a few games dont exist manually
        # to do: check a few of each actually
        # to do: helper func to verify player name in title matches game info (sgf specs) player name
        # to do: for process_new_games logic, my filtering for identifying new vs existing games needs tightening

        new_games = [fp for fp in mapping_filename_to_file_status if mapping_filename_to_file_status[fp] == (1, 0, 0)]
        process_new_games(aeb_pro, new_games, list_of_existing_pro_filepaths)

        existing_games = [fp for fp in mapping_filename_to_file_status if mapping_filename_to_file_status[fp] == (0, 1, 0)]
        process_existing_games(aeb_pro, existing_games, list_of_existing_pro_filepaths)

        similar_games = [fp for fp in mapping_filename_to_file_status if mapping_filename_to_file_status[fp] == (0, 0, 1)]
        process_similar_games(aeb_pro, similar_games, list_of_existing_pro_filepaths, mapping_filename_to_matching_games)
        print(f"{len(similar_games)} similar games found.")

if __name__ == '__main__':
    main()
