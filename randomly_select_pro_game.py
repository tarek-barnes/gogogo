import argparse
import calendar
import os
import random
import subprocess
import sys

from collections import Counter
from datetime import datetime

def parse_user_args(source_filepath: str, args_dict: dict) -> tuple:
    matching_min_date = match_user_input__date(args_dict['mindate'], is_max_date=False) if args_dict['mindate'] else None
    matching_max_date = match_user_input__date(args_dict['maxdate'], is_max_date=True) if args_dict['maxdate'] else None
    matching_pros = match_user_input__pro_player(args_dict['player'], get_list_of_pro_players(source_filepath)) if args_dict['player'] else None
    todays_date = True if args_dict['today'] else None
    return (matching_min_date, matching_max_date, todays_date, matching_pros)

def get_filepaths_of_acceptable_pros(source_filepath: str, user_player_name: str) -> list:
    list_of_pro_games = []
    matching_pros = get_list_of_pro_players(source_filepath) if user_player_name is None else user_player_name
    source_filepaths = [f"{source_filepath}/{k}" for k in matching_pros]

    for fp in source_filepaths:
        for (root, _, files) in os.walk(fp):
            for file in files:
                if file.endswith('.sgf'):
                    list_of_pro_games.append(os.path.join(root, file))

    return list_of_pro_games

def get_dates_matching_todays_date(min_year=None, max_year=None) -> str:
    todays_month = datetime.now().month
    todays_month = f"0{todays_month}" if len(str(todays_month)) == 1 else str(todays_month)
    todays_day = datetime.now().day
    todays_day = f"0{todays_day}" if len(str(todays_day)) == 1 else str(todays_day)
    todays_month_day = f"{todays_month}{todays_day}"

    min_year = 1500 if not min_year else min_year
    max_year = (datetime.now().year + 1) if not max_year else max_year
    return [f"{k}{todays_month_day}" for k in range(min_year, max_year)]

def is_date_acceptable_to_the_user(this_date, user_min_date, user_max_date, user_todays_date) -> bool:
    if (user_todays_date and this_date not in get_dates_matching_todays_date()):
        return False
    if (user_min_date and this_date < user_min_date):
        return False
    if (user_max_date and this_date > user_max_date):
        return False
    return True

def get_date_from_game_filepath(pro_game_filepath: str) -> str:
    return pro_game_filepath.split("/")[-1].split('-')[0]

def filter_filepaths_by_acceptable_dates(list_of_pro_games, user_min_date, user_max_date, user_todays_date):
    list_of_pro_games = list(set(list_of_pro_games))
    did_user_provide_a_min_date = user_min_date is not None
    did_user_provide_a_max_date = user_max_date is not None
    did_user_provide_todays_date = user_todays_date is not None
    did_user_provide_any_dates = (did_user_provide_a_min_date or did_user_provide_a_max_date or did_user_provide_todays_date)

    if not did_user_provide_any_dates:
        return list_of_pro_games
    return [fp for fp in list_of_pro_games if is_date_acceptable_to_the_user(get_date_from_game_filepath(fp), user_min_date, user_max_date, user_todays_date)]

def get_list_of_pro_games(source_filepath: str, args_dict: dict) -> list:
    list_of_pro_games = []
    multiple_source_filepaths = []

    (user_min_date, user_max_date, user_todays_date, user_player_name) = parse_user_args(source_filepath, args_dict)

    did_user_provide_a_min_date = user_min_date is not None
    did_user_provide_a_max_date = user_max_date is not None
    did_user_provide_todays_date = user_todays_date is not None
    did_user_provide_a_player_name = user_player_name is not None

    list_of_pro_games = get_filepaths_of_acceptable_pros(source_filepath, user_player_name)
    list_of_pro_games = filter_filepaths_by_acceptable_dates(list_of_pro_games, user_min_date, user_max_date, user_todays_date)
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
            return ('', '')

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
        potential_years = [k for k in [first_date_val, second_date_val, third_date_val] if len(k) == 4]
        # if 3 nums are provided, the year should be the one that's 4 digits
        if len(potential_years) > 1:
            # to do...?
            pass
        elif len(potential_years) == 1:
            print(">>> SHOULD BE HURR")
            inferred_year = potential_years[0]
            if first_date_val == inferred_year:
                if verify_user_input__date_month(third_date_val):
                    inferred_month = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                    inferred_day = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                    return (inferred_day, inferred_month, inferred_year)
                elif verify_user_input__date_month(second_date_val):
                    inferred_month = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                    inferred_day = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                    return (inferred_day, inferred_month, inferred_year)
            elif second_date_val == inferred_year:
                if verify_user_input__date_month(third_date_val):
                    inferred_month = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                    inferred_day = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                    return (inferred_day, inferred_month, inferred_year)
                elif verify_user_input__date_month(first_date_val):
                    inferred_month = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                    inferred_day = "0" + third_date_val if len(third_date_val) == 1 else third_date_val
                    return (inferred_day, inferred_month, inferred_year)
            elif third_date_val == inferred_year:
                if verify_user_input__date_month(second_date_val):
                    inferred_month = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                    inferred_day = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                    return (inferred_day, inferred_month, inferred_year)
                elif verify_user_input__date_month(first_date_val):
                    inferred_month = "0" + first_date_val if len(first_date_val) == 1 else first_date_val
                    inferred_day = "0" + second_date_val if len(second_date_val) == 1 else second_date_val
                    return (inferred_day, inferred_month, inferred_year)

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
    parser.add_argument("--today", action='store_true', help="Get historical games from this date")
    args = parser.parse_args()
    args_dict = vars(args)

    print(f"here is the args_dict: {args_dict}")

    destination_dir = '/Users/tarek/github/gogogo/pro_games'
    list_of_pro_games = get_list_of_pro_games(destination_dir, args_dict)
    choice = random.choice(list_of_pro_games)
    print_rec(choice)

if __name__ == '__main__':
    main()
