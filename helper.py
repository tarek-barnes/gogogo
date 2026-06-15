from sgfmill import sgf

import os

PRO_DIR_ROOT = "/Users/tarek/github/gogogo/pro_games"

# to do:
# - email myself professional game record
# - load games into database
#  > games
#  > game_sources
#  > players
#  > player_aliases
#  > game_players (who is black vs white for a game_id)
#  > game_metadata


# i want to add functionality that covers all bases for go games
# so just to describe those different bases:
# - primitives can refer to helper funcs which do basic board manipulation (also parse_sgf)
# - manipulation can refer to those which change the board or add semantic meaning to it (e.g. get_all_symmetries)
# - fingerprinting can refer to bookkeeping board states and game records
# - validation can refer to finding bad records (e.g. consecutive same-player moves)
# - metadata can refer to user-friendly info handling/storage (e.g. normalize_player_name)
# - analysis can refer to comparing games (e.g. deduplication)
# - eventually: ingestion pipeline 
# - eventually: reporting, data health

# currently being used:
#     analyze_two_similar_games,
#     count_moves_in_a_game,
#     count_number_of_same_moves,
#     get_game,
#     get_list_of_pro_filepaths,
#     get_matching_games,
#     are_these_two_games_the_same

# to do:
# Board Primitives

# apply_move(board, move) → new board state with captures applied
# get_liberties(board, group) → liberty count for a connected group
# get_connected_group(board, coordinate) → flood fill from a stone
# remove_captures(board, move) → returns board with captured stones removed
# detect_ko(board, move, board_history) → simple and superko variants
# is_legal_move(board, move, board_history) → combines liberty and ko checks
# score_board(board, ruleset) → Chinese vs Japanese scoring

# Symmetry & Canonicalization

# rotate_board(board, n) → 90° rotation n times
# reflect_board(board, axis) → horizontal, vertical, diagonal
# get_all_symmetries(board) → all 8 transformations
# canonical_orientation(board) → lexicographically smallest of the 8
# transform_move(move, symmetry) → apply a symmetry transform to a coordinate
# canonical_game_sequence(move_list) → full game as canonical board states

# Fingerprinting

# position_fingerprint(board) → hash of canonical board state
# game_fingerprint(move_list) → hash of full canonical sequence
# prefix_fingerprint(move_list, n) → fingerprint at move n, for AI cache keys
# fingerprint_all_positions(move_list) → returns fingerprint at every move, used for position-level AI caching

# Validation

# validate_sgf(path) → top-level validator, calls everything below
# validate_move_legality(board_history, move_list) → checks every move is legal
# validate_player_alternation(move_list) → catches consecutive same-color moves
# validate_metadata_completeness(metadata) → flags missing komi, ruleset, result, players
# validate_result_consistency(move_list, result) → e.g. game ends at move 50 but result says resignation at move 200
# validate_board_size(sgf) → confirm it's actually 19x19 (or flag 9x9, 13x13 explicitly)

# Metadata Extraction

# extract_metadata(sgf) → players, ranks, date, komi, result, ruleset, event
# normalize_player_name(name) → handles encoding differences, alternate romanizations
# detect_ruleset(sgf) → infer from metadata or source if not explicit
# extract_move_timestamps(sgf) → if time data exists, useful for game quality signals

# Similarity & Deduplication

# find_common_prefix(move_list_a, move_list_b) → index where games first diverge
# similarity_score(move_list_a, move_list_b) → float 0–1 based on common prefix length relative to total
# is_prefix_game(move_list_a, move_list_b) → one game is a truncated version of the other
# find_duplicate_candidates(fingerprint_db) → exact match lookup
# find_similar_candidates(fingerprint_db, threshold) → near-duplicate clustering
# classify_discrepancy(move_list_a, move_list_b) → single divergence vs scattered vs prefix

# Ingestion Pipeline

# ingest_sgf(path, db, log) → orchestrates parse → validate → canonicalize → fingerprint → store
# batch_ingest(directory, db, log) → runs ingest_sgf across all files with error isolation
# resolve_duplicate(game_a, game_b, policy) → applies your tiered deduplication logic
# write_ingestion_log(event, path, details) → structured JSONL logging

# Reporting & Data Health

# generate_health_report(db) → summary of validation failures, duplicates, missing metadata
# diff_games(move_list_a, move_list_b) → move-by-move diff output
# estimate_game_quality(sgf) → composite score flagging short games, missing data, suspicious patterns
# cluster_by_opening(fingerprint_db, depth) → group games by shared prefix up to move N, useful early signal for joseki work later





### BOARD PRIMITIVES

def extract_game_moves_from_filepath(sgf_filepath) -> list:
    """Returns list of coords. e.g.: [((15, 16), (15, 3), ...)]"""
    (_, moves) = extract_raw_game_data_from_filepath(sgf_filepath)
    return moves

def extract_raw_game_data_from_filepath(sgf_file_path: str) -> tuple:
    """Returns (metadata, moves) where each entry is a list."""
    metadata, moves = [], []

    with open(sgf_file_path, 'rb') as f:
        sgf_content = f.read()

    game = sgf.Sgf_game.from_bytes(sgf_content)

    for node in game.get_main_sequence():
        color, point = node.get_move()
        if color is not None:
            moves.append(point)
    
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

# to do: format player name to include rank
# to do: add AB/AW - in case handicap? verify this doesn't break 'moves'
# to do: figure out comments
# to do: add file format FF
# to do: add time limit TM
# chicken
def parse_sgf(sgf_filepath: str) -> dict:
    """Returns a dict of parsed game data."""
    (metadata, moves) = extract_raw_game_data_from_filepath(sgf_filepath)
    metadata_dict = {k: v for (k, v) in metadata}

    return {
        "moves": moves,
        "num_moves": len(moves),
        "black_player": parse_metadata_black_player(metadata_dict),
        "white_player": parse_metadata_white_player(metadata_dict),
        "event": parse_metadata_event(metadata_dict),
        "round_num": parse_metadata_round_num(metadata_dict),
        "date": parse_metadata_date(metadata_dict),
        "board_size": parse_metadata_board_size(metadata_dict),
        "komi": parse_metadata_komi(metadata_dict),
        "handicap": parse_metadata_handicap(metadata_dict),
        "result": parse_metadata_game_result(metadata_dict),
        "ruleset": parse_metadata_ruleset(metadata_dict),
        "raw_metadata": metadata
    }



### METADATA

def extract_raw_metadata_dict_from_filepath(sgf_filepath) -> dict:
    """Returns dict s.t. keys are properties described here: https://en.wikipedia.org/wiki/Smart_Game_Format"""
    (metadata, _) = extract_raw_game_data_from_filepath(sgf_filepath)
    return {k: v for (k, v) in metadata}

def is_black_player_name_included_in_metadata(metadata: dict) -> bool:
    return 'PB' in metadata

def is_black_player_rank_included_in_metadata(metadata: dict) -> bool:
    return 'BR' in metadata

def is_white_player_name_included_in_metadata(metadata: dict) -> bool:
    return 'PW' in metadata

def is_white_player_rank_included_in_metadata(metadata: dict) -> bool:
    return 'WR' in metadata

def is_board_size_included_in_metadata(metadata: dict) -> bool:
    return 'SZ' in metadata

def is_komi_included_in_metadata(metadata: dict) -> bool:
    return 'KM' in metadata

def is_handicap_included_in_metadata(metadata: dict) -> bool:
    return 'HA' in metadata

def is_event_included_in_metadata(metadata: dict) -> bool:
    return 'EV' in metadata

def is_round_num_included_in_metadata(metadata: dict) -> bool:
    return 'RO' in metadata

def is_date_included_in_metadata(metadata: dict) -> bool:
    return 'DT' in metadata

def is_game_result_included_in_metadata(metadata: dict) -> bool:
    return 'RE' in metadata

def is_ruleset_included_in_metadata(metadata: dict) -> bool:
    return 'RU' in metadata

def is_application_source_included_in_metadata(metadata: dict) -> bool:
    return 'AP' in metadata

def parse_metadata_black_player(metadata: dict) -> str:
    return metadata['PB'] if is_black_player_name_included_in_metadata(metadata) else ''

def parse_metadata_white_player(metadata: dict) -> str:
    return metadata['PW'] if is_black_player_name_included_in_metadata(metadata) else ''

def parse_metadata_event(metadata: dict) -> str:
    return metadata['EV'] if is_event_included_in_metadata(metadata) else ''

def parse_metadata_board_size(metadata: dict) -> int:
    return metadata['SZ'] if is_board_size_included_in_metadata(metadata) else 0

def parse_metadata_komi(metadata: dict) -> str:
    return metadata['KM'] if is_komi_included_in_metadata(metadata) else ''

def parse_metadata_handicap(metadata: dict) -> int:
    return metadata['HA'] if is_handicap_included_in_metadata(metadata) else 0

def parse_metadata_game_result(metadata: dict) -> str:
    return metadata['RE'] if is_game_result_included_in_metadata(metadata) else ''

def parse_metadata_ruleset(metadata: dict) -> str:
    return metadata['RU'] if is_ruleset_included_in_metadata(metadata) else ''

def parse_metadata_date(metadata: dict) -> str:
    return metadata['DT'] if is_date_included_in_metadata(metadata) else ''

def parse_metadata_round_num(metadata: dict) -> int:
    return metadata['RO'] if is_round_num_included_in_metadata(metadata) else 0


# def normalize_player_name(name):
#     pass


### ANALYSIS

def get_list_of_all_pros_in_collection() -> list:
    return os.listdir(PRO_DIR_ROOT)

def is_this_a_pro_we_have_in_our_collection(pro_name: str) -> bool:
    return pro_name in get_list_of_all_pros_in_collection()

def get_list_of_all_pros_games_in_collection(pro_name: str) -> list:
    if not is_this_a_pro_we_have_in_our_collection(pro_name):
        return []
    return os.listdir(f"{PRO_DIR_ROOT}/{pro_name}")

def get_list_of_all_games_between_two_pro_players_in_collection(pro_name_one: str, pro_name_two: str) -> list:
    if not (is_this_a_pro_we_have_in_our_collection(pro_name_one) and is_this_a_pro_we_have_in_our_collection(pro_name_one)):
        return []
    elif (is_this_a_pro_we_have_in_our_collection(pro_name_one) or is_this_a_pro_we_have_in_our_collection(pro_name_one)):
        our_pro = pro_name_one if is_this_a_pro_we_have_in_our_collection(pro_name_one) else pro_name_two
        untracked_pro = pro_name_one if our_pro != pro_name_one else pro_name_two
        our_pro_games = get_list_of_all_pros_games_in_collection(our_pro)
        if any([k for k in our_pro_games if untracked_pro in k]):
            return [k for k in our_pro_games if untracked_pro in k]
        # to do: probably worth adding more filters here
        else:
            return []
    (a, b) = (get_list_of_all_pros_games_in_collection(pro_name_one), get_list_of_all_pros_games_in_collection(pro_name_two))
    (a, b) = (set(a), set(b))
    return list(a&b)
















############################################################################################
# everything below here needs to be refactored carefully later... generalizations above this line
############################################################################################

### to do: handling raw data files

def get_enumerated_game_record(sgf_file_path: str) -> list:
    """1-indexed."""
    (_, game_record) = get_game(sgf_file_path)
    return list(enumerate(game_record, start=1))


# parse_sgf will deprecate this
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
    
    create_sgf_game_from_moves(sgf_file_path, metadata, legal_moves)


def get_games_matching_date(filepath: str, pro_filepath: str) -> list:
    date_to_search = filepath.split("/")[-1].split("-")[0]
    is_date_to_search_only_a_year = len(date_to_search) == 4
    is_date_to_search_only_a_year_and_month = len(date_to_search) > 4 and len(date_to_search) <= 6
    exact_date_matches = []
    fuzzy_date_matches = []

    for pro_fn in os.listdir(pro_filepath):
        pro_fn_date = pro_fn.split("-")[0]
        does_pro_game_only_have_a_year = len(pro_fn_date) == 4
        does_pro_game_only_have_a_year_and_month = len(pro_fn_date) > 4 and len(pro_fn_date) <= 6
        filepath = f"{pro_filepath}/{pro_fn}"
        if pro_fn.split("-")[0] == date_to_search:
            exact_date_matches.append(filepath)
        # what if filepath is 19981121-Tanaka Masato-Cho Chikun.sgf
        #      and pro_filepath is 1998-Tanaka Masato-Cho Chikun.sgf
        elif (does_pro_game_only_have_a_year and date_to_search.startswith(pro_fn_date)):
            fuzzy_date_matches.append(filepath)
        # what if filepath is 19981121-Tanaka Masato-Cho Chikun.sgf
        #      and pro_filepath is 199811-Tanaka Masato-Cho Chikun.sgf
        elif (does_pro_game_only_have_a_year_and_month and date_to_search.startswith(pro_fn_date)):
            fuzzy_date_matches.append(filepath)
        # what if filepath is 1998-Tanaka Masato-Cho Chikun.sgf
        #      and pro_filepath is 19981121-Tanaka Masato-Cho Chikun.sgf
        elif (is_date_to_search_only_a_year and pro_fn_date.startswith(date_to_search)):
            fuzzy_date_matches.append(filepath)
        # what if filepath is 1998-Tanaka Masato-Cho Chikun.sgf
        #      and pro_filepath is 19981121-Tanaka Masato-Cho Chikun.sgf
        elif (is_date_to_search_only_a_year_and_month and pro_fn_date.startswith(date_to_search)):
            fuzzy_date_matches.append(filepath)
    return exact_date_matches + fuzzy_date_matches


def get_list_of_dates(filepath: str) -> list:
    filenames = os.listdir(filepath)
    return [k.split("-")[0] for k in filenames]


def get_list_of_pro_filepaths() -> list:
    return sorted([f"{PRO_DIR_ROOT}/{k}" for k in os.listdir(PRO_DIR_ROOT)])


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
