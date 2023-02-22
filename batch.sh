#!/usr/bin/env bash

set -e

cp=$(find /mnt/storage/shawn/crawling/youtube -maxdepth 1 -mindepth 1 -type d | grep -v HomePlus)

for c in $cp; do
  bn=$(basename $c)
  lcbn=${bn,,}
  echo $bn $lcbn
  if [ ! -f $c/.done ] || [ ! -f /mnt/storage/shawn/crawling/data/$lcbn/info.txt ]; then
    rm -rf /mnt/storage/shawn/crawling/data/$lcbn/data
    bash run.sh --yt_stage 1 --stage 1 --stop-stage 1 --nj 64 \
      $c /mnt/storage/shawn/crawling/data/$lcbn /mnt/storage/shawn/formatted/yt_${lcbn}
    touch $c/.done
  fi
  if [ ! -f /mnt/storage/shawn/crawling/data/$lcbn/.done ]; then
    bash run.sh --yt_stage 0 --stage 2 --stop-stage 2 --nj 64 \
      $c /mnt/storage/shawn/crawling/data/$lcbn /mnt/storage/shawn/formatted/yt_${lcbn}
  fi
done

