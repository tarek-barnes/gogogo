import argparse
import calendar
import os
import random
import subprocess
import sys

from collections import Counter
from datetime import datetime

# bug
# ipython randomly_select_pro_game.py -- --player='iyama yuuta' --mindate='2001 12 11'
# {'player': 'iyama yuuta', 'mindate': '2001 12 11', 'maxdate': None}
# >>> DATE INPUT IS A DAY & MONTH & YEAR
# >>> DOESNT CONTAIN MONTH NAME - ONLY NUM
# >>> Found min date: 2011122001
# >>> Selected via: RANDOMLY WITH REPLACEMENT:
# >>>>>> It's a Iyama Yuuta game
# >>>>>> /Users/tarek/github/gogogo/pro_games/Iyama Yuuta/20130110-Iyama Yuuta-Takao Shinji.sgf
# >>> Thing copied to clipboard

def get_list_of_pro_games(source_filepath: str, args_dict: dict) -> list:
    list_of_pro_games = []
    multiple_source_filepaths = []

    #  to do: generalize this later
    if args_dict['maxdate']:
        matching_max_date = match_user_input__date(args_dict['maxdate'], is_max_date=True)
        print(f">>> Found max date: {matching_max_date}")
    if args_dict['mindate']:
        matching_min_date = match_user_input__date(args_dict['mindate'], is_max_date=False)
        print(f">>> Found min date: {matching_min_date}")
    if 'player' in args_dict:
         matching_pros = match_user_input__pro_player(args_dict['player'], get_list_of_pro_players(source_filepath))
         if type(matching_pros) == str:
             source_filepath += "/"
             source_filepath += matching_pros
         elif type(matching_pros) == list:
             for mp in matching_pros:
                 this_filepath = source_filepath
                 this_filepath += "/"
                 this_filepath += mp
                 multiple_source_filepaths.append(this_filepath)

    # to do: delete me later... only one root filepath used to be accepted
    if not multiple_source_filepaths:
        for (root, _, files) in os.walk(source_filepath):
            for file in files:
                if file.endswith('.sgf'):
                   list_of_pro_games.append(os.path.join(root, file))
    else:
        for fp in multiple_source_filepaths:
            for (root, _, files) in os.walk(fp):
                for file in files:
                    if file.endswith('.sgf'):
                        list_of_pro_games.append(os.path.join(root, file))


    list_of_pro_games = list(set(list_of_pro_games))
    list_of_pro_games_filtered_by_date = []
    if args_dict['mindate'] and args_dict['maxdate']:
        min_date = matching_min_date
        max_date = matching_max_date
        for pro_game in list_of_pro_games:
            filename = pro_game.split("/")[-1]
            filename_date = filename.split('-')[0]
            if filename_date >= min_date and filename_date <= max_date:
                list_of_pro_games_filtered_by_date.append(pro_game)
    elif args_dict['mindate']:
        min_date = matching_min_date
        for pro_game in list_of_pro_games:
            filename = pro_game.split("/")[-1]
            filename_date = filename.split('-')[0]
            if filename_date >= min_date:
                list_of_pro_games_filtered_by_date.append(pro_game)
    elif args_dict['maxdate']:
        max_date = matching_max_date
        for pro_game in list_of_pro_games:
            filename = pro_game.split("/")[-1]
            filename_date = filename.split('-')[0]
            if filename_date <= max_date:
                list_of_pro_games_filtered_by_date.append(pro_game)
    list_of_pro_games = list_of_pro_games_filtered_by_date if list_of_pro_games_filtered_by_date else list_of_pro_games
    return list_of_pro_games


def get_current_year() -> int:
    return datetime.now().year

def verify_user_input__date(user_input: str) -> bool:
    #  loose checks
    return (type(user_input) == str and all([(k.isdigit() or k.isalpha() or k.isspace() or k in "/-") for k in user_input]))

def verify_user_input__date_year(user_input: str) -> bool:
    if len(user_input) == 2:
        return True
    elif len(user_input) == 4:
        return ((user_input.startswith("1") or user_input.startswith("2")) and int(user_input) <= get_current_year())

def verify_user_input__date_month(user_input: str) -> bool:
    if len(user_input) == 1:
        return True if int(user_input) > 0 else False
    elif len(user_input) == 2:
        return True if int(user_input) <= 12 else False
    elif user_input in get_list_of_month_names(are_month_names_abbreviated = False):
        return True
    elif user_input in get_list_of_month_names(are_month_names_abbreviated = True):
        return True
    return False

def verify_user_input__date_day(user_input: str) -> bool:
    if len(user_input) == 1:
        return True if int(user_input) > 0 else False
    elif len(user_input) == 2:
        return True if int(user_input) <= 31 else False

def verify_user_input__date_month_year(user_input: str) -> bool:
    return (len(user_input) >= 4 and  # e.g. 1/04 as jan 2004
            len(user_input) < 15 and  # e.g. september 2022
            (user_input.count("/") == 1 or user_input.count("-") == 1 or user_input.count(" ") == 1) and
            (any([(k in user_input) for k in "1234567890"])))

def verify_user_input__date_day_month_year(user_input: str) -> bool:
    return (len(user_input) >= 8 and len(user_input) < 18 and (user_input.count("/") == 2 or user_input.count("-") == 2 or user_input.count(" ") == 2))

def match_user_input__date_year(user_input: str) -> str:
    if not verify_user_input__date_year(user_input):
        print(">>> Error: the provided year is not understandable")
        return

    if len(user_input) == 2:
        current_year = get_current_year()
        if int(user_input) > int(str(current_year)[2:]):
            return '19' + user_input
        else:
            return '20' + user_input
    return user_input

def match_user_input__date_month_year(user_input: str) -> (str, str):
    month_to_num_mapping = get_mapping_month_name_to_num(are_month_names_abbreviated=False)
    month_abbr_to_num_mapping = get_mapping_month_name_to_num(are_month_names_abbreviated=True)
    non_num_or_letter_chars = list(set([k for k in user_input if (not k.isdigit() and not k.isalpha())]))
    inferred_delimiter = non_num_or_letter_chars[0] if len(non_num_or_letter_chars) == 1 else default_delimiter
    does_user_input_contain_a_month_name = (any([(k.lower() in user_input) for k in month_to_num_mapping]) or any([(k.lower() in user_input) for k in month_abbr_to_num_mapping]))
    does_user_input_start_with_a_month_name = (user_input[0].isalpha() and does_user_input_contain_a_month_name)

    if user_input.count(inferred_delimiter) > 1:
        print(">>> something's weird about this user input... looks like a month year but has too many delims")
        print(user_input)

    # letters are in user_input
    if does_user_input_contain_a_month_name:
        if does_user_input_start_with_a_month_name:
            (inferred_month, inferred_year) = user_input.split(inferred_delimiter)
            inferred_month = inferred_month.lower()
            if inferred_month in month_to_num_mapping:
                inferred_month_num = month_to_num_mapping[inferred_month]
            elif inferred_month in month_abbr_to_num_mapping:
                inferred_month_num = month_abbr_to_num_mapping[inferred_month]
        else:
            (inferred_year, inferred_month) = user_input.split(inferred_delimiter)
            inferred_month = inferred_month.lower()
            if inferred_month in month_to_num_mapping:
                inferred_month_num = month_to_num_mapping[inferred_month]
            elif inferred_month in month_abbr_to_num_mapping:
                inferred_month_num = month_abbr_to_num_mapping[inferred_month]

        inferred_month_num = str(inferred_month_num)
        inferred_month_num = "0" + inferred_month_num if len(inferred_month_num) == 1 else inferred_month_num
        inferred_year = match_user_input__date_year(inferred_year)
        return (inferred_month_num, inferred_year)

    # only nums are in user_input
    else:
        (first_num, second_num) = user_input.split(inferred_delimiter)
        if len(first_num) == 4:
            (inferred_month, inferred_year) = (second_num, first_num)
        elif len(second_num) == 4:
            (inferred_month, inferred_year) = (first_num, second_num)
        elif len(first_num) == 1:
            (inferred_month, inferred_year) = (first_num, second_num)
        elif len(second_num) == 1:
            (inferred_month, inferred_year) = (second_num, first_num)
        elif int(first_num) <= 12 and int(second_num) > 12:
            (inferred_month, inferred_year) = (first_num, second_num)
        elif int(second_num) <= 12 and int(first_num) > 12:
            (inferred_month, inferred_year) = (second_num, first_num)
        # if both nums are <= 12, assume the year starts with '0' (i.e. 09 --> 2009)
        elif len(first_num) == 2 and len(second_num) == 2 and first_num.startswith("0"):
            (inferred_month, inferred_year) = (second_num, first_num)
        else:
            # how to figure out which one is a year if they both have 2 digits?
            print(f">>> Issue with date matcher - we have a difficult use-case: {user_input}... canceling process")
            return

        inferred_month_num = "0" + inferred_month if len(inferred_month) == 1 else inferred_month
        inferred_year = match_user_input__date_year(inferred_year)
        return (inferred_month_num, inferred_year)

def match_user_input__date_day_month_year(user_input: str) -> (str, str, str):
    current_year = get_current_year()
    month_to_num_mapping = get_mapping_month_name_to_num(are_month_names_abbreviated=False)
    month_abbr_to_num_mapping = get_mapping_month_name_to_num(are_month_names_abbreviated=True)

    non_num_or_letter_chars = list(set([k for k in user_input if (not k.isdigit() and not k.isalpha())]))
    inferred_delimiter = non_num_or_letter_chars[0] if len(non_num_or_letter_chars) == 1 else default_delimiter
    does_user_input_contain_a_month_name = (any([(k.lower() in user_input) for k in month_to_num_mapping]) or any([(k.lower() in user_input) for k in month_abbr_to_num_mapping]))
    does_user_input_start_with_a_month_name = (user_input[0].isalpha() and does_user_input_contain_a_month_name)

    if does_user_input_contain_a_month_name:
        print(">>> CONTAINS MONTH NAME")
        if does_user_input_start_with_a_month_name:
            print(">>> STARTS W/ MONTH NAME")
            #  will assume: month day year
            (inferred_month, inferred_day, inferred_year) = user_input.split(inferred_delimiter)
            inferred_month = inferred_month.lower()
            if inferred_month in month_to_num_mapping:
                inferred_month_num = month_to_num_mapping[inferred_month]
            elif inferred_month in month_abbr_to_num_mapping:
                inferred_month_num = month_abbr_to_num_mapping[inferred_month]

            inferred_year = match_user_input__date_year(inferred_year)

            # num_days_in_inferred_month = get_mapping_num_days_in_month(int(inferred_year))[int(inferred_month)]
            inferred_month_num = "0" + inferred_month_num if len(str(inferred_month_num)) == 1 else inferred_month_num
            return (inferred_day, inferred_month_num, inferred_year)
            # return f"{inferred_year}{inferred_month_num}{inferred_day}"

        elif not does_user_input_start_with_a_month_name:
            print(">>> DOESNT START W/ MONTH NAME")
            (first_date_val, second_date_val, third_date_val) = user_input.split(inferred_delimiter)
            #  a) year month day
            #  b) year day month?
            if verify_user_input__date_year(first_date_val):
                inferred_year = match_user_input__date_year(first_date_val)
                if second_date_val.lower() in month_to_num_mapping:
                    inferred_month_num = month_to_num_mapping[second_date_val.lower()]
                    inferred_day = third_date_val
                elif second_date_val.lower() in month_abbr_to_num_mapping:
                    inferred_month_num = month_abbr_to_num_mapping[second_date_val.lower()]
                    inferred_day = third_date_val
                elif third_date_val.lower() in month_to_num_mapping:
                    inferred_month_num = month_to_num_mapping[third_date_val.lower()]
                    inferred_day = second_date_val
                elif third_date_val.lower() in month_abbr_to_num_mapping:
                    inferred_month_num = month_abbr_to_num_mapping[third_date_val.lower()]
                    inferred_day = second_date_val
                inferred_month_num = "0" + inferred_month if len(inferred_month) == 1 else inferred_month
                # return f"{inferred_year}{inferred_month_num}{inferred_day}"
                return (inferred_day, inferred_month_num, inferred_year)
            #  d) day year month?
            #  e) month year day
            elif verify_user_input__date_year(second_date_val):
                inferred_year = match_user_input__date_year(second_date_val)
                if first_date_val.lower() in month_to_num_mapping:
                    inferred_month_num = month_to_num_mapping[first_date_val.lower()]
                    inferred_day = third_date_val
                elif first_date_val.lower() in month_abbr_to_num_mapping:
                    inferred_month_num = month_abbr_to_num_mapping[first_date_val.lower()]
                    inferred_day = third_date_val
                elif third_date_val.lower() in month_to_num_mapping:
                    inferred_month_num = month_to_num_mapping[third_date_val.lower()]
                    inferred_day = first_date_val
                elif third_date_val.lower() in month_abbr_to_num_mapping:
                    inferred_month_num = month_abbr_to_num_mapping[third_date_val.lower()]
                    inferred_day = first_date_val
                inferred_month_num = "0" + inferred_month if len(inferred_month) == 1 else inferred_month
                # return f"{inferred_year}{inferred_month_num}{inferred_day}"
                return (inferred_day, inferred_month_num, inferred_year)
            #  c) day month year
            #  f) month day year
            elif verify_user_input__date_year(third_date_val):
                inferred_year = match_user_input__date_year(third_date_val)
                if first_date_val.lower() in month_to_num_mapping:
                    inferred_month_num = month_to_num_mapping[first_date_val.lower()]
                    inferred_day = second_date_val
                elif first_date_val.lower() in month_abbr_to_num_mapping:
                    inferred_month_num = month_abbr_to_num_mapping[first_date_val.lower()]
                    inferred_day = second_date_val
                elif second_date_val.lower() in month_to_num_mapping:
                    inferred_month_num = month_to_num_mapping[second_date_val.lower()]
                    inferred_day = first_date_val
                elif second_date_val.lower() in month_abbr_to_num_mapping:
                    inferred_month_num = month_abbr_to_num_mapping[second_date_val.lower()]
                    inferred_day = first_date_val
                inferred_month_num = "0" + inferred_month if len(inferred_month) == 1 else inferred_month
                # return f"{inferred_year}{inferred_month_num}{inferred_day}"
                return (inferred_day, inferred_month_num, inferred_year)
    #  month name NOT in user input -> so month is a num
    elif not does_user_input_contain_a_month_name:
        print(">>> DOESNT CONTAIN MONTH NAME - ONLY NUM")
        (first_date_val, second_date_val, third_date_val) = user_input.split(inferred_delimiter)
        # chicken
        # trying to fix a bug...
        # if 3 nums are provided, the year should be the one that's 4 digits
        if (len(first_date_val) == 4 or len(second_date_val) == 4 or len(third_date_val) == 4):
            inferred_year = third_date_val if len(third_date_val) == 4 else second_date_val if len(second_date_val) == 4 else first_date_val
        #  american format: e.g. 12/31/90
        #  european format: e.g. 31/12/90
        elif verify_user_input__date_year(third_date_val):
            inferred_year = match_user_input__date_year(third_date_val)
            if verify_user_input__date_month(first_date_val):
                inferred_month = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                inferred_day = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                # return f"{inferred_year}{inferred_month}{inferred_day}"
                return (inferred_day, inferred_month, inferred_year)
            elif verify_user_input__date_month(second_date_val):
                inferred_month = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                inferred_day = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                # return f"{inferred_year}{inferred_month}{inferred_day}"
                return (inferred_day, inferred_month, inferred_year)
        #  2009-*
        elif verify_user_input__date_year(first_date_val):
            inferred_year = match_user_input__date_year(first_date_val)
            if verify_user_input__date_month(third_date_val):
                inferred_month = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                inferred_day = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                # return f"{inferred_year}{inferred_month}{inferred_day}"
                return (inferred_day, inferred_month, inferred_year)
            elif verify_user_input__date_month(second_date_val):
                inferred_month = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                inferred_day = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                # return f"{inferred_year}{inferred_month}{inferred_day}"
                return (inferred_day, inferred_month, inferred_year)
        #  unlikely case: year in middle, e.g. dec 2009 31 (wtf?!)
        elif verify_user_input__date_year(second_date_val):
            inferred_year = match_user_input__date_year(second_date_val)
            if verify_user_input__date_month(third_date_val):
                inferred_month = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                inferred_day = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                # return f"{inferred_year}{inferred_month}{inferred_day}"
                return (inferred_day, inferred_month, inferred_year)
            elif verify_user_input__date_month(second_date_val):
                inferred_month = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                inferred_day = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                # return f"{inferred_year}{inferred_month}{inferred_day}"
                return (inferred_day, inferred_month, inferred_year)
        else:
            print(">>> Error: Trying to figure out the date, input has year & month & day, but what do?")
            return ('', '', '')



def get_list_of_month_names(are_month_names_abbreviated: bool = False) -> list:
    if are_month_names_abbreviated:
        month_names = list(calendar.month_abbr)
        return [k.lower() for k in month_names[1:]]
    else:
        month_names = list(calendar.month_name)
        return [k.lower() for k in month_names[1:]]

def get_mapping_month_name_to_num(are_month_names_abbreviated: bool = False) -> dict:
    return dict(zip(get_list_of_month_names(are_month_names_abbreviated), range(1, 13)))

# to do: simplify this func
def match_user_input__date(user_input: str, is_max_date: bool = False, default_delimiter: str = " ") -> str:
    if not verify_user_input__date(user_input):
        print(">>> Error: the provided date is not understandable")
        return

    user_input = user_input.strip()
    # current_year = get_current_year()
    # month_to_num_mapping = get_mapping_month_name_to_num(are_month_names_abbreviated=False)
    # month_abbr_to_num_mapping = get_mapping_month_name_to_num(are_month_names_abbreviated=True)

    # non_num_or_letter_chars = list(set([k for k in user_input if (not k.isdigit() and not k.isalpha())]))
    # inferred_delimiter = non_num_or_letter_chars[0] if len(non_num_or_letter_chars) == 1 else default_delimiter
    # does_user_input_contain_a_month_name = (any([(k.lower() in user_input) for k in month_to_num_mapping]) or any([(k.lower() in user_input) for k in month_abbr_to_num_mapping]))
    # does_user_input_start_with_a_month_name = (user_input[0].isalpha() and does_user_input_contain_a_month_name)

    if verify_user_input__date_year(user_input):
        print(">>> DATE INPUT IS JUST A YEAR")
        inferred_year = match_user_input__date_year(user_input)
        return f"{inferred_year}1231" if is_max_date else f"{inferred_year}0101"

    elif verify_user_input__date_month_year(user_input):
        print(">>> DATE INPUT IS A MONTH & YEAR")
        (inferred_month, inferred_year) = match_user_input__date_month_year(user_input)
        num_days_in_inferred_month = get_mapping_num_days_in_month(int(inferred_year))[int(inferred_month)]
        return f"{inferred_year}{inferred_month}{num_days_in_inferred_month}" if is_max_date else f"{inferred_year}{inferred_month}01"

    elif verify_user_input__date_day_month_year(user_input):
        print(">>> DATE INPUT IS A DAY & MONTH & YEAR")
        (inferred_day, inferred_month, inferred_year) = match_user_input__date_day_month_year(user_input)
        return f"{inferred_year}{inferred_month}{inferred_day}"

    else:
        print(">>> hmmm... date detected, but formatting not recognized")
        return

def get_mapping_num_days_in_month(year: int) -> dict:
    return {month: calendar.monthrange(year, month)[1] for month in range(1, 13)}

def verify_user_input__pro_player(user_input: str):
    #  loose checks
    return (type(user_input) == str and all([(k.isalpha() or k.isspace() or k in "-'") for k in user_input]))

def get_list_of_pro_players(source_filepath: str) -> list:
    return os.listdir(source_filepath)

def match_user_input__pro_player(user_input: str, list_of_pro_players: list) -> list:
    if not verify_user_input__pro_player(user_input):
        print(">>> that doesn't look like a valid pro name... try again next time")
        return []

    #  direct match
    if user_input in list_of_pro_players:
        return [user_input]

    #  if only first or last name matches
    partial_matches = [k for k in list_of_pro_players if user_input.lower() in k.lower()]
    if len(partial_matches) >= 1:
        return partial_matches

    #  num of matching chars, if clear winner
    get_match_score_between_strings(user_input, 'Lee Hajin')
    mapping_player_to_score = {k: get_match_score_between_strings(user_input, k) for k in list_of_pro_players}

    best_match_score = max(mapping_player_to_score.values())
    matching_results = [k for (k, v) in mapping_player_to_score.items() if v == best_match_score]
    if len(matching_results) == 1:
        # return matching_results[0]
        return matching_results
    else:
        print(">>> Couldn't find a pro with a similar name")
        return []

def get_match_score_between_strings(str_a: str, str_b: str) -> int:
    (str_a, str_b) = (str_a.lower(), str_b.lower())
    (counter_a, counter_b) = (Counter(str_a), Counter(str_b))
    num_matching_chars = 0
    for (k, v) in counter_a.items():
        num_matching_chars += min(v, counter_b[k])
    return num_matching_chars

def copy_thing_to_clipboard(thing: str):
    subprocess.run('pbcopy', input=thing.encode(), check=True)
    print(f">>>>>> {thing}")
    print(">>> Thing copied to clipboard")

def print_rec(rec: str) -> str:
    #  `rec` should be a filepath
    (main_player, filename) = rec.split('/')[-2:]
    print(f">>> Selected via: RANDOMLY WITH REPLACEMENT:")
    print(f">>>>>> It's a {main_player} game")

    # copy_thing_to_clipboard(filename)
    copy_thing_to_clipboard(rec)


def main():
    # allow keywords (attack, fighting, aggressive, defense, defending, defensive, shape, fuseki, midgame, endgame, tesuji, etc.) to prioritize other professionals
    # allow for keyword to specify num_requests
    # allow for keyword to specify min_date, max_date, daterange?
    # allow for functionality to rate a rec

    parser = argparse.ArgumentParser(description="Parameters to filter by")
    # parser.add_argument("-n", "--num", type=int, default=1, help="How many games")
    # to do: can i accept >1 player?
    parser.add_argument("-p", "--player", type=str, help="Games from one specific player")
    parser.add_argument("--mindate", type=str, help="Games on/after a certain date")
    parser.add_argument("--maxdate", type=str, help="Games on/before a certain date")
    args = parser.parse_args()
    args_dict = vars(args)

    print(args_dict)

    destination_dir = '/Users/tarek/github/gogogo/pro_games'
    list_of_pro_games = get_list_of_pro_games(destination_dir, args_dict)
    choice = random.choice(list_of_pro_games)
    print_rec(choice)

if __name__ == '__main__':
    main()
