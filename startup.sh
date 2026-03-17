#!/bin/bash
mkdir -p /app/ephe
wget -q https://github.com/aloistr/swisseph/raw/master/ephe/seas_18.se1 -O /app/ephe/seas_18.se1
wget -q https://github.com/aloistr/swisseph/raw/master/ephe/semo_18.se1 -O /app/ephe/semo_18.se1
wget -q https://github.com/aloistr/swisseph/raw/master/ephe/sepl_18.se1 -O /app/ephe/sepl_18.se1
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
