import os
import re

# these: https://github.com/yenw/computer-go-dataset/tree/master/Professional

DESTINATION_DIRNAME = "computer_go_destination"

def create_destination_dir():
    if not os.path.isdir(DESTINATION_DIRNAME):
        os.mkdir(DESTINATION_DIRNAME)

def extract(file: str, destination_dir: str):
    with open(file, 'r') as f:
        raw_data = f.read()
        data = raw_data.split('\n')
        data = [k for k in data if k]
        for game_record in data:
            game_record_lines = game_record.split(";")
            first_line = game_record_lines[0]
            if (first_line != "(" or game_record_lines[-1][-1] != ")"):
                print(">>> ERROR! SGF not formatted properly?")
                breakpoint()

            # use second line and get metadata dict
            second_line = game_record_lines[1]
            metadata_dict = dict(re.findall(r'(\w+)\[(.*?)\]', second_line))
            assumed_date = metadata_dict['GN']
            try:
                if assumed_date.count('-') == 2:
                    (assumed_year, assumed_month, assumed_day) = assumed_date.split('-')


                    formatted_month = assumed_month
                    while formatted_month and not formatted_month[-1].isdigit():
                        formatted_month = formatted_month[:-1]

                    formatted_day = assumed_day
                    while formatted_day and not formatted_day[-1].isdigit():
                        formatted_day = formatted_day[:-1]
                elif assumed_date.count('-') == 1:
                    (assumed_year, _) = assumed_date.split('-')
                    assumed_month = ''
                    formatted_month = assumed_month
                    assumed_day = ''
                    formatted_day = assumed_day
            except Exception as e:
                print(e)
                breakpoint()

            formatted_date = f"{assumed_year}{formatted_month}{formatted_day}"
            black_player = metadata_dict['PB']
            white_player = metadata_dict['PW']

            game_record_filename = f"{formatted_date}---{black_player}---{white_player}.sgf"
            game_record_filepath = f"{destination_dir}/{game_record_filename}"

            with open(game_record_filepath, "w") as f:
                f.write(f"{first_line}\n")  # don't want the file to start with ;
                for line in game_record_lines[1:-1]:
                    f.write(f";{line}\n")
                f.write(f";{game_record_lines[-1]}")  # don't want the file to end with \n
            print(f">>> Created file {game_record_filename}")

def main():
    files_to_extract = [
        '/Users/tarek/github/computer-go-dataset/Professional/pro1940-1999.txt',
        '/Users/tarek/github/computer-go-dataset/Professional/pro2000+.txt'
    ]

    create_destination_dir()
    for file in files_to_extract:
        extract(file, DESTINATION_DIRNAME)

if __name__ == '__main__':
    main()
