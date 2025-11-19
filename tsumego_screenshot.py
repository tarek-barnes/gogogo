import glob
import os
import pyautogui
import shutil
import subprocess
import time
from PIL import Image

SCREENSHOT_SAVES_TO_DIR = '/Users/tarek/Desktop'
DESTINATION_DIR = '/Users/tarek/github/gogogo/anki_tsumego'

def take_interactive_screenshot(timeout=30, interval=0.5):
    before = get_most_recent_screenshot_filepath()

    applescript = '''
    tell application "System Events"
        key down command
        key down shift
        key code 21 -- key code 21 = "4" key
        delay 0.1
        key up shift
        key up command
    end tell
    '''
    subprocess.run(['osascript', '-e', applescript])

    # wait for a screenshot to be taken before breaking
    start = time.time()
    while True:
        time.sleep(interval)
        after = get_most_recent_screenshot_filepath()
        if after != before:
            return after
        if time.time() - start > timeout:
            return

def get_most_recent_screenshot_filepath():
    desktop_path = os.path.expanduser(SCREENSHOT_SAVES_TO_DIR)
    files = [f for f in glob.glob(os.path.join(desktop_path, '*')) if os.path.isfile(f)]
    if not files:
        return None
    return max(files, key=os.path.getctime)

def give_file_anustart(filepath):
    # simplifies the name of the the file
    current_name = filepath.split('/')[-1]
    new_name = ''
    for k in current_name:
        if k.isdigit():
            new_name += k
    new_name += '.jpg'
    new_filepath = f"{DESTINATION_DIR}/{new_name}"

    # make the file smaller
    img = Image.open(filepath)
    rgb_img = img.convert("RGB")
    rgb_img.save(new_filepath, format='JPEG', quality=30, optimize=True)

    os.remove(filepath)

    return new_filepath

def duplicate_filepath_for_answer(filepath):
    answer_filepath = filepath.replace('.jpg', '_ANSWER.jpg')
    shutil.copy(filepath, answer_filepath)
    return answer_filepath

def ensure_preview_is_the_active_window():
    applescript = '''
    tell application "Preview"
    activate
    end tell
    '''
    subprocess.run(['osascript', '-e', applescript])
    time.sleep(0.2)


def make_window_fullscreen():
    ensure_preview_is_the_active_window()

    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('alt')
    pyautogui.press('return')
    pyautogui.keyUp('alt')
    pyautogui.keyUp('ctrl')

def make_window_small_again():
    #  this actually does 2 things:
    #  1) ctrl + option + LEFT --> moves window to left-side (vertical)
    #  2) cmd + 9 --> zoom to fit
    applescript = '''
    tell application "System Events"
    key down control
    key down option
    key code 123 -- left arrow
    key up option
    key up control
    delay 1
    keystroke "9" using {command down}
    end tell
    '''
    subprocess.run(['osascript', '-e', applescript])

def make_window_magnification_to_actual_size_again():
    pyautogui.hotkey('command', '9')

def open_answer_file_in_preview(filepath):
    subprocess.run(["open", filepath])
    time.sleep(0.3)
    make_window_fullscreen()

def click_markup_tool_in_preview():
    time.sleep(0.2)
    ensure_preview_is_the_active_window()

    # clicks the "markup toolbar" button
    (x1, y1) = (1383, 71)
    markup_coords = (x1, y1)
    pyautogui.click(markup_coords)

    time.sleep(0.1)

    # clicks the "draw" button
    (x2, y2) = (157, 115)
    draw_coords = (x2, y2)
    pyautogui.click(draw_coords)

    make_window_small_again()

def main():
    print(">>> INFO: Starting")
    os.makedirs(DESTINATION_DIR, exist_ok=True)
    print(">>> INFO: Made dest dir")
    most_recent_download = take_interactive_screenshot()
    print(">>> INFO: Took screenshot")
    new_filepath = give_file_anustart(most_recent_download)
    print(">>> INFO: Did the thing")
    answer_filepath = duplicate_filepath_for_answer(new_filepath)
    print(">>> INFO: Created answer img file")
    open_answer_file_in_preview(answer_filepath)
    print(">>> INFO: Opened file in Preview")
    click_markup_tool_in_preview()
    print(">>> INFO: Done")

if __name__ == '__main__':
    main()
