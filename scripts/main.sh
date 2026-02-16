#!/bin/bash

TYPES=('otp' 'ridership')
TIMES=('saturday' 'sunday' 'weekday')

rm -rf ../export/
mkdir -p ../export/parsed_data

for i in "${TYPES[@]}"; do
  for j in "${TIMES[@]}"; do
    (
      uv run send_requests.py --export ../export/${i}-${j}-data --request-body ../request-bodies/${i}_${j}.json --routes ../routes.txt
      uv run parse_data.py --input "../export/${i}-${j}-data/*.json" --output ../export/parsed_data/${i}-${j}-data.csv
    ) &
  done
done
