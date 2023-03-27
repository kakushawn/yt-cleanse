# Introduction

使用 yt-dlp 爬 youtube 語料。

# steps 1. 下載

- `mkdir ttv`
- `bash download.sh TTV https://www.youtube.com/@TTV_NEWS`
    - 參數1: prefix
        - 音檔之 prefix
    - 參數2: url
        - 直接拋給 yt-dlp 之 youtube url
        - 主要針對頻道爬
        - 亦可以 query 爬，但容易爬到很多髒東西
- 只存音檔
- 以字幕作為 filter，預設以有中文字幕為主
    
# steps 2. 清理

- `bash run.sh --stage 0 --stop-stage 2 db datadir formatted`
    - 參數1: db
        - download.sh 爬下來的資料夾
    - 參數2: datadir
        - 整理後的資料夾，會產生 kaldi data dir
    - 參數3: formatted dir
        - 以 espnet 轉換音檔後的資料夾，已棄用
    - optional 參數：stage
        - 1: 清理 yt-dlp 下載的資料
            - see: main.py
        - 2: 文字正規劃
- `main.py` 之 stage
    - 1: 以 whisper 偵測語言
    - 2: 根據字幕與 whisper 偵測結果篩選
        - 根據參數決定踢掉開頭/結果片段數量
        - 踢掉字幕與 whisper 偵測結果不合的影片
        - 踢掉音檔長度與文字長度差異過大的影片
        - 踢掉主要語言 (i.e. zh) 之比例過少的影片
    - 3: 整理統合表 info.txt
    - 4: 製作 kaldi data