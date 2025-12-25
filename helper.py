from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from sgfmill import sgf

import os

def count_moves_in_a_game(sgf_file_path: str) -> int:
    with open(sgf_file_path, 'r') as f:
        raw_sgf = f.read()

    num_moves = 0
    game = sgf.Sgf_game.from_string(raw_sgf)
    for node in game.get_main_sequence():
        if node.has_property('B') or node.has_property('W'):
            num_moves += 1
    return num_moves

def is_sgf_file_formatted_in_the_expected_way(sgf_file_path: str) -> bool:
    game = get_game_record_as_string(sgf_file_path)
    return game[0] == '('

def fix_badly_formatted_sgf_file(sgf_file_path: str):
    """
    Waltheri.net sometimes has games which don't progress after a certain point.
    Usually they're very long (400+ moves) and will have repeat moves (i.e. Black plays twice).
    Once a repeat move is seen, it can be assumed the game is over.
    """
    badly_formatted_game_as_str = get_game_record_as_string(sgf_file_path)
    badly_formatted_game_as_list = badly_formatted_game_as_str.split("\n")
    badly_formatted_game_as_list = [k for k in badly_formatted_game_as_list if k]
    badly_formatted_game_as_list = [k.split(';') for k in badly_formatted_game_as_list]
    badly_formatted_game_as_flat_list = [j for k in badly_formatted_game_as_list for j in k if j]

    first_line = badly_formatted_game_as_flat_list[0]

    os.remove(sgf_file_path)

    with open(sgf_file_path, 'w') as f:
        f.write(f"{first_line}\n")  # don't want the file to start with ;
        move_num = 1
        have_prefs_been_set = False
        expected_next_mover = 'B'
        for line in badly_formatted_game_as_flat_list[1:]:
            if (line.startswith('B') or line.startswith('W')):
                current_mover = 'B' if line.startswith('B') else 'W'
                #  this means one side has played two moves in a row, which is illegal
                if current_mover != expected_next_mover:
                    f.write(")")
                    break
                f.write(f";{line}\n")
                expected_next_mover = 'W' if expected_next_mover == 'B' else 'B'
                move_num += 1
            else:
                if not have_prefs_been_set:
                    f.write(f";{line}\n")
                    have_prefs_been_set = True
                else:
                    f.write(f"{line}\n")

def get_game_record_as_string(sgf_file_path: str) -> str:
    with open(sgf_file_path, 'rb') as f:
        sgf_content = f.read()
    game = sgf.Sgf_game.from_bytes(sgf_content)
    return game.serialise().decode("utf-8")

def get_list_of_dates(filepath: str) -> list:
    filenames = os.listdir(filepath)
    return [k.split("-")[0] for k in filenames]
