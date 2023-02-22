#!/usr/bin/env bash

prefix=$1
url=$2

yt-dlp \
  -x --audio-format opus --no-keep-video \
  -f bestaudio -ciw -o "${prefix}_%(id)s.%(ext)s" \
  --sub-lang "zh.*" --write-sub --sub-format srt --match-filter requested_subtitles \
  --download-archive archive.txt -v \
  "$url"

touch .done

