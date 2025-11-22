#!/usr/bin/env bash
set -e

# Cache sudo using provided password
printf 'Raistlin89\n' | sudo -S -v

# Navigate, activate venv, and run the app
cd /home/gearscodeandfire/timmy-backend
. .venv/bin/activate
cd v33
python app.py --debug

# Keep the shell open for logs/interaction
exec bash -l


