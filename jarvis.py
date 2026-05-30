import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import tempfile
import requests
import asyncio
import edge_tts
import os
import re
import sys
import time
import threading
import subprocess
import webbrowser
import ctypes
import shutil
import platform
import socket
from datetime import datetime
from urllib.parse import quote_plus, unquote

# INIT
recognizer = sr.Recognizer()
is_speaking = False
stop_speaking_event = threading.Event()
current_audio_alias = None
pending_confirmation = None
assistant_name = "Jarvis"
user_title = "sir"
voice_name = "en-IN-NeerjaNeural"
voice_rate = "+20%"
current_context = {
    "app": None,
    "last_query": None,
}

# CLEAN TEXT
def clean_text(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'[_#`]', '', text)
    return text.strip()

def jarvis_line(text):
    return f"{text}, {user_title}."

def is_internet_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2).close()
        return True
    except OSError:
        return False

# PLAY AUDIO
def mci(command):
    ctypes.windll.winmm.mciSendStringW(command, None, 0, None)

def stop_speaking():
    global current_audio_alias
    stop_speaking_event.set()

    if current_audio_alias:
        mci(f"stop {current_audio_alias}")
        mci(f"close {current_audio_alias}")
        current_audio_alias = None

    return True

def play_audio(file_path):
    global is_speaking, current_audio_alias
    is_speaking = True
    stop_speaking_event.clear()
    current_audio_alias = f"jarvisvoice{int(time.time() * 1000)}"

    try:
        mci(f'open "{os.path.abspath(file_path)}" type mpegvideo alias {current_audio_alias}')
        mci(f"play {current_audio_alias}")

        while not stop_speaking_event.is_set():
            time.sleep(0.1)
            status_buffer = ctypes.create_unicode_buffer(32)
            ctypes.windll.winmm.mciSendStringW(
                f"status {current_audio_alias} mode",
                status_buffer,
                32,
                None,
            )
            if status_buffer.value == "stopped":
                break
    finally:
        if current_audio_alias:
            mci(f"close {current_audio_alias}")
            current_audio_alias = None
        is_speaking = False
        try:
            os.remove(file_path)
        except:
            pass

# SPEAK
async def speak_async(text):
    text = clean_text(text)
    print("Jarvis:", text)

    file_path = "voice.mp3"

    tts = edge_tts.Communicate(text, voice=voice_name, rate=voice_rate)
    await tts.save(file_path)

    threading.Thread(target=play_audio, args=(file_path,), daemon=True).start()

def speak(text):
    asyncio.run(speak_async(text))

# LISTEN
def listen(prompt="Listening...", seconds=3):
    fs = 16000

    print(prompt)

    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()

    recording = (recording * 32767).astype(np.int16)

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()  # 🔥 fix file lock

    write(temp_file.name, fs, recording)

    with sr.AudioFile(temp_file.name) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio)
        print("You:", text)
        return text.lower()
    except:
        return None
    finally:
        try:
            os.remove(temp_file.name)
        except:
            pass

# AI
def ask_ai(question):
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3",
        "prompt": (
            "You are Jarvis, a calm, witty, high-competence desktop AI assistant. "
            "Answer like a polished systems aide: concise, useful, and lightly cinematic. "
            f"Keep it under two sentences and address the user as {user_title} when natural. "
            f"User request: {question}"
        ),
        "stream": False,
        "options": {"num_predict": 80}
    }

    try:
        response = requests.post(url, json=payload)
        return response.json()["response"]
    except:
        return jarvis_line("I cannot connect to my local intelligence core")

# LOCAL ACTIONS
APP_ALIASES = {
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "paint": "mspaint",
    "wordpad": "write",
    "command prompt": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "control panel": "control",
    "settings": "ms-settings:",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
}

APP_PROCESSES = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "wordpad": "wordpad.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "Taskmgr.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
}

WEBSITE_ALIASES = {
    "browser": "https://www.google.com",
    "web": "https://www.google.com",
    "internet": "https://www.google.com",
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "wikipedia": "https://www.wikipedia.org",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com"
}

WEB_APP_SEARCH_URLS = {
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "google": "https://www.google.com/search?q={query}",
    "github": "https://github.com/search?q={query}",
    "wikipedia": "https://www.wikipedia.org/w/index.php?search={query}",
    "gmail": "https://mail.google.com/mail/u/0/#search/{query}",
    "chatgpt": "https://chatgpt.com/?q={query}",
}

EDITING_HOTKEYS = {
    "new": (0x11, 0x4E),
    "new file": (0x11, 0x4E),
    "open file": (0x11, 0x4F),
    "print": (0x11, 0x50),
    "find": (0x11, 0x46),
    "replace": (0x11, 0x48),
    "copy": (0x11, 0x43),
    "cut": (0x11, 0x58),
    "paste": (0x11, 0x56),
    "select all": (0x11, 0x41),
    "undo": (0x11, 0x5A),
    "redo": (0x11, 0x59),
    "save": (0x11, 0x53),
    "save as": (0x11, 0x10, 0x53),
    "close tab": (0x11, 0x57),
    "new tab": (0x11, 0x54),
    "reopen tab": (0x11, 0x10, 0x54),
    "next tab": (0x11, 0x09),
    "previous tab": (0x11, 0x10, 0x09),
    "refresh": (0x74,),
    "reload": (0x74,),
    "fullscreen": (0x7A,),
    "zoom in": (0x11, 0xBB),
    "zoom out": (0x11, 0xBD),
    "reset zoom": (0x11, 0x30),
    "address bar": (0x11, 0x4C),
    "go back": (0x12, 0x25),
    "go forward": (0x12, 0x27),
    "open menu": (0x12,),
    "properties": (0x12, 0x0D),
}

NAVIGATION_KEYS = {
    "scroll down": 0x22,
    "scroll up": 0x21,
    "page down": 0x22,
    "page up": 0x21,
    "go down": 0x28,
    "go up": 0x26,
    "move down": 0x28,
    "move up": 0x26,
    "go left": 0x25,
    "go right": 0x27,
    "home": 0x24,
    "end": 0x23,
}

MEDIA_KEYS = {
    "volume up": 0xAF,
    "increase volume": 0xAF,
    "turn volume up": 0xAF,
    "volume down": 0xAE,
    "decrease volume": 0xAE,
    "turn volume down": 0xAE,
    "unmute": 0xAD,
    "mute": 0xAD,
    "play": 0xB3,
    "pause": 0xB3,
    "play pause": 0xB3,
    "next track": 0xB0,
    "previous track": 0xB1,
}

CONFIRM_WORDS = {"yes", "confirm", "do it", "proceed"}
CANCEL_WORDS = {"no", "cancel", "stop", "never mind"}

def normalize_target(text, prefixes):
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return ""

def set_context(app_name, query=None):
    current_context["app"] = app_name
    if query is not None:
        current_context["last_query"] = query

def get_web_app_name(target):
    target = target.strip().lower()
    if target in WEBSITE_ALIASES:
        return target

    for app_name in WEB_APP_SEARCH_URLS:
        if app_name in target:
            return app_name

    return None

def parse_ordinal(text):
    ordinal_words = {
        "first": 1,
        "1st": 1,
        "one": 1,
        "second": 2,
        "2nd": 2,
        "two": 2,
        "third": 3,
        "3rd": 3,
        "three": 3,
        "fourth": 4,
        "4th": 4,
        "four": 4,
        "fifth": 5,
        "5th": 5,
        "five": 5,
    }

    for word, number in ordinal_words.items():
        if word in text:
            return number

    match = re.search(r"\b(\d+)\b", text)
    if match:
        return int(match.group(1))

    return None

def open_context_search(app_name, query):
    query = query.strip()
    if not query:
        speak(jarvis_line("What should I search for"))
        return True

    if app_name not in WEB_APP_SEARCH_URLS:
        return False

    url = WEB_APP_SEARCH_URLS[app_name].format(query=quote_plus(query))
    webbrowser.open(url)
    set_context(app_name, query)
    speak(jarvis_line(f"Searching {app_name} for {query}"))
    return True

def play_youtube_result(position):
    query = current_context.get("last_query")
    if not query:
        speak(jarvis_line("Search YouTube first, then tell me which result to play"))
        return True

    try:
        response = requests.get(
            "https://www.youtube.com/results",
            params={"search_query": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        video_ids = []
        for video_id in re.findall(r'"videoId":"([^"]+)"', response.text):
            if video_id not in video_ids:
                video_ids.append(video_id)

        if len(video_ids) >= position:
            webbrowser.open(f"https://www.youtube.com/watch?v={video_ids[position - 1]}")
            speak(jarvis_line(f"Playing video number {position}"))
        else:
            speak(jarvis_line(f"I could not find video number {position}"))
    except:
        speak(jarvis_line("I could not load the YouTube results"))

    return True

def open_numbered_web_result(position):
    query = current_context.get("last_query")
    if not query:
        speak(jarvis_line("Search first, then tell me which result to open"))
        return True

    if current_context.get("app") == "youtube":
        return play_youtube_result(position)

    try:
        response = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        links = []
        for href in re.findall(r'class="result__a" href="([^"]+)"', response.text):
            href = href.replace("&amp;", "&")
            match = re.search(r"uddg=([^&]+)", href)
            url = unquote(match.group(1)) if match else href
            if url.startswith("http") and url not in links:
                links.append(url)

        if len(links) >= position:
            webbrowser.open(links[position - 1])
            speak(jarvis_line(f"Opening result number {position}"))
        else:
            speak(jarvis_line(f"I could not find result number {position}"))
    except:
        speak(jarvis_line("I could not load the search results"))

    return True

def handle_context_command(user_input):
    app_name = current_context.get("app")

    search_query = normalize_target(user_input, [
        "search for ",
        "search ",
        "find ",
        "look up ",
    ])
    if search_query and app_name:
        if open_context_search(app_name, search_query):
            return True
        return search_active_app(search_query)

    if "site" in user_input or "result" in user_input or app_name == "youtube":
        position = parse_ordinal(user_input)
        if position and ("open" in user_input or "play" in user_input):
            return open_numbered_web_result(position)

    if "where am i" in user_input or "current app" in user_input:
        if app_name:
            speak(jarvis_line(f"You are working in {app_name}"))
        else:
            speak(jarvis_line("No app context is active"))
        return True

    return False

def open_app(app_name):
    app_name = app_name.strip().lower()
    command = APP_ALIASES.get(app_name, app_name)

    try:
        if command.startswith("ms-"):
            os.startfile(command)
        else:
            subprocess.Popen(command, shell=True)
        set_context(app_name)
        speak(jarvis_line(f"Opening {app_name}"))
        return True
    except:
        speak(jarvis_line(f"I could not open {app_name}"))
        return True

def open_website(target):
    target = target.strip().lower()

    if not target:
        speak(jarvis_line("Which website should I open"))
        return True

    url = WEBSITE_ALIASES.get(target, target)

    if "." not in url and not url.startswith(("http://", "https://")):
        url = f"https://www.google.com/search?q={url.replace(' ', '+')}"
    elif not url.startswith(("http://", "https://")):
        url = "https://" + url

    webbrowser.open(url)
    set_context(get_web_app_name(target) or "browser")
    speak(jarvis_line(f"Opening {target}"))
    return True

def search_web(query):
    query = query.strip()

    if not query:
        speak(jarvis_line("What should I search for"))
        return True

    webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
    set_context("google", query)
    speak(jarvis_line(f"Searching the web for {query}"))
    return True

def press_media_key(key_code, times=1):
    for _ in range(times):
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)
        time.sleep(0.05)

def press_key(key_code):
    ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)

def press_key_times(key_code, times=1):
    for _ in range(times):
        press_key(key_code)
        time.sleep(0.05)

def press_hotkey(*key_codes):
    for key_code in key_codes:
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)

    for key_code in reversed(key_codes):
        ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)

def mouse_click(button="left", clicks=1):
    flags = {
        "left": (0x0002, 0x0004),
        "right": (0x0008, 0x0010),
        "middle": (0x0020, 0x0040),
    }
    down, up = flags[button]
    for _ in range(clicks):
        ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)
        time.sleep(0.05)

def mouse_scroll(amount):
    ctypes.windll.user32.mouse_event(0x0800, 0, 0, amount, 0)

def set_clipboard_text(text):
    safe_text = text.replace("'", "''")
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{safe_text}'"],
        capture_output=True,
        text=True,
    )

def get_clipboard_text():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()

def paste_text(text):
    set_clipboard_text(text)
    time.sleep(0.1)
    press_hotkey(0x11, 0x56)

def type_text(text):
    if not text:
        speak(jarvis_line("What should I write"))
        return True

    paste_text(text)
    speak(jarvis_line("Written"))
    return True

def read_active_content():
    original_clipboard = get_clipboard_text()
    press_hotkey(0x11, 0x41)
    time.sleep(0.2)
    press_hotkey(0x11, 0x43)
    time.sleep(0.4)
    copied_text = get_clipboard_text()

    if original_clipboard:
        set_clipboard_text(original_clipboard)

    copied_text = clean_text(copied_text)
    if not copied_text:
        speak(jarvis_line("I could not read text from the active window"))
        return True

    preview = copied_text[:900]
    if len(copied_text) > 900:
        preview += "..."
    speak(preview)
    return True

def search_active_app(query):
    press_hotkey(0x11, 0x46)
    time.sleep(0.2)
    paste_text(query)
    time.sleep(0.1)
    press_key(0x0D)
    speak(jarvis_line(f"Searching here for {query}"))
    return True

def open_app_command_search(query):
    press_hotkey(0x11, 0x10, 0x50)
    time.sleep(0.2)
    paste_text(query)
    speak(jarvis_line(f"Searching app commands for {query}"))
    return True

def focus_address_or_search_box(text=None):
    press_hotkey(0x11, 0x4C)
    time.sleep(0.1)
    if text:
        paste_text(text)
        speak(jarvis_line(f"Entered {text}"))
    else:
        speak(jarvis_line("Address bar focused"))
    return True

def switch_apps(steps=1):
    alt_key = 0x12
    tab_key = 0x09
    ctypes.windll.user32.keybd_event(alt_key, 0, 0, 0)
    for _ in range(steps):
        press_key(tab_key)
        time.sleep(0.12)
    ctypes.windll.user32.keybd_event(alt_key, 0, 2, 0)
    return True

def handle_window_command(user_input):
    if user_input in ("switch app", "switch apps", "next app", "change app"):
        switch_apps()
        return True

    if user_input in ("previous app", "last app"):
        switch_apps()
        return True

    if user_input in ("minimize window", "minimize"):
        press_hotkey(0x5B, 0x28)
        return True

    if user_input in ("maximize window", "maximize"):
        press_hotkey(0x5B, 0x26)
        return True

    if user_input in ("restore window", "restore"):
        press_hotkey(0x5B, 0x28)
        return True

    if user_input in ("snap left", "move window left"):
        press_hotkey(0x5B, 0x25)
        return True

    if user_input in ("snap right", "move window right"):
        press_hotkey(0x5B, 0x27)
        return True

    if user_input in ("show desktop", "desktop"):
        press_hotkey(0x5B, 0x44)
        return True

    return False

def close_current_window():
    alt_key = 0x12
    f4_key = 0x73
    ctypes.windll.user32.keybd_event(alt_key, 0, 0, 0)
    ctypes.windll.user32.keybd_event(f4_key, 0, 0, 0)
    ctypes.windll.user32.keybd_event(f4_key, 0, 2, 0)
    ctypes.windll.user32.keybd_event(alt_key, 0, 2, 0)
    speak(jarvis_line("Closing the active window"))
    return True

def handle_media_command(user_input):
    for phrase, key_code in MEDIA_KEYS.items():
        if phrase in user_input:
            times = 5 if key_code in (0xAE, 0xAF) else 1
            press_media_key(key_code, times)
            speak(jarvis_line(phrase))
            return True
    return False

def handle_editing_command(user_input):
    app_command = normalize_target(user_input, [
        "use app function ",
        "app function ",
        "command ",
        "run command ",
    ])
    if app_command:
        return open_app_command_search(app_command)

    search_text = normalize_target(user_input, [
        "write in search ",
        "type in search ",
        "search box ",
        "address bar ",
    ])
    if search_text:
        return focus_address_or_search_box(search_text)

    text_to_type = normalize_target(user_input, [
        "write ",
        "type ",
        "enter text ",
        "dictate ",
    ])
    if text_to_type:
        return type_text(text_to_type)

    if "read aloud" in user_input or "read this page" in user_input or "read page" in user_input:
        return read_active_content()

    for phrase, hotkey in EDITING_HOTKEYS.items():
        if user_input == phrase or user_input.startswith(phrase + " "):
            press_hotkey(*hotkey)
            speak(jarvis_line(phrase))
            return True

    for phrase, key_code in NAVIGATION_KEYS.items():
        if user_input == phrase:
            times = 5 if phrase in ("go down", "go up", "move down", "move up") else 1
            press_key_times(key_code, times)
            return True

    if user_input in ("mouse click", "click", "left click"):
        mouse_click("left")
        return True

    if user_input in ("double click", "mouse double click"):
        mouse_click("left", 2)
        return True

    if user_input in ("right click", "context menu"):
        mouse_click("right")
        return True

    if user_input in ("middle click",):
        mouse_click("middle")
        return True

    if user_input in ("mouse scroll down", "wheel down"):
        mouse_scroll(-600)
        return True

    if user_input in ("mouse scroll up", "wheel up"):
        mouse_scroll(600)
        return True

    if user_input in ("press enter", "enter"):
        press_key(0x0D)
        return True

    if user_input in ("press tab", "tab"):
        press_key(0x09)
        return True

    if user_input in ("press escape", "escape"):
        press_key(0x1B)
        return True

    if user_input in ("delete", "press delete"):
        press_key(0x2E)
        return True

    if user_input in ("backspace", "press backspace"):
        press_key(0x08)
        return True

    position = parse_ordinal(user_input)
    if position and ("open" in user_input or "play" in user_input) and ("site" in user_input or "result" in user_input or "video" in user_input):
        return open_numbered_web_result(position)

    return False

def close_app(app_name):
    app_name = app_name.strip().lower()

    if not app_name or app_name in ("something", "anything"):
        speak(jarvis_line("What should I close"))
        return True

    if app_name in ("this", "this window", "current window", "active window", "window"):
        return close_current_window()

    process_name = APP_PROCESSES.get(app_name)

    if not process_name and app_name.endswith(".exe"):
        process_name = app_name

    if process_name:
        result = subprocess.run(
            ["taskkill", "/im", process_name, "/f"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            speak(jarvis_line(f"Closed {app_name}"))
            return True

    if close_window_by_title(app_name):
        speak(jarvis_line(f"Closed {app_name}"))
    else:
        speak(jarvis_line(f"I could not find {app_name}"))
    return True

def close_window_by_title(title):
    safe_title = title.replace("'", "''")
    powershell = (
        f"$target='{safe_title}';"
        "$matches=Get-Process | Where-Object { $_.MainWindowTitle -and $_.MainWindowTitle -like \"*${target}*\" };"
        "foreach ($process in $matches) { $process.CloseMainWindow() | Out-Null };"
        "if ($matches) { exit 0 } else { exit 1 }"
    )

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", powershell],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0

def lock_computer():
    subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
    speak(jarvis_line("Locking the computer"))
    return True

def take_screenshot():
    screenshots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Jarvis")
    os.makedirs(screenshots_dir, exist_ok=True)
    file_path = os.path.join(
        screenshots_dir,
        f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
    )

    powershell = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$screen=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
        "$bmp=New-Object System.Drawing.Bitmap $screen.Width,$screen.Height;"
        "$graphics=[System.Drawing.Graphics]::FromImage($bmp);"
        "$graphics.CopyFromScreen($screen.Left,$screen.Top,0,0,$screen.Size);"
        f"$bmp.Save('{file_path}');"
        "$graphics.Dispose();"
        "$bmp.Dispose();"
    )

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", powershell],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        speak(jarvis_line("Screenshot saved"))
    else:
        speak(jarvis_line("I could not take a screenshot"))
    return True

def system_status():
    total, used, free = shutil.disk_usage(os.path.expanduser("~"))
    free_gb = round(free / (1024 ** 3), 1)
    total_gb = round(total / (1024 ** 3), 1)
    computer = socket.gethostname()
    system = platform.platform()
    speak(f"Status report, {user_title}. {computer} is running {system}. Disk free space is {free_gb} GB out of {total_gb} GB.")
    return True

def diagnostics_report():
    total, used, free = shutil.disk_usage(os.path.expanduser("~"))
    free_percent = round((free / total) * 100)
    local_ai_ready = False
    internet_status = "online" if is_internet_connected() else "offline"

    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        local_ai_ready = True
    except:
        local_ai_ready = False

    ai_status = "online" if local_ai_ready else "offline"
    speak(
        f"Diagnostics complete, {user_title}. Internet is {internet_status}, local AI core is {ai_status}, "
        f"and storage has {free_percent} percent free."
    )
    return True

def tactical_briefing():
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    total, used, free = shutil.disk_usage(os.path.expanduser("~"))
    free_gb = round(free / (1024 ** 3), 1)
    speak(
        f"{greeting}, {user_title}. Systems are online. It is {datetime.now().strftime('%I:%M %p')}. "
        f"You have {free_gb} gigabytes free on the main drive. Awaiting instructions."
    )
    return True

def list_capabilities():
    speak(
        f"Here is what I can do, {user_title}. I can open apps, close apps, open websites, search the web, "
        "search inside YouTube, Google, GitHub, Wikipedia, Gmail, and ChatGPT, open numbered search results, "
        "play numbered YouTube videos, type whatever you say, write into search boxes, read aloud visible text, "
        "copy, cut, paste, select all, undo, redo, save, save as, print, find, replace, create a new file, open a file, "
        "press enter, tab, escape, delete, and backspace, scroll up and down, move with arrow keys, click, double click, "
        "right click, switch apps, minimize, maximize, restore, snap windows left or right, show desktop, open new tabs, "
        "close tabs, reopen tabs, switch tabs, refresh, go back, go forward, zoom in, zoom out, reset zoom, fullscreen, "
        "focus the address bar, use app command search, control volume, mute, unmute, play, pause, next track, previous track, "
        "take screenshots, lock the computer, report system status, run diagnostics, give a tactical briefing, enable startup, "
        "disable startup, and with confirmation I can shut down, restart, or sleep the computer."
    )
    return True

def acknowledge_presence():
    speak(jarvis_line("At your service"))
    return True

def startup_file_path():
    startup_dir = os.path.join(
        os.environ["APPDATA"],
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
    )
    return os.path.join(startup_dir, "JarvisAssistant.bat")

def enable_startup():
    startup_bat = startup_file_path()
    python_path = sys.executable
    script_path = os.path.abspath(__file__)

    with open(startup_bat, "w", encoding="utf-8") as file:
        file.write(f'@echo off\ncd /d "{os.path.dirname(script_path)}"\n"{python_path}" "{script_path}"\n')

    speak(jarvis_line("Jarvis will start when Windows starts"))
    return True

def disable_startup():
    startup_bat = startup_file_path()

    if os.path.exists(startup_bat):
        os.remove(startup_bat)
        speak(jarvis_line("Jarvis startup is disabled"))
    else:
        speak(jarvis_line("Jarvis startup was already disabled"))
    return True

def request_confirmation(action, message):
    global pending_confirmation
    pending_confirmation = action
    speak(message + f" Say yes to confirm or no to cancel, {user_title}.")
    return True

def confirm_pending(user_input):
    global pending_confirmation

    if not pending_confirmation:
        return False

    if user_input in CONFIRM_WORDS:
        action = pending_confirmation
        pending_confirmation = None
        action()
        return True

    if user_input in CANCEL_WORDS:
        pending_confirmation = None
        speak(jarvis_line("Cancelled"))
        return True

    speak(jarvis_line("Please say yes to confirm or no to cancel"))
    return True

def shutdown_computer():
    speak(jarvis_line("Shutting down the computer"))
    subprocess.Popen(["shutdown", "/s", "/t", "5"])

def restart_computer():
    speak(jarvis_line("Restarting the computer"))
    subprocess.Popen(["shutdown", "/r", "/t", "5"])

def sleep_computer():
    speak(jarvis_line("Putting the computer to sleep"))
    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])

def handle_system_command(user_input):
    if user_input in ("are you there", "you there", "online", "status jarvis"):
        return acknowledge_presence()

    if (
        "what can you do" in user_input
        or "what you can do" in user_input
        or "what all you can do" in user_input
        or "what all can you do" in user_input
        or "tell me what you can do" in user_input
        or "tell me your commands" in user_input
        or "show capabilities" in user_input
        or "help me" in user_input
        or "list commands" in user_input
    ):
        return list_capabilities()

    if "run diagnostics" in user_input or "diagnostics" in user_input:
        return diagnostics_report()

    if "status report" in user_input or "daily briefing" in user_input or "tactical briefing" in user_input:
        return tactical_briefing()

    close_target = normalize_target(user_input, ["close app ", "quit app ", "close "])
    if close_target:
        return close_app(close_target)

    if "lock computer" in user_input or "lock screen" in user_input:
        return lock_computer()

    if "take screenshot" in user_input or "screenshot" in user_input:
        return take_screenshot()

    if "system status" in user_input or "computer status" in user_input:
        return system_status()

    if "disable startup" in user_input or "do not start with windows" in user_input:
        return disable_startup()

    if "enable startup" in user_input or "start with windows" in user_input:
        return enable_startup()

    if "shutdown computer" in user_input or "turn off computer" in user_input:
        return request_confirmation(shutdown_computer, "This will shut down the computer.")

    if "restart computer" in user_input or "reboot computer" in user_input:
        return request_confirmation(restart_computer, "This will restart the computer.")

    if "sleep computer" in user_input or "put computer to sleep" in user_input:
        return request_confirmation(sleep_computer, "This will put the computer to sleep.")

    return handle_media_command(user_input)

def handle_local_command(user_input):
    if user_input in ("cut", "stop speaking", "stop talking", "interrupt"):
        stop_speaking()
        print("Speech cut")
        return True

    if confirm_pending(user_input):
        return True

    if handle_context_command(user_input):
        return True

    if handle_editing_command(user_input):
        return True

    if handle_window_command(user_input):
        return True

    if handle_system_command(user_input):
        return True

    app_name = normalize_target(user_input, ["open app ", "launch ", "start "])
    if app_name:
        return open_app(app_name)

    if user_input.startswith("open "):
        target = normalize_target(user_input, ["open "])
        if target in WEBSITE_ALIASES or "." in target:
            return open_website(target)
        return open_app(target)

    website = normalize_target(user_input, ["browse ", "go to ", "open website "])
    if website:
        return open_website(website)

    query = normalize_target(user_input, [
        "search web for ",
        "search google for ",
        "web search for ",
        "search for ",
        "google ",
    ])
    if query:
        return search_web(query)

    return False

# START
tactical_briefing()

while True:

    # PREVENT SELF LISTENING
    if is_speaking:
        time.sleep(0.1)
        continue

    user_input = listen("Listening for command...")

    if not user_input:
        time.sleep(0.3)
        continue

    # EXIT
    if "exit jarvis" in user_input or "shutdown jarvis" in user_input or user_input in ("exit", "quit"):
        speak(jarvis_line("Shutting down"))
        break

    # STOP RESPONSE (basic)
    if "stop" in user_input and not pending_confirmation:
        print("Stopped")
        continue

    # LOCAL COMMANDS
    if handle_local_command(user_input):
        time.sleep(0.3)
        continue

    # AI RESPONSE
    if is_internet_connected():
        reply = ask_ai(user_input)
        speak(reply)
    else:
        speak(jarvis_line("I need an internet connection for that request"))

    time.sleep(0.3)
