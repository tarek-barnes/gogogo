from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from sgfmill import sgf

import logging
import os
import re
import shutil
import time

# BUG - should be 0 matches
# {'player': 'sakata', 'mindate': '2015', 'maxdate': None}
# >>> DATE INPUT IS JUST A YEAR
# >>> Found min date: 20150101
# >>> Selected via: RANDOMLY WITH REPLACEMENT:
# >>>>>> It's a Sakata Eio game
# >>>>>> /Users/tarek/github/gogogo/pro_games/Sakata Eio/19800807-Sakata Eio-Sekiyama Toshio.sgf
# >>> Thing copied to clipboard

# first game cant be downloaded? get a breakpoint (sometimes)
# can't quit browser at the end of scrape - get AttributeError: 'NoneType' object has no attribute 'quit'

# TO DO
# go seigen - classic player
# ueno asami - top tier woman player (not in weatheria?)

# env vars
DESTINATION_DIR = "/Users/tarek/github/gogogo/destination"
DOWNLOAD_DIR = "/Users/tarek/Downloads"
MAX_MOVES_IN_A_GAME = 400
SKIP_FIRST_N_GAMES = 0  # NOTE: use the counting number corresponding to the last successfully downloaded game
URL_TO_SCRAPE = "https://ps.waltheri.net/database/player/Kajiwara%20Takeo/"

def count_moves_in_a_game(sgf_file_path: str) -> int:
    with open(sgf_file_path, 'r') as f:
        raw_sgf = f.read()

    num_moves = 0
    game = sgf.Sgf_game.from_string(raw_sgf)
    for node in game.get_main_sequence():
        if node.has_property('B') or node.has_property('W'):
            num_moves += 1
    return num_moves

def fix_badly_formatted_sgf_file(sgf_file_path: str):
    with open(sgf_file_path, 'rb') as f:
        sgf_content = f.read()

    badly_formatted_game = sgf.Sgf_game.from_bytes(sgf_content)
    badly_formatted_game_as_str = badly_formatted_game.serialise().decode("utf-8")
    badly_formatted_game_as_list = badly_formatted_game_as_str.split("\n")
    badly_formatted_game_as_list = [k for k in badly_formatted_game_as_list if k]
    badly_formatted_game_as_list = [k.split(';') for k in badly_formatted_game_as_list]
    badly_formatted_game_as_flat_list = [j for k in badly_formatted_game_as_list for j in k if j]

    first_line = badly_formatted_game_as_flat_list[0]
    if first_line != '(':
        logging.error('Major error. File is not an SGF file. Canceling process.')
        return

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

def get_stats_player_winrates():
    # list of players = []
    # for each player:
    #  for each game: win+=1
    #  return win/total
    # some formatting
    pass

def start_driver(verbose: bool = False) -> webdriver.Chrome:
    return webdriver.Chrome()

def go_to_url_startpoint(driver: webdriver.Chrome, destination_url: str, verbose: bool = False) -> webdriver.Chrome:
    driver.get(destination_url)
    time.sleep(5)
    if verbose:
        logging.info(f"Got to {destination_url}")
    return driver

def load_all_records_on_page(driver: webdriver.Chrome, verbose: bool = False) -> webdriver.Chrome:
    if verbose:
        logging.info("Clicking button to switch to list view")

    button = driver.find_elements(By.XPATH, '//button[@class="btn btn-default" and @id="btn-table-view"]')
    button[0].click()
    time.sleep(10)

    if verbose:
        logging.info("Expanding list of games. This might take a few minutes...")

    # keep scrolling to the bottom of the page and clicking "load more games"
    load_more_games_button = driver.find_elements(By.XPATH, '//button[@class="btn btn-lg btn-default"]')
    while len(load_more_games_button) > 0:
        try:
            load_more_games_button[0].click()
        except ElementNotInteractableException:
            load_more_games_button = []
        finally:
            time.sleep(10)

    if verbose:
        logging.info("Done making all games visible")
    return driver

def get_games_metadata(driver: webdriver.Chrome, verbose: bool = False) -> (webdriver.Chrome, list):
    # List of dicts for keeping track of game metadata exposed in the table
    games = []

    # Find the table containing the game data
    table = driver.find_element(By.XPATH, '//table[@class="table table-hover table-stripped"]')
    rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # Skip the header row

    if verbose:
        logging.info("Retrieving games' metadata...")

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, 'td')

        b_player_name = cols[0].text.strip()
        b_player_name_no_rank = re.sub(r'\s*\([^)]*\)', '', b_player_name)
        w_player_name = cols[1].text.strip()
        w_player_name_no_rank = re.sub(r'\s*\([^)]*\)', '', w_player_name)
        date = cols[2].text.strip()
        date_no_dashes = date.replace('-', '')
        result = cols[4].text.strip()

        game_data = {
            'BPlayer': b_player_name_no_rank,
            'WPlayer': w_player_name_no_rank,
            'Date': date,
            # 'Event': cols[3].text.strip(),  # often empty
            'Result': result,
            'FileName': f"{b_player_name_no_rank} - {w_player_name_no_rank}.sgf",
            'UpdatedFileName': f"{date_no_dashes}-{b_player_name_no_rank}-{w_player_name_no_rank}.sgf",
        }
        games.append(game_data)
    if verbose:
        logging.info(f"Successfully retrieved {len(games)} metadata entries")
    return (driver, games)

def get_games_download_buttons(driver: webdriver.Chrome, verbose: bool = False) -> (webdriver.Chrome, list):
    if verbose:
        logging.info("Retrieving download buttons...")
    download_game_buttons = driver.find_elements(By.XPATH, '//a[@class="download-link"]')
    if verbose:
        logging.info(f"Successfully retrieved {len(download_game_buttons)} download buttons")
    return (driver, download_game_buttons)

def download_all_games(driver: webdriver.Chrome, skip_first_n_games: int = 0, verbose: bool = False) -> webdriver.Chrome:
    (driver, games_metadata) = get_games_metadata(driver, verbose)
    (driver, games_download_buttons) = get_games_download_buttons(driver, verbose)
    if len(games_metadata) != len(games_download_buttons):
        logging.error("Critical error: number of metadata entries doesn't match number of games to download - canceling process")
        return driver
    if skip_first_n_games > 0:
        logging.warning(f"WARNING: STARTING PROCESS FROM GAME #{skip_first_n_games + 1}")

    num_games_so_far = skip_first_n_games + 1
    num_total_games = len(games_metadata)
    for game in range(skip_first_n_games, num_total_games):
        driver = download_one_game(driver, games_metadata[game], games_download_buttons[game], num_games_so_far, num_total_games, verbose)
        num_games_so_far += 1
    return driver

def download_one_game(driver: webdriver.Chrome, metadata_record: dict, download_button: WebElement, num_games_so_far: int, num_total_games: int, verbose: bool) -> webdriver.Chrome:
    game_record = metadata_record
    try:
        download_button.click()
        time.sleep(5)

        download_destination_path = DOWNLOAD_DIR
        downloaded_file_path = download_destination_path + '/' + game_record['FileName']
        new_destination_path = DESTINATION_DIR
        new_file_path = new_destination_path + '/' + game_record['FileName']

        # check if downloaded_file_path exists
        # if not, usually this means there is a (b) or (s) before a rank for one of the user's names, and the regex over-filtered it out
        # so let's just redefine the download_file_path
        if not os.path.isfile(downloaded_file_path):
            downloaded_file_path_alternatives = [k for k in os.listdir(download_destination_path) if (k.startswith(game_record['BPlayer']) or k.startswith(game_record['WPlayer']))]
            if len(downloaded_file_path_alternatives) == 1 or len(downloaded_file_path_alternatives) == 2:
                downloaded_file_path = download_destination_path + '/' + downloaded_file_path_alternatives[-1]
            else:
                # try clicking the download button again... sometimes it fails to work
                time.sleep(2)
                print(">>> see if download button works the second time?")
                breakpoint()
                download_button.click()
                time.sleep(4)

        if count_moves_in_a_game(downloaded_file_path) >= MAX_MOVES_IN_A_GAME:
            logging.warning(f"Game #{num_games_so_far}: {game_record['UpdatedFileName']} is improperly formatted. Fixing...")
            fix_badly_formatted_sgf_file(downloaded_file_path)

        shutil.move(downloaded_file_path, new_file_path)

        updated_file_path = new_destination_path + '/' + game_record['UpdatedFileName']
        os.rename(new_file_path, updated_file_path)
        if verbose:
            logging.info(f"Downloaded game #{num_games_so_far}/{num_total_games}: {game_record['UpdatedFileName']}")
        time.sleep(1)
        return driver
    except FileNotFoundError as e:
        logging.error("File not found... here's the exact error:")
        logging.error(e)
        breakpoint()
        # return driver
    except Exception as e:
        print(">>> An unexpected error occurred while downloading a game")
        print(f">>> Here's the error: {e}")
        breakpoint()

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    driver = start_driver(verbose=True)
    driver = go_to_url_startpoint(driver, URL_TO_SCRAPE, verbose=True)
    driver = load_all_records_on_page(driver, verbose=True)
    driver = download_all_games(driver, skip_first_n_games=SKIP_FIRST_N_GAMES, verbose=True)
    driver.quit()

if __name__ == '__main__':
    main()
