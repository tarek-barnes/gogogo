import argparse
import os
import random
import subprocess

def get_list_of_pro_games(source_filepath: str) -> list:
    list_of_pro_games = []
    for (root, _, files) in os.walk(source_filepath):
        for file in files:
            if file.endswith('.sgf'):
                list_of_pro_games.append(os.path.join(root, file))
    return list_of_pro_games

def print_rec(rec: str) -> str:
    #  `rec` should be a filepath
    (main_player, filename) = rec.split('/')[-2:]
    print(f">>> Selected via: RANDOMLY WITH REPLACEMENT:")
    print(f">>>>>> It's a {main_player} game")
    print(f">>>>>> {filename}")

    subprocess.run('pbcopy', input=filename.encode(), check=True)
    print(">>> Filename copied to clipboard")

def main():
    # allow keywords (attack, fighting, aggressive, defense, defending, defensive, shape, fuseki, midgame, endgame, tesuji, etc.) to prioritize other professionals
    # allow for keyword to specify num_requests
    # allow for keyword to specify min_date, max_date, daterange?
    # allow for functionality to rate a rec

    # start_cli()?
    # destination_dir = get_destination_dir()
    # list_of_pro_game_filepaths = get_list_of_pro_games()
    # print_rec(random.select(list_of_pro_game_filepaths))

    parser = argparse.ArgumentParser(description="Parameters to filter by")
    parser.add_argument("--num", type=int, default=1, help="How many games")
    parser.add_argument("--player", type=str, help="Games from one specific player")
    parser.add_argument("--mindate", type=str, help="Games on/after a certain date")
    parser.add_argument("--maxdate", type=str, help="Games on/before a certain date")
    args = parser.parse_args()
    print(args)


    destination_dir = '/Users/tarek/github/gogogo/pro_games'
    list_of_pro_games = get_list_of_pro_games(destination_dir)
    choice = random.choice(list_of_pro_games)
    print_rec(choice)

if __name__ == '__main__':
    main()
