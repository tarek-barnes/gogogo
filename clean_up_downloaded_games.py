import os
import shutil

SOURCE_DIRS = ['/Users/tarek', '/Users/tarek/Downloads']
DESTINATION_DIR = '/Users/tarek/gogames'

def move_go_games(source_directory, destination_directory):
    num_files = 0
    for file in os.listdir(source_directory):
        if file.endswith('.sgf'):
            shutil.move(f'{source_directory}/{file}', f'{destination_directory}/{file}')
            num_files += 1
    print(f">>> {num_files} files moved from {source_directory}.")

def main():
    if not os.path.isdir(DESTINATION_DIR):
        os.mkdir(DESTINATION_DIR)

    for source_dir in SOURCE_DIRS:
        move_go_games(source_dir, DESTINATION_DIR)

if __name__ == '__main__':
    main()