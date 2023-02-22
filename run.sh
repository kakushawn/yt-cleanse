#!/usr/bin/env bash

stage=1
stop_stage=3
yt_stage=0
srt_drop_start=3
srt_drop_end=3
nj=16

set -e

. ./utils/parse_options.sh

if [ $# != 3 ]; then
  echo "Usage: $0 [options] db dst formatted dir"
  echo $0 $@
  exit 1
fi


# /mnt/storage/shawn/crawling/youtube/TedTaipei/
ytdb=$1
# /tmp/tedtaipei
dst=$2
# /mnt/storage/shawn/formatted/yt_tedtaipei
formated_dir=$3

if [ $stage -le 1 ] && [ $stop_stage -ge 1 ]; then
  python main.py \
    --nj $nj \
    --stage $yt_stage \
    --srt-drop-begin $srt_drop_start \
    --srt-drop-end $srt_drop_end \
    $ytdb $dst
fi

if [ $stage -le 2 ] && [ $stop_stage -ge 2 ]; then
  mv $dst/data/text $dst/data/text.raw
  if [ ! -d chinese_text_normalization ]; then
    git clone https://github.com/kakushawn/chinese_text_normalization
  fi
  python chinese_text_normalization/python/cn_tn.py  \
    --to_banjiao --to_upper --format ark \
    $dst/data/text.raw $dst/data/text.normed
  sed 's/\t/ /g' $dst/data/text.normed > $dst/data/text.normed2
  cut -d " " -f 1 $dst/data/text.normed2 > $dst/data/utts
  cut -d " " -f 2- $dst/data/text.normed2 | tr "[:lower:]" "[:upper:]" > $dst/data/trans
  cat $dst/data/trans |\
    python local/replace_en_space_to_bpe_space.py |\
    sed 's/▁/ /g' | sed 's/ \+/ /g' | sed 's/ $//g' | sed 's/^ //' > $dst/data/trans2
  paste -d " " $dst/data/utts $dst/data/trans2 > $dst/data/text

  awk '{print $1" ffmpeg -i "$2" -ac 1 -ar 16000 -acodec pcm_s16le -f wav pipe:1 |";}' \
    $dst/data/wav.scp > $dst/data/wav.scp.piped

  awk '{print $1" "$1}' $dst/data/text > $dst/data/utt2spk

  bash utils/data/get_utt2dur.sh --nj $nj $dst/data
  utils/fix_data_dir.sh $dst/data
  touch $dst/.done
fi

if [ $stage -le 3 ] && [ $stop_stage -ge 3 ]; then
  bash scripts/audio/format_wav_scp.sh \
    --nj $nj --fs 16000 \
    --segments $dst/data/segments \
    $dst/data/wav.scp.piped $formated_dir
fi

if [ $stage -le 4 ] && [ $stop_stage -ge 4 ]; then
  cp $dst/data/{text,utt2spk} $formated_dir
  bash utils/data/get_utt2dur.sh --nj $nj --read-entire-file true $formated_dir
  utils/fix_data_dir.sh $formated_dir
  dur=$(bash local/get_total_duration.sh $formated_dir)
  echo "duration: $dur"
fi

# ds=$(find /mnt/storage/shawn/crawling/youtube/ -maxdepth 1 -mindepth 1 -type d)
# for d in $ds; do
# cd $d
# echo $d
# find . -name "*opus" | cut -d "." -f 2 | cut -d "/" -f 2 | sort > opuslist
# find . -name "*vtt" | cut -d "." -f 2 | cut -d "/" -f 2 | sort > vttlist
# comm -23 opuslist vttlist > novtt
# find . -name "*opus" | grep -f novtt | xargs -I {} rm {}
# rm opuslist vttlist novtt
# ls -al | grep vtt | wc -l
# ls -al | grep opus | wc -l
# echo "--"
# done