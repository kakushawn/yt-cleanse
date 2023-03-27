#!/usr/bin/env bash

find /mnt/storage/shawn/crawling/data -mindepth 1 -maxdepth 1 -type d -exec bash local/get_total_duration.sh {}/data \; > d
find /mnt/storage/shawn/crawling/data -mindepth 1 -maxdepth 1 -type d > c
paste -d " " d c | sort -n -k1,1 > dc
rm d c
awk '{tot+=$1} END{print tot}' dc
