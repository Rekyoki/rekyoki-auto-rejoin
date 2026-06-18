import subprocess, time, sys, re, requests, json, os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.table import Table
from rich import box

console = Console()

CONFIG_FILE    = os.path.expanduser("~/.rekyoki_config.json")
CHECK_INTERVAL = 30
LOAD_WAIT      = 25

PRESENCE = {
    0: ("Offline",    "red"),
    1: ("On Website", "yellow"),
    2: ("In Game",    "green"),
    3: ("In Studio",  "blue"),
}

# ── CONFIG ─────────────────────────────────────────────

def save_config(user_id, username, cookie):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"user_id": user_id, "username": username, "cookie": cookie}, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None

def delete_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

# ── ROOT COOKIE EXTRACTION ─────────────────────────────

# Possible locations of Roblox's WebView cookie database
ROBLOX_COOKIE_PATHS = [
    "/data/data/com.roblox.client/app_webview/Default/Cookies",
    "/data/data/com.roblox.client/app_webview/Cookies",
    "/data/data/com.roblox.client/databases/Cookies",
]

def has_root():
    """Check if su is available and working."""
    try:
        result = subprocess.run(
            ["su", "-c", "echo ok"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "ok"
    except:
        return False

def auto_extract_cookie():
    """Extract .ROBLOSECURITY from Roblox app data using root + sqlite3."""
    console.print("[dim]Searching for Roblox cookie in app data...[/dim]")

    for db_path in ROBLOX_COOKIE_PATHS:
        # Check if the file exists first
        check = subprocess.run(
            ["su", "-c", f"test -f '{db_path}' && echo yes || echo no"],
            capture_output=True, text=True, timeout=5
        )
        if check.stdout.strip() != "yes":
            continue

        console.print(f"[dim]Found database at {db_path}[/dim]")

        # Copy to temp location so sqlite3 can read it safely
        tmp = "/data/local/tmp/roblox_cookies_tmp"
        subprocess.run(
            ["su", "-c", f"cp '{db_path}' '{tmp}' && chmod 644 '{tmp}'"],
            timeout=5
        )

        try:
            result = subprocess.run(
                ["su", "-c", f"sqlite3 '{tmp}' \"SELECT value FROM cookies WHERE name='.ROBLOSECURITY' LIMIT 1\""],
                capture_output=True, text=True, timeout=10
            )
            cookie = result.stdout.strip()
            # Clean up temp file
            subprocess.run(["su", "-c", f"rm -f '{tmp}'"], timeout=3)

            if cookie:
                return cookie
            else:
                console.print(f"[yellow][?] Database found but no cookie in it yet.[/yellow]")
        except Exception as e:
            console.print(f"[yellow][!] sqlite3 error: {e}[/yellow]")
            subprocess.run(["su", "-c", f"rm -f '{tmp}'"], timeout=3)

    return None

# ── ROBLOX API ─────────────────────────────────────────

def get_self_from_cookie(cookie: str):
    try:
        r = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            headers={"Cookie": f".ROBLOSECURITY={cookie}"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return str(data.get("id")), data.get("displayName") or data.get("name")
    except Exception as e:
        console.print(f"[red][!] API error: {e}[/red]")
    return None, None

def check_presence(user_id: str, cookie: str):
    try:
        r = requests.post(
            "https://presence.roblox.com/v1/presence/users",
            json={"userIds": [int(user_id)]},
            headers={
                "Cookie": f".ROBLOSECURITY={cookie}",
                "Content-Type": "application/json",
            },
            timeout=10
        )
        if r.status_code == 200:
            presences = r.json().get("userPresences", [])
            if presences:
                p = presences[0]
                return (
                    p.get("userPresenceType", 0),
                    p.get("placeId"),
                    p.get("gameId"),
                )
    except Exception as e:
        console.print(f"[yellow][!] Presence check failed: {e}[/yellow]")
    return None, None, None

def is_in_target_game(user_id: str, cookie: str, place_id: str):
    ptype, api_place_id, _ = check_presence(user_id, cookie)
    if ptype is None:
        return None
    label, color = PRESENCE.get(ptype, ("Unknown", "white"))
    if ptype == 2:
        if str(api_place_id) == str(place_id):
            console.print(f"[green][✓][/green] Status: [{color}]{label}[/{color}] — correct game ✅")
            return True
        else:
            console.print(
                f"[yellow][~][/yellow] Status: [{color}]{label}[/{color}] "
                f"— wrong game (Place ID: {api_place_id})"
            )
            return False
    else:
        console.print(f"[red][✗][/red] Status: [{color}]{label}[/{color}]")
        return False

# ── LINK PARSING ───────────────────────────────────────

def extract_place_id_from_link(link: str):
    match = re.search(r"roblox\.com/games/(\d+)", link)
    return match.group(1) if match else None

def extract_private_code(link: str):
    match = re.search(r"privateServerLinkCode=([^&\s]+)", link)
    if match:
        return match.group(1)
    match = re.search(r"roblox\.com/share\?code=([^&\s]+)", link)
    return match.group(1) if match else None

# ── LAUNCH ─────────────────────────────────────────────

def launch_game(place_id: str, private_code: str = None):
    uri = f"roblox://placeId={place_id}"
    if private_code:
        uri += f"&linkCode={private_code}"
    subprocess.run(
        ["am", "start", "-a", "android.intent.action.VIEW", "-d", uri],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

# ── BANNER ─────────────────────────────────────────────

ASCII_ART = """\
[bold magenta] ██████╗ ███████╗██╗  ██╗██╗   ██╗ ██████╗ ██╗  ██╗██╗[/bold magenta]
[bold magenta]██╔══██╗██╔════╝██║ ██╔╝╚██╗ ██╔╝██╔═══██╗██║ ██╔╝██║[/bold magenta]
[bold cyan]██████╔╝█████╗  █████╔╝  ╚████╔╝ ██║   ██║█████╔╝ ██║[/bold cyan]
[bold cyan]██╔══██╗██╔══╝  ██╔═██╗   ╚██╔╝  ██║   ██║██╔═██╗ ██║[/bold cyan]
[bold blue]██║  ██║███████╗██║  ██╗   ██║   ╚██████╔╝██║  ██╗██║[/bold blue]
[bold blue]╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝[/bold blue]"""

def banner(username: str = None):
    console.clear()
    console.print()
    console.print(ASCII_ART)
    console.print()
    info = "[dim]🎮  Auto Rejoin  •  Termux Edition[/dim]"
    if username:
        info += f"  •  [green]{username}[/green]"
    console.print(f"          {info}")
    console.print()

def draw_menu():
    table = Table(box=box.ROUNDED, border_style="bright_blue", show_header=False, padding=(0, 2))
    table.add_column(justify="center", style="bold yellow")
    table.add_column(style="white")
    table.add_row("1", "Join by  [cyan]Game ID[/cyan]")
    table.add_row("2", "Join by  [magenta]Private Server Link[/magenta]")
    table.add_row("3", "Refresh Cookie  [dim](re-extract from Roblox app)[/dim]")
    table.add_row("4", "Switch Account  [dim](clear saved login)[/dim]")
    table.add_row("5", "[red]Exit[/red]")
    console.print(table)

# ── SETUP ──────────────────────────────────────────────

def get_cookie_auto_or_manual():
    """Try root extraction first, fall back to manual paste."""
    root = has_root()

    if root:
        console.print("[green][✓][/green] Root detected — attempting auto cookie extraction...")
        cookie = auto_extract_cookie()
        if cookie:
            console.print("[green][✓][/green] Cookie extracted automatically!")
            return cookie
        else:
            console.print(
                "[yellow][!][/yellow] Couldn't find cookie automatically.\n"
                "[dim]Make sure you've logged into Roblox at least once on this device.[/dim]"
            )
    else:
        console.print("[yellow][!][/yellow] No root detected — falling back to manual entry.")

    # Manual fallback
    console.print("\n[bold]How to get your .ROBLOSECURITY cookie manually:[/bold]")
    console.print(
        "[dim]  On PC:\n"
        "    1. Go to roblox.com and log in\n"
        "    2. Press F12 → Application → Cookies → roblox.com\n"
        "    3. Copy the .ROBLOSECURITY value\n\n"
        "  On Android (Kiwi Browser):\n"
        "    1. Install Kiwi Browser + Cookie-Editor extension\n"
        "    2. Log into roblox.com and open Cookie-Editor\n"
        "    3. Find .ROBLOSECURITY and copy the value[/dim]\n"
    )
    return Prompt.ask("[cyan]Paste your .ROBLOSECURITY cookie[/cyan]").strip()

def prompt_setup():
    console.print(Panel(
        "[bold]Account Setup[/bold]\n"
        "[dim]Your cookie is saved locally on your device only.[/dim]",
        border_style="cyan"
    ))
    console.print()

    cookie = get_cookie_auto_or_manual()
    if not cookie:
        return None, None, None

    console.print("\n[dim]Verifying cookie with Roblox API...[/dim]")
    user_id, username = get_self_from_cookie(cookie)

    if not user_id:
        console.print("[red][!] Invalid cookie or couldn't reach Roblox API.[/red]")
        time.sleep(3)
        return None, None, None

    console.print(f"[green][✓][/green] Logged in as: [bold]{username}[/bold]  (ID: {user_id})")
    save_config(user_id, username, cookie)
    console.print("[green][✓][/green] Credentials saved for future launches.")
    time.sleep(2)
    return user_id, username, cookie

def setup(skip_banner=False):
    config = load_config()
    if config:
        if not skip_banner:
            banner(config.get("username"))
        console.print(
            f"\n[green][✓][/green] Welcome back, "
            f"[bold]{config['username']}[/bold]! (ID: {config['user_id']})"
        )
        console.print("[dim]Verifying saved cookie...[/dim]")
        user_id, username = get_self_from_cookie(config["cookie"])
        if user_id:
            console.print("[green][✓][/green] Cookie still valid.\n")
            time.sleep(1)
            return config["user_id"], config["username"], config["cookie"]
        else:
            console.print("[yellow][!][/yellow] Saved cookie expired — re-extracting...")
            time.sleep(1)
            # Try to auto re-extract before asking manually
            if has_root():
                cookie = auto_extract_cookie()
                if cookie:
                    user_id, username = get_self_from_cookie(cookie)
                    if user_id:
                        console.print(f"[green][✓][/green] Re-extracted! Logged in as [bold]{username}[/bold]")
                        save_config(user_id, username, cookie)
                        time.sleep(1)
                        return user_id, username, cookie
            delete_config()
            console.print("[red][!] Could not auto re-extract. Please enter cookie manually.[/red]")
            time.sleep(1)

    banner()
    return prompt_setup()

# ── REJOIN LOOP ────────────────────────────────────────

def rejoin_loop(user_id, cookie, place_id, private_code=None):
    label = f"[cyan]{place_id}[/cyan]"
    if private_code:
        label += " + [magenta]Private Server[/magenta]"

    console.print(Panel(f"Auto Rejoin active for {label}", border_style="green"))
    console.print(f"[green][+][/green] Launching Roblox...")
    launch_game(place_id, private_code)
    console.print(f"[dim]Waiting {LOAD_WAIT}s for game to load...[/dim]")
    time.sleep(LOAD_WAIT)

    try:
        while True:
            result = is_in_target_game(user_id, cookie, place_id)
            if result is True:
                console.print(f"[dim]Next check in {CHECK_INTERVAL}s...[/dim]")
            elif result is False:
                console.print("[yellow][!][/yellow] Not in target game — rejoining...")
                launch_game(place_id, private_code)
                console.print(f"[dim]Waiting {LOAD_WAIT}s...[/dim]")
                time.sleep(LOAD_WAIT)
            else:
                console.print("[yellow][!][/yellow] API error — skipping check.")
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        console.print("\n[red][x] Stopped. Returning to menu...[/red]")
        time.sleep(1)

# ── FLOWS ──────────────────────────────────────────────

def flow_game_id(user_id, cookie):
    console.print("\n[bold cyan]Enter Game ID[/bold cyan] [dim](roblox.com/games/XXXXXXX)[/dim]")
    place_id = Prompt.ask("[cyan]Place ID[/cyan]").strip()
    if not place_id.isdigit():
        console.print("[red][!] Invalid — numbers only.[/red]")
        time.sleep(2)
        return
    rejoin_loop(user_id, cookie, place_id)

def flow_private_server(user_id, cookie):
    console.print("\n[bold magenta]Paste your Private Server Link[/bold magenta]")
    link = Prompt.ask("[magenta]Link[/magenta]").strip()

    place_id = extract_place_id_from_link(link)
    private_code = extract_private_code(link)

    if not place_id:
        if private_code:
            console.print(
                "[yellow][?][/yellow] New-style share link detected — "
                "Place ID isn't included in this URL."
            )
            place_id = Prompt.ask("[cyan]Enter the Place ID manually[/cyan]").strip()
            if not place_id.isdigit():
                console.print("[red][!] Invalid Place ID — numbers only.[/red]")
                time.sleep(2)
                return
        else:
            console.print("[red][!] Couldn't find a Place ID or server code in that link.[/red]")
            time.sleep(2)
            return

    if not private_code:
        console.print("[yellow][?] No private server code found — joining as public.[/yellow]")
        time.sleep(1)

    rejoin_loop(user_id, cookie, place_id, private_code)

def flow_refresh_cookie(user_id, username, cookie):
    """Re-extract cookie from Roblox app data."""
    console.print("\n[dim]Re-extracting cookie from Roblox app...[/dim]")
    new_cookie = auto_extract_cookie()
    if not new_cookie:
        console.print("[red][!] Could not extract cookie. Is Roblox installed and logged in?[/red]")
        time.sleep(2)
        return user_id, username, cookie

    new_user_id, new_username = get_self_from_cookie(new_cookie)
    if not new_user_id:
        console.print("[red][!] Extracted cookie appears invalid.[/red]")
        time.sleep(2)
        return user_id, username, cookie

    save_config(new_user_id, new_username, new_cookie)
    console.print(f"[green][✓][/green] Cookie refreshed! Logged in as [bold]{new_username}[/bold]")
    time.sleep(2)
    return new_user_id, new_username, new_cookie

# ── MAIN ───────────────────────────────────────────────

def main():
    user_id, username, cookie = setup()
    if not user_id:
        console.print("[red]Setup failed. Exiting.[/red]")
        sys.exit(1)

    while True:
        banner(username)
        draw_menu()
        console.print()
        choice = Prompt.ask("[bold]Choose[/bold]", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            flow_game_id(user_id, cookie)
        elif choice == "2":
            flow_private_server(user_id, cookie)
        elif choice == "3":
            user_id, username, cookie = flow_refresh_cookie(user_id, username, cookie)
        elif choice == "4":
            delete_config()
            console.print("[yellow]Saved login cleared.[/yellow]")
            time.sleep(1)
            user_id, username, cookie = setup(skip_banner=True)
            if not user_id:
                sys.exit(1)
        elif choice == "5":
            console.print("\n[dim]Goodbye![/dim]")
            sys.exit(0)

if __name__ == "__main__":
    main()
