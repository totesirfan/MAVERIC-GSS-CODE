#!/bin/bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gnuradio
cd "$(dirname "$0")"
python3 MAV_RX.py
stty sane 2>/dev/null
printf '\e[?25h\e[0m'
