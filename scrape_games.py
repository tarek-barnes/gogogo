from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from sgfmill import sgf

import logging
import os
import re
import shutil
import time

# players to scrape:
# Tang Weixing

# Xu Jiayang (#17)
# Byun Sangil (#22)
# Ichiriki Ryo (#11 ranked player)
# Ding Hao (#3 ranked player)

# env vars
DESTINATION_DIR = "/Users/tarek/github/gogogo/destination"
DOWNLOAD_DIR = "/Users/tarek/Downloads"
MAX_MOVES_IN_A_GAME = 400
SKIP_FIRST_N_GAMES = 0  # helpful if a scrape fails mid-way through
# to do: accept a list of URLs instead of one at a time
URL_TO_SCRAPE = "https://ps.waltheri.net/database/player/Tang%20Weixing/"

def count_moves_in_a_game(sgf_file_path: str) -> int:
    with open(sgf_file_path, 'r') as f:
        raw_sgf = f.read()

    game = sgf.Sgf_game.from_string(raw_sgf)
    num_moves = 0

    for node in game.get_main_sequence():
        if node.has_property('B') or node.has_property('W'):
            num_moves += 1
    return num_moves

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
    return (webdriver.Chrome, download_game_buttons)

def download_all_games(driver: webdriver.Chrome, skip_first_n_games: int = 0, verbose: bool = False) -> webdriver.Chrome:
    (driver, games_metadata) = get_games_metadata(driver, verbose)
    (driver, games_download_buttons) = get_games_download_buttons(driver, verbose)
    if len(games_metadata) != len(games_download_buttons):
        logging.error(">>> Critical error: number of metadata entries doesn't match number of games to download - canceling process")
        return webdriver.Chrome

    num_games_so_far = skip_first_n_games + 1
    num_total_games = len(games_metadata)
    for game in range(skip_first_n_games, num_total_games):
        driver = download_one_game(driver, games_metadata[game], games_download_buttons[game], num_games_so_far, num_total_games, verbose)
        num_games_so_far += 1
    return driver

def download_one_game(driver: webdriver.Chrome, metadata_record: dict, download_button: str, num_games_so_far: int, num_total_games: int, verbose: bool) -> webdriver.Chrome:
    # to do: change download_button to correct type, a selenium element
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
            logging.warning(f"Skipping game #{num_games_so_far}: {game_record['UpdatedFileName']} due to improper formatting (too many moves)")
            os.remove(downloaded_file_path)
            return driver

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
