#!/usr/bin/env bash

# Calculate the total duration in hours

if [ $# -ne 1 ]; then
    echo "Usage: $0 data"
    echo "e.g. $0 data/train"
    exit 1
fi

data=$1


if [ -f $data/utt2dur ]; then
    dur_file=$data/utt2dur;
elif [ -f $data/reco2dur ]; then
    dur_file=$data/reco2dur;
else
    echo "[Error] Either utt2dur of rec2dur does not exist."
    exit 1
fi

cat $dur_file |\
    awk -F" " 'BEGIN{
            tot = 0.0;
        } {
            tot+=$2;
        } END {
            print tot/3600
        }'


