from glob import glob
import argparse
import os
import whisper
from p_tqdm import p_map
import torch
import re
import ffmpeg
from bs4 import BeautifulSoup
from html import unescape


model = None
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--nj", default=8, type=int)
parser.add_argument("--stage", default=1, type=int)
parser.add_argument("--srt-drop-begin", default=0, type=int)
parser.add_argument("--srt-drop-end", default=0, type=int)
parser.add_argument("db")
parser.add_argument("dst")

SRT_PATTERN = re.compile(r"^[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3} --> [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}")
ZH_PATTERN = re.compile(r'[\u4e00-\u9fff\u3105-\u3129]')
EN_PATTERN = re.compile(r'[a-zA-Z]+')


def filter_no_subtitle(dst):
    srt_list = glob(f"{dst}/*.vtt")
    flist = []
    for srt in srt_list:
        prefix, lang, ext = srt.split(".")
        if "zh" not in lang[:3]:
            continue
        audio = f"{prefix}.opus"
        if not os.path.exists(audio):
            continue
        flist.append([srt, audio])
    return flist


def detect_lang(f, length=48000):
    audio = whisper.load_audio(f)
    audio = whisper.pad_or_trim(audio, length=480000)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    _, probs = model.detect_language(mel)
    lang = max(probs, key=probs.get)
    return lang


def identify_lang(flist, seconds=60):
    result = []
    
    alist = [a for _, a in flist]
    torch.set_num_threads(1)
    langs = p_map(detect_lang, alist, num_cpus=8)

    for i in range(len(langs)):
        flist[i].append(langs[i])
        result.append(flist[i])
    return result


def dump_lang_flist(flist, dst):
    if not os.path.exists(dst):
        os.makedirs(dst)
    with open(f'{dst}/flist_langs.txt', 'w') as fp:
        for f in flist:
            line = f'{f[0]} {f[1]} {f[2]}\n'
            fp.write(line)


def load_lang_flist(dst):
    with open(f'{dst}/flist_langs.txt') as fp:
        lines = fp.read().splitlines()
    result = []
    for line in lines:
        srt, audio, lang = line.strip("\n").split(" ")
        result.append([srt, audio, lang])
    return result


def load_srt(srt_file, drop_begin=0, drop_end=0):
    with open(srt_file) as fp:
        lines = fp.read().splitlines()
    sub_begin = 0
    for line in lines:
        if re.match(SRT_PATTERN, line) is None:
            sub_begin += 1
        else:
            break
    lines = lines[sub_begin:]
    lines = [line for line in lines if line.strip("\n") != ""]
    srt = []
    for line in lines:
        line = line.strip("\n")
        if re.match(SRT_PATTERN, line) is not None:
            srt.append([line, []])
        else:
            try:
                srt[-1][-1].append(line)
            except:
                print('failed to partse srt.')
                print('line', line)
                print('srt_file', srt_file)
                exit(0)
    for item in srt:
        item[1] = " ".join(item[1])
    if drop_end == 0:
        return srt[drop_begin:]
    return srt[drop_begin:-1*drop_end]


def check_audio_srt_ratio(duration, srt, ratio=60):
    zhs = 0
    ens = 0
    for _, line in srt:
        zh = len(re.findall(ZH_PATTERN, line))
        en = len(re.findall(EN_PATTERN, line))
        zhs = zhs + zh
        ens = ens + en
    return (float(zhs+ens) / float(duration)) <= float(60)
    

def check_zh_ratio(srt, ratio=1):
    zhs = 0
    ens = 0
    for _, line in srt:
        zh = len(re.findall(ZH_PATTERN, line))
        en = len(re.findall(EN_PATTERN, line))
        zhs = zhs + zh
        ens = ens + en
    if ens<1:
        return True
    return float(zhs)/float(ens) > ratio


def filter_bad_srt(flist, drop_begin=0, drop_end=0):
    result = []
    for srt_file, audio_file, lang in flist:
        srt = load_srt(srt_file, drop_begin=0, drop_end=0)
        audio = ffmpeg.probe(audio_file)
        # filter non zh lang
        if lang != 'zh':
            print('filtered by language identification', audio_file)
            continue
        # filter ratio between audio duration and srt size
        if not check_audio_srt_ratio(audio['format']['duration'], srt):
            print('filtered by duration', audio_file)
            continue
        # filter srt not matching lang
        if not check_zh_ratio(srt):
            print('filtered by zh ratio:', audio_file)
            continue
        result.append([srt_file, audio_file])
    return result


def dump_valitated_srt_flist(flist, dst):
    with open(f'{dst}/flist_srt_filtered.txt', 'w') as fp:
        for srt_file, audio_file in flist:
            line = f'{srt_file} {audio_file}\n'
            fp.write(line)


def load_validated_srt_flist(dst):
    with open(f'{dst}/flist_srt_filtered.txt') as fp:
        lines = fp.read().splitlines()
    result = []
    for line in lines:
        srt_file, audio_file = line.strip("\n").split(" ")
        result.append([audio_file, srt_file])
    return result


def ts_to_seconds(ts):
    hour, minutes, seconds = ts.split(":")
    seconds = float(seconds)
    seconds = seconds + float(minutes)*60
    seconds = seconds + float(hour)*60*60
    return seconds


def convert_vtt_timestamp(ts):
    tokens = ts.split(" ")
    begts, endts = tokens[0], tokens[2]
    beg = ts_to_seconds(begts.strip(" "))
    end = ts_to_seconds(endts.strip(" "))
    return beg, end


def convert_and_dump_segments(flist, dst, drop_begin=0, drop_end=0):
    result = []
    with open(f'{dst}/info.txt', 'w') as fp:
        for audio_file, srt_file in flist:
            tid = audio_file.split("/")[-1].split(".")[0][-11:]
            srt = load_srt(srt_file, drop_begin=drop_begin, drop_end=drop_end)
            for ts, subtitle in srt:
                try:
                    begin, end = convert_vtt_timestamp(ts)
                    line = f'{tid}-{begin:010.2f}-{end:010.2f} {audio_file} {begin} {end} {subtitle}\n'
                    fp.write(line)
                except Exception as e:
                    print('failed to parse srt for line:')
                    print(ts)
                    print(subtitle)


def make_data(dst):
    with open(f'{dst}/info.txt') as fp:
        lines = fp.read().splitlines()
    datadir = f'{dst}/data'
    if not os.path.exists(datadir):
        os.makedirs(datadir)
    # tid audio begin end trans
    cnt = 10
    with open(f'{datadir}/wav.scp', 'w') as fp_wavscp, \
        open(f'{datadir}/text', 'w') as fp_text, \
        open(f'{datadir}/segments', 'w') as fp_segment:
        for line in lines:
            tokens = line.strip("\n").split(" ")
            tid = tokens[0]
            audio = tokens[1]
            aid = audio.split("/")[-1].split(".")[0]
            begin = tokens[2]
            end = tokens[3]
            trans = BeautifulSoup(unescape(" ".join(tokens[4:])), "lxml").text
            line_wavscp = f"{aid} {audio}\n"
            fp_wavscp.write(line_wavscp)
            line_text = f"{tid} {trans}\n"
            fp_text.write(line_text)
            line_segment = f"{tid} {aid} {begin} {end}\n"
            fp_segment.write(line_segment)

    with open(f'{datadir}/wav.scp') as fp:
        lines = fp.read().splitlines()
    lines = sorted(set(lines))
    with open(f'{datadir}/wav.scp', 'w') as fp:
        for line in lines:
            fp.write(line+"\n")


def main():
    args = parser.parse_args()
    global model
    if args.stage < 2:
        model = whisper.load_model("base", device='cpu')
        flist = filter_no_subtitle(args.db)
        print('language identification')
        flist = identify_lang(flist)
        dump_lang_flist(flist, args.dst)

    if args.stage < 3:
        flist = load_lang_flist(args.dst)
        flist = filter_bad_srt(
            flist, drop_begin=args.srt_drop_begin, drop_end=args.srt_drop_end)
        dump_valitated_srt_flist(flist, args.dst)

    if args.stage < 4:
        flist = load_validated_srt_flist(args.dst)
        convert_and_dump_segments(
            flist, args.dst, drop_begin=args.srt_drop_begin, drop_end=args.srt_drop_end)

    if args.stage < 5:
        make_data(args.dst)


if __name__ == "__main__":
    main()