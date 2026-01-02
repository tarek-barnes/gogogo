# from selenium import webdriver
# from selenium.common.exceptions import ElementNotInteractableException
# from selenium.webdriver.common.by import By
# from selenium.webdriver.remote.webelement import WebElement
from sgfmill import sgf

import os


### handling raw data files

def get_enumerated_game_record(sgf_file_path: str) -> list:
    """1-indexed."""
    (_, game_record) = get_game(sgf_file_path)
    return list(enumerate(game_record, start=1))


def get_game(sgf_file_path: str) -> list:
    metadata, moves = [], []

    with open(sgf_file_path, 'rb') as f:
        sgf_content = f.read()

    game = sgf.Sgf_game.from_bytes(sgf_content)

    for node in game.get_main_sequence():
        color, point = node.get_move()
        if color is not None:
            moves.append((color, point))
    
    for node in game.get_main_sequence():
        for key in [k for k in node.properties() if k not in ['B', 'W']]:
            raw_values = node.get_raw_list(key)
            for raw in raw_values:
                if isinstance(raw, bytes):
                    value = raw.decode("utf-8", errors="replace")
                else:
                    value = raw
                metadata.append((key, value))
    return (metadata, moves)


### matching games

def are_these_two_games_the_same(filepath_a: str, filepath_b: str, min_num_same_moves: int = 15) -> bool:
    num_same_moves = count_number_of_same_moves(filepath_a, filepath_b)
    if num_same_moves >= min_num_same_moves:
        return True
    return False


# todo: rename to match with 'count_moves_in_a_game' func syntax
#       also disambiguate... this is only UNTIL DIVERGENCE... but indicates otherwise
def count_number_of_same_moves(filepath_a: str, filepath_b: str) -> int:
    # in order
    num_same_moves = 0
    (a_moves, b_moves) = (get_enumerated_game_record(filepath_a), get_enumerated_game_record(filepath_b))
    num_max_same_moves = min(len(a_moves), len(b_moves))
    for k in range(num_max_same_moves):
        if a_moves[k] == b_moves[k]:
            num_same_moves += 1
        else:
            return num_same_moves
    return num_same_moves


# todo: rename to match with 'count_moves_in_a_game' func syntax
#       also disambiguate... this is ALL INTERSECTING MOVES, not "all same moves until a divergence"
def count_total_number_of_same_moves(filepath_a: str, filepath_b: str) -> int:
    num_same_moves = 0
    (a_moves, b_moves) = (get_enumerated_game_record(filepath_a), get_enumerated_game_record(filepath_b))
    num_max_same_moves = min(len(a_moves), len(b_moves))
    for k in range(num_max_same_moves):
        if a_moves[k] == b_moves[k]:
            num_same_moves += 1
    return num_same_moves


def get_matching_games(filepath: str, pro_filepaths: list) -> list:
    """
    Match one game with an option of pros, by date.
    Decided matching on names was too much given all the different spellings.

    `filename`: the game you want matched on others.
    `pro_filepath`: a path to a pro's games. can be a list of paths.
    """
    potential_matches = []
    for pro_fp in pro_filepaths:
        potential_matches += get_games_matching_date(filepath, pro_fp)

    if len(potential_matches) == 0:
        return []
    else:
        return potential_matches


### validation / analysis

def analyze_two_similar_games(filepath_a: str, filepaths_to_match: list) -> tuple:
    mapping_game_num_to_filepath = {}
    mapping_game_num_to_game_record = {}
    mapping_game_num_to_num_moves = {}
    mapping_game_num_to_num_same_moves_before_discrepancy = {}
    mapping_game_num_to_num_same_moves = {}

    welcome_text = "1 matching game was found:" if len(filepaths_to_match) == 1 else f"{len(filepaths_to_match)} matching games were found:"
    print(f"\n{welcome_text}")
    print(f"Game 1 (Primary Key): {filepath_a}")

    mapping_game_num_to_filepath[1] = filepath_a
    mapping_game_num_to_game_record[1] = get_enumerated_game_record(filepath_a)
    mapping_game_num_to_num_moves[1] = count_moves_in_a_game(filepath_a)

    welcome_game_counter = 1
    for (game, simimilarity_score) in filepaths_to_match:
        welcome_game_counter += 1
        mapping_game_num_to_filepath[welcome_game_counter] = game
        mapping_game_num_to_game_record[welcome_game_counter] = get_enumerated_game_record(game)
        mapping_game_num_to_num_moves[welcome_game_counter] = count_moves_in_a_game(game)
        mapping_game_num_to_num_same_moves_before_discrepancy[welcome_game_counter] = count_number_of_same_moves(filepath_a, game)
        mapping_game_num_to_num_same_moves[welcome_game_counter] = count_total_number_of_same_moves(filepath_a, game)
        print(f"Game {welcome_game_counter}: {game}")

    num_moves_text = f"Num moves ------------"
    for (game_num, num_moves) in sorted(mapping_game_num_to_num_moves.items(), key=lambda x: x[0]):
        num_moves_text += f" Game {game_num}: {num_moves}"
    print(num_moves_text)

    num_same_moves_before_discrepancy_text = f"First N same moves --- Game 1: NA "
    for (game_num, num_moves) in sorted(mapping_game_num_to_num_same_moves_before_discrepancy.items(), key=lambda x: x[0]):
        num_same_moves_before_discrepancy_text += f" Game {game_num}: {num_moves}"
    print(num_same_moves_before_discrepancy_text)

    num_same_moves_text = f"Num same moves ------- Game 1: NA "
    for (game_num, num_moves) in sorted(mapping_game_num_to_num_same_moves.items(), key=lambda x: x[0]):
        num_same_moves_text += f" Game {game_num}: {num_moves}"
    print(num_same_moves_text)


def count_moves_in_a_game(sgf_file_path: str) -> int:
    return len(get_enumerated_game_record(sgf_file_path))


def create_sgf_game_from_moves(output_path: str,
                               metadata: list,
                               game_moves: list,
                               board_size: int = 19):
    game = sgf.Sgf_game(board_size)
    root = game.get_root()

    for key, value in metadata:
        if value is None:
            continue

        # SGF expects a list of bytes
        if isinstance(value, str):
            raw_values = [value.encode("utf-8")]
        elif isinstance(value, bytes):
            raw_values = [value]
        else:
            # last resort
            raw_values = [str(value).encode("utf-8")]

        root.set_raw_list(key, raw_values)

    node = root
    for color, point in game_moves:
        node = node.new_child()
        node.set_move(color, point)

    with open(output_path, "wb") as f:
        f.write(game.serialise())


def fix_badly_formatted_sgf_file(sgf_file_path: str):
    """
    Waltheri.net sometimes has games which don't progress after a certain point.
    Usually they're very long (400+ moves) and will have repeat moves (i.e. Black plays twice).
    Once a repeat move is seen, it can be assumed the game is over.
    """
    metadata, moves = get_game(sgf_file_path)
    legal_moves = []
    last_color = None

    for color, point in moves:
        if color == last_color:
            break
        legal_moves.append((color, point))
        last_color = color
    
    output_filepath = f"/Users/tarek/nonsense/{sgf_file_path.split('/')[-1]}"
    create_sgf_game_from_moves(output_filepath, metadata, legal_moves)


def get_games_matching_date(filepath: str, pro_filepath: str) -> list:
    date_to_search = filepath.split("/")[-1].split("-")[0]
    return [pro_filepath + "/" + k for k in os.listdir(pro_filepath) if k.split("-")[0] == date_to_search]


def get_list_of_dates(filepath: str) -> list:
    filenames = os.listdir(filepath)
    return [k.split("-")[0] for k in filenames]


# refers to a move by black or white, and not metadata
def is_move_valid(move: str) -> bool:
    return (move.startswith('B[') or move.startswith('W['))


def is_single_piece_of_metadata(move: str) -> bool:
    return is_single_move(move) and not is_move_valid(move)


def is_multiple_pieces_of_info(move: str) -> bool:
    return (move.count('[') == move.count(']'))


def is_sgf_file_formatted_in_the_expected_way(sgf_file_path: str) -> bool:
    game = get_game_record(sgf_file_path)
    return game[0] == '('


def is_single_and_valid_move(move: str) -> bool:
    return is_single_move(move) and is_move_valid(move)


def is_single_move(move: str) -> bool:
    return move.count('[') == 1 and move.count(']') == 1
