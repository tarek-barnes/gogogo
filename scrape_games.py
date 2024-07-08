from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
import os
import re
import shutil
import time

driver = webdriver.Chrome()
url = "https://ps.waltheri.net/database/player/Lee%20Sedol/"
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
    # print(f">>> currently in row: {row}")
    # breakpoint()
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
    print(f">>> Potential issue - mismatch in game records found ({len(games)}) vs. download links found ({len(download_game_buttons)})")

for k in range(len(games)):
# for k in range(889, len(games)):
    game_record = games[k]
    download_button = download_game_buttons[k]
    download_button.click()
    time.sleep(5)

    download_destination_path = "/Users/tarek/Downloads"
    downloaded_file_path = download_destination_path + '/' + game_record['FileName']
    new_destination_path = "/Users/tarek/github/gogogo/destination"
    new_file_path = new_destination_path + '/' + game_record['FileName']

    # check if downloaded_file_path exists
    # if not, usually this means there is a (b) or (s) before a rank for one of the user's names, and the regex over-filtered it out
    # so let's just refresh the download_file_path
    if not os.path.isfile(downloaded_file_path):
        download_file_path_alternatives = [k for k in os.listdir(download_destination_path) if (k.startswith(game_record['BPlayer']) or k.startswith(game_record['WPlayer']))]
        if len(download_file_path_alternatives) == 1:
            download_file_path = download_file_path_alternatives[0]

    try:
        # TO DO:
        # - if a game has the same name, don't replace the duplicate, rather, give it a new name!!

        # Move the file from ~/Downloads to ~/github/gogogo/destination
        shutil.move(downloaded_file_path, new_file_path)

        # Rename the file
        updated_file_path = new_destination_path + '/' + game_record['UpdatedFileName']
        os.rename(new_file_path, updated_file_path)
        time.sleep(5)

        print(f">>> Successfully downloaded {game_record['UpdatedFileName']} ----------------- game #{k+1}/{len(games)}")
    except Exception as e:
        print(">>> An error occured trying to rename/move the file from ~/Downloads -> destination directory")
        print(f">>> Here's the error: {e}")
        breakpoint()

print(f">>> Done - grabbed {len(games)} games")
driver.quit()

