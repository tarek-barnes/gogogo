import subprocess
import glob
import os
import time
import re
import shutil
import requests
import json
import urllib.request
import base64
import psutil
from datetime import datetime
from PIL import Image

PROCESSED_DIR = '/Users/tarek/github/gogogo/anki_tsumego/processed'
SOURCE_DIR = '/Users/tarek/github/gogogo/anki_tsumego'

def generate_image_html(image_filepath):
    with open(image_filepath, 'rb') as f:
        image_data = f.read()
    img_base64 = base64.b64encode(image_data).decode('utf-8')
    img_html = f'<img src="data:image/png;base64,{img_base64}">'
    return img_html

def generate_card_skeleton(path_to_question, path_to_answer):
    # with open(image_path, 'rb') as f:
    #     img_data = f.read()
    # img_base64 = base64.b64encode(img_data).decode('utf-8')
    # img_html = f'<img src="data:image/png;base64,{img_base64}">'
    question_img_html = generate_image_html(path_to_question)
    answer_img_html = generate_image_html(path_to_answer)

    # front = f"""
    # {img_html}
    # <div style="font-size:12px; position:absolute; bottom:0; width:100%; text-align:center;">
    # </div>
    # """
    return {
        "deckName": "Tsumego",
        "modelName": "Basic",
        "fields": {
            "Front": question_img_html,
            "Back": answer_img_html
        },
        "tags": []
    }

def invoke(action, params=None):
    return requests.post("http://localhost:8765", json={
        "action": action,
        "version": 6,
        "params": params or {}
        }).json()

def create_anki_card(path_to_question, path_to_answer):
    response = invoke("addNote", {"note": generate_card_skeleton(path_to_question, path_to_answer)})
    note_id = response.get("result")
    return note_id

def get_list_of_unprocessed_tsumego():
    return [f"{SOURCE_DIR}/{k}" for k in os.listdir(SOURCE_DIR) if k.endswith('.jpg')]

def process_tsumego(path_to_question, path_to_answer):
    # ensure paths exist
    if (not os.path.exists(path_to_question) or not os.path.exists(path_to_answer)):
        print(">>> ERROR: Invalid PATH received")
        print(f">>> QUESTION: '{path_to_question}'")
        print(f">>> ANSWER: '{path_to_answer}'")
        return None

    # create anki card
    card_id = create_anki_card(path_to_question, path_to_answer)

    # move fps to processed_dir
    if card_id is not None:
        shutil.move(path_to_question, PROCESSED_DIR)
        shutil.move(path_to_answer, PROCESSED_DIR)
        return True
    else:
        print(">>> ERROR: Couldn't create card... canceling process...")
        return False

def add_all_new_tsumego_to_anki():
    tsumego_to_go_through = [k for k in get_list_of_unprocessed_tsumego() if not k.endswith('_ANSWER.jpg')]
    counter = 0

    for tsumego in tsumego_to_go_through:
        file_name = tsumego.split('/')[-1]
        print(f">>> PROCESSING '{file_name}'")
        answer = tsumego.replace('.jpg', '_ANSWER.jpg')
        if os.path.exists(answer):
            process_tsumego(tsumego, answer)
            counter += 1
        else:
            print(f">>> ERROR: Couldn't find matching answer for '{file_name}'... canceling process...")
    print(f">>> Successfully added {counter} tsumego")

def is_anki_running():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'anki' in proc.info['name'].lower():
            return True
    return False

def start_anki_in_background():
    apple_script = '''
    tell application "Anki"
        launch
    end tell
    tell application "System Events"
        set visible of process "Anki" to false
    end tell
    '''
    subprocess.run(["osascript", "-e", apple_script])

def make_sure_anki_is_running():
    if not is_anki_running():
        start_anki_in_background()

def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(SOURCE_DIR, exist_ok=True)
    make_sure_anki_is_running()

    add_all_new_tsumego_to_anki()

if __name__ == '__main__':
    main()
