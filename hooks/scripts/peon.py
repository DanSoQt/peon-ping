"""peon-ping: Audio alerts for Claude Code hooks.

Cross-platform Claude Code plugin that plays sound alerts when Claude
finishes work, needs permission, or is idle. Compatible with CESP
(Coding Event Sound Pack Specification) sound packs.

Platforms: macOS (afplay), Windows (ffplay/winsound), Linux (paplay/ffplay/aplay)
"""
import sys
import os
import json
import time
import random
import subprocess
import shutil
import platform

PLATFORM = platform.system()  # 'Windows', 'Darwin', 'Linux'

# Plugin root (set by Claude Code when running hooks)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.environ.get(
    'CLAUDE_PLUGIN_ROOT',
    os.path.dirname(os.path.dirname(_SCRIPT_DIR)))

# User data (mutable config/state, outside plugin directory)
USER_DATA = os.path.join(os.path.expanduser('~'), '.claude', 'peon-ping')
CONFIG_PATH = os.path.join(USER_DATA, 'config.json')
STATE_PATH = os.path.join(USER_DATA, '.state.json')
PAUSED_PATH = os.path.join(USER_DATA, '.paused')
DEFAULT_CONFIG = os.path.join(PLUGIN_ROOT, 'config.default.json')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_user_data():
    """Create user data dir and seed default config on first run."""
    os.makedirs(USER_DATA, exist_ok=True)
    if not os.path.exists(CONFIG_PATH) and os.path.exists(DEFAULT_CONFIG):
        shutil.copy2(DEFAULT_CONFIG, CONFIG_PATH)


def load_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default if default is not None else {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Audio playback
# ---------------------------------------------------------------------------

def play_sound(filepath, volume=0.5):
    """Play a sound file using the best available player."""
    if not os.path.isfile(filepath):
        return

    kw = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if PLATFORM == 'Windows':
        kw['creationflags'] = 0x08000000  # CREATE_NO_WINDOW

    # macOS: afplay (built-in, volume 0.0-1.0)
    if PLATFORM == 'Darwin':
        subprocess.Popen(['afplay', '-v', str(volume), filepath], **kw)
        return

    # ffplay (cross-platform, volume 0-100)
    ffplay = shutil.which('ffplay')
    if ffplay:
        vol = max(0, min(100, int(volume * 100)))
        subprocess.Popen(
            [ffplay, '-nodisp', '-autoexit', '-loglevel', 'quiet',
             '-volume', str(vol), filepath], **kw)
        return

    # Linux: paplay (PulseAudio) or aplay (ALSA)
    if PLATFORM == 'Linux':
        for player in ('paplay', 'pw-play', 'aplay'):
            exe = shutil.which(player)
            if exe:
                cmd = [exe, filepath]
                if player == 'aplay':
                    cmd = [exe, '-q', filepath]
                subprocess.Popen(cmd, **kw)
                return

    # Windows fallback: winsound (WAV only, no volume control)
    if PLATFORM == 'Windows' and filepath.lower().endswith('.wav'):
        try:
            import winsound
            winsound.PlaySound(
                filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Focus detection
# ---------------------------------------------------------------------------

def is_terminal_focused():
    """Check if a terminal window is currently in the foreground."""
    if PLATFORM == 'Darwin':
        try:
            r = subprocess.run(
                ['osascript', '-e',
                 'tell application "System Events" to get name of '
                 'first application process whose frontmost is true'],
                capture_output=True, text=True, timeout=2)
            app = r.stdout.strip().lower()
            return any(t in app for t in [
                'terminal', 'iterm', 'wezterm', 'alacritty', 'kitty',
                'hyper', 'tabby'])
        except Exception:
            return False

    if PLATFORM == 'Windows':
        try:
            import ctypes
            import ctypes.wintypes
            u32 = ctypes.windll.user32
            hwnd = u32.GetForegroundWindow()
            length = u32.GetWindowTextLengthW(hwnd)
            if not length:
                return False
            buf = ctypes.create_unicode_buffer(length + 1)
            u32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
            return any(kw in title for kw in [
                'windows terminal', 'command prompt', 'powershell', 'pwsh',
                'cmd.exe', 'wezterm', 'alacritty', 'kitty', 'mintty',
                'conemu', 'cmder', 'hyper', 'tabby'])
        except Exception:
            return False

    if PLATFORM == 'Linux':
        try:
            r = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowname'],
                capture_output=True, text=True, timeout=2)
            title = r.stdout.strip().lower()
            return any(kw in title for kw in [
                'terminal', 'konsole', 'xterm', 'alacritty', 'kitty',
                'wezterm', 'tilix', 'terminator', 'gnome-terminal'])
        except Exception:
            return False

    return False


# ---------------------------------------------------------------------------
# Desktop notifications
# ---------------------------------------------------------------------------

def show_notification(title, message):
    """Show a native desktop notification."""
    if PLATFORM == 'Darwin':
        safe_t = title.replace('"', '\\"')
        safe_m = message.replace('"', '\\"')
        subprocess.Popen(
            ['osascript', '-e',
             f'display notification "{safe_m}" with title "{safe_t}"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif PLATFORM == 'Windows':
        safe_t = title.replace("'", "''")
        safe_m = message.replace("'", "''")
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$n = New-Object System.Windows.Forms.NotifyIcon;"
            "$n.Icon = [System.Drawing.SystemIcons]::Information;"
            f"$n.BalloonTipTitle = '{safe_t}';"
            f"$n.BalloonTipText = '{safe_m}';"
            "$n.Visible = $true;"
            "$n.ShowBalloonTip(5000);"
            "Start-Sleep -Seconds 6;"
            "$n.Dispose()")
        subprocess.Popen(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000)

    elif PLATFORM == 'Linux':
        exe = shutil.which('notify-send')
        if exe:
            subprocess.Popen(
                [exe, title, message],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# Sound picker (CESP-compatible)
# ---------------------------------------------------------------------------

def pick_sound(pack_dir, category, state):
    """Pick a random sound from a CESP category, avoiding repeats."""
    manifest = load_json(os.path.join(pack_dir, 'openpeon.json'))
    sounds = manifest.get('categories', {}).get(category, {}).get('sounds', [])
    if not sounds:
        return None
    last = state.get('last_played', {}).get(category, '')
    pool = sounds if len(sounds) <= 1 else [
        s for s in sounds if s['file'] != last]
    pick = random.choice(pool)
    state.setdefault('last_played', {})[category] = pick['file']
    return os.path.join(pack_dir, pick['file'])


# ---------------------------------------------------------------------------
# Annoyed (rapid-prompt) detection
# ---------------------------------------------------------------------------

def check_annoyed(state, threshold, window_sec):
    now = time.time()
    ts = [t for t in state.get('prompt_timestamps', []) if now - t < window_sec]
    ts.append(now)
    state['prompt_timestamps'] = ts
    return len(ts) >= threshold


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def handle_cli():
    """Handle --pause/--resume/--toggle/--status. Returns True if handled."""
    if len(sys.argv) < 2:
        return False
    cmd = sys.argv[1]
    if cmd == '--pause':
        open(PAUSED_PATH, 'w').close()
        print('peon-ping: sounds paused')
    elif cmd == '--resume':
        try:
            os.remove(PAUSED_PATH)
        except FileNotFoundError:
            pass
        print('peon-ping: sounds resumed')
    elif cmd == '--toggle':
        if os.path.exists(PAUSED_PATH):
            os.remove(PAUSED_PATH)
            print('peon-ping: sounds resumed')
        else:
            open(PAUSED_PATH, 'w').close()
            print('peon-ping: sounds paused')
    elif cmd == '--status':
        paused = os.path.exists(PAUSED_PATH)
        config = load_json(CONFIG_PATH)
        pack = config.get('active_pack', 'peon')
        vol = config.get('volume', 0.5)
        print(f'peon-ping: {"paused" if paused else "active"}')
        print(f'  pack: {pack}  volume: {vol}')
    elif cmd in ('--help', '-h'):
        print('Usage: peon --pause | --resume | --toggle | --status')
    elif cmd.startswith('--'):
        print(f'Unknown option: {cmd}', file=sys.stderr)
        sys.exit(1)
    else:
        return False
    return True


# ---------------------------------------------------------------------------
# Main hook handler
# ---------------------------------------------------------------------------

def main():
    ensure_user_data()

    if handle_cli():
        return

    # Read hook event from stdin
    try:
        event = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return

    config = load_json(CONFIG_PATH, {
        'enabled': True, 'volume': 0.5, 'active_pack': 'peon',
        'desktop_notifications': True,
        'annoyed_threshold': 3, 'annoyed_window_seconds': 10,
        'categories': {}})
    state = load_json(STATE_PATH)

    if not config.get('enabled', True):
        return

    paused = os.path.exists(PAUSED_PATH)
    volume = config.get('volume', 0.5)
    active_pack = config.get('active_pack', 'peon')
    cat_config = config.get('categories', {})
    desktop_notif = config.get('desktop_notifications', True)

    event_name = event.get('hook_event_name', '')
    ntype = event.get('notification_type', '')
    cwd = event.get('cwd', '')
    session_id = event.get('session_id', '')
    perm_mode = event.get('permission_mode', '')

    # Suppress sounds for agent/delegate sessions
    agent_sessions = set(state.get('agent_sessions', []))
    if perm_mode in ('delegate',):
        agent_sessions.add(session_id)
        state['agent_sessions'] = list(agent_sessions)
        save_json(STATE_PATH, state)
        return
    if session_id in agent_sessions:
        return

    project = os.path.basename(cwd) if cwd else 'claude'
    project = ''.join(
        c for c in project if c.isalnum() or c in ' ._-') or 'claude'

    if event_name == 'SessionStart' and paused:
        print("peon-ping: sounds paused -- use 'peon --resume' or "
              "'/peon-ping-toggle' to unpause", file=sys.stderr)

    # Map hook events to CESP categories
    category = ''
    status = ''
    marker = ''
    notify = False
    msg = ''

    if event_name == 'SessionStart':
        category = 'session.start'
        status = 'ready'
    elif event_name == 'UserPromptSubmit':
        threshold = config.get('annoyed_threshold', 3)
        window = config.get('annoyed_window_seconds', 10)
        if (cat_config.get('user.spam', True)
                and check_annoyed(state, threshold, window)):
            category = 'user.spam'
        elif cat_config.get('task.acknowledge', True):
            category = 'task.acknowledge'
        status = 'working'
    elif event_name == 'Stop':
        category = 'task.complete'
        status = 'done'
        marker = '* '
    elif event_name == 'Notification':
        if ntype == 'permission_prompt':
            category = 'input.required'
            status = 'needs approval'
            marker = '* '
            notify = True
            msg = f'{project} -- A tool is waiting for your permission'
        elif ntype == 'idle_prompt':
            category = 'task.complete'
            status = 'done'
            marker = '* '
            notify = True
            msg = f'{project} -- Ready for your next instruction'
        else:
            return
    else:
        return

    # Category enabled check
    if category and not cat_config.get(category, True):
        category = ''

    # Set terminal tab title
    title = f'{marker}{project}: {status}'
    try:
        sys.stdout.buffer.write(f'\033]0;{title}\007'.encode('utf-8'))
        sys.stdout.buffer.flush()
    except Exception:
        pass

    # Play sound
    pack_dir = os.path.join(PLUGIN_ROOT, 'packs', active_pack)
    if category and not paused:
        sound_file = pick_sound(pack_dir, category, state)
        if sound_file and os.path.isfile(sound_file):
            play_sound(sound_file, volume)

    save_json(STATE_PATH, state)

    # Desktop notification when terminal is not focused
    if notify and not paused and desktop_notif and not is_terminal_focused():
        show_notification(title, msg)


if __name__ == '__main__':
    main()
