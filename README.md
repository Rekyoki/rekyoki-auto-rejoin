# 🎮 Rekyoki Auto Rejoin

Auto rejoin tool for Roblox, built for Termux on Android.

## Install & Run (one command)

```bash
curl -sL https://raw.githubusercontent.com/Rekyoki/rekyoki-auto-rejoin/main/auto_rejoin.py -o auto_rejoin.py && pkg install sqlite -y && pip install rich prompt_toolkit requests -q && python auto_rejoin.py
```

## Features

- Auto rejoins when you get kicked or disconnected
- Supports Game ID and Private Server links (old & new format)
- Uses Roblox Presence API to check if you're actually in-game
- Saves your login so you only enter your cookie once
- Big ASCII banner 😎

## Requirements

- Termux (from F-Droid)
- Python 3
- Internet connection

## Setup

1. Install Termux from https://f-droid.org/packages/com.termux/
2. Paste the one-liner above into Termux
3. Enter your `.ROBLOSECURITY` cookie when prompted
4. Choose Game ID or Private Server and you're good to go

## Getting your cookie

**On PC:**
1. Go to roblox.com and log in
2. Press F12 → Application → Cookies → roblox.com
3. Copy the `.ROBLOSECURITY` value

**On Android (Kiwi Browser):**
1. Install Kiwi Browser + Cookie-Editor extension
2. Log into roblox.com and open Cookie-Editor
3. Find `.ROBLOSECURITY` and copy the value

> ⚠️ Never share your cookie with anyone.

## Credits

Made by Rekyoki
