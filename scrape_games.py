from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from sgfmill import sgf
import os
import re
import shutil
import time

# players to scrape:
# Yang Dingxin
# Tang Weixing
# Xu Jiayang
# Byun Sangil
# Ichiriki Ryo (#11 ranked player)
# Ding Hao (#3 ranked player)

# env vars
DESTINATION_DIR = "/Users/tarek/github/gogogo/destination"
DOWNLOAD_DIR = "/Users/tarek/Downloads"
MAX_MOVES_IN_A_GAME = 400
# to do: accept a list of URLs instead of one at a time
URL_TO_SCRAPE = "https://ps.waltheri.net/database/player/Li%20Xuanhao/"

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


driver = webdriver.Chrome()
# url = "https://ps.waltheri.net/database/player/Li%20Xuanhao/"
url = URL_TO_SCRAPE
driver.get(url)
time.sleep(5)

print(">>> Clicking button to get list view")
button = driver.find_elements(By.XPATH, '//button[@class="btn btn-default" and @id="btn-table-view"]')
button[0].click()
time.sleep(10)

print(">>> Loading all the games on the page. This might take a few minutes...")
# keep scrolling to the bottom of the page and clicking "load more games"
load_more_games_button = driver.find_elements(By.XPATH, '//button[@class="btn btn-lg btn-default"]')

# For debugging
# load_more_games_button[0].click()

while len(load_more_games_button) > 0:
    try:
        load_more_games_button[0].click()
    except ElementNotInteractableException:
        load_more_games_button = []
    finally:
        time.sleep(10)

print(">>> Done loading all the games")

# List of dicts for keeping track of game metadata exposed in the table
games = []

# Find the table containing the game data
table = driver.find_element(By.XPATH, '//table[@class="table table-hover table-stripped"]')
rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # Skip the header row

print(">>> Collecting metadata for games")
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

# Start downloading the games, and renaming downloaded files to better format, one at a time (to avoid naming collisions)
download_game_buttons = driver.find_elements(By.XPATH, '//a[@class="download-link"]')
if len(download_game_buttons) != len(games):
    print(f">>> WARNING: Mismatch in game records ({len(games)}) vs. download links ({len(download_game_buttons)})")

for k in range(len(games)):
# for k in range(336, len(games)):
    game_record = games[k]
    download_button = download_game_buttons[k]
    download_button.click()
    time.sleep(5)

    download_destination_path = DOWNLOAD_DIR
    # download_destination_path = "/Users/tarek/Downloads"
    downloaded_file_path = download_destination_path + '/' + game_record['FileName']
    new_destination_path = DESTINATION_DIR
    # new_destination_path = "/Users/tarek/github/gogogo/destination"
    new_file_path = new_destination_path + '/' + game_record['FileName']

    # check if downloaded_file_path exists
    # if not, usually this means there is a (b) or (s) before a rank for one of the user's names, and the regex over-filtered it out
    # so let's just redefine the download_file_path
    if not os.path.isfile(downloaded_file_path):
        downloaded_file_path_alternatives = [k for k in os.listdir(download_destination_path) if (k.startswith(game_record['BPlayer']) or k.startswith(game_record['WPlayer']))]
        if len(downloaded_file_path_alternatives) == 1 or len(downloaded_file_path_alternatives) == 2:
            downloaded_file_path = download_destination_path + '/' + downloaded_file_path_alternatives[-1]

    try:
        # TO DO:
        # - if a game has the same name, don't replace the duplicate, rather, give it a new name!!


        if count_moves_in_a_game(downloaded_file_path) >= MAX_MOVES_IN_A_GAME:
            print(f">>> Skipping game #{k+1}/{len(games)}: {game_record['UpdatedFileName']} due to improper formatting (too many moves)")
            os.remove(downloaded_file_path)
            continue

        # Move the file to DESINATION_DIR
        shutil.move(downloaded_file_path, new_file_path)

        # Rename the file
        updated_file_path = new_destination_path + '/' + game_record['UpdatedFileName']
        os.rename(new_file_path, updated_file_path)
        print(f">>> Successfully downloaded {game_record['UpdatedFileName']} ----------------- game #{k+1}/{len(games)}")
        time.sleep(5)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(">>> An error occured trying to DESTINATION_DIR")
        print(f">>> Here's the error: {e}")
        breakpoint()

print(f">>> Done - grabbed {len(games)} games")
driver.quit()

