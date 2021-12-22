# coding: utf-8

import urllib.parse
import requests
import csv
import pandas as pd
import datetime
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import tweepy
from io import BytesIO

# 今日の年月日を取得 
DIFF_JST_FROM_UTC = 9
now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
today = now.date()

# 年月日時間
str_dateime_now = now.strftime("%Y/%m/%d %H:%M")

# api設定
api = {
    # 1:免許情報検索  2: 登録情報検索
    "ST": 1,
    # 詳細情報付加 0:なし 1:あり
    "DA": 1,
    # スタートカウント
    "SC": 1,
    # 取得件数
    "DC": 2,
    # 出力形式 1:CSV 2:JSON 3:XML
    "OF": 1,
    # 無線局の種別
    "OW": "FB",
    # 所轄総合通信局
    "IT": "E",
    # 都道府県/市区町村
    "HCV": 29000,
    # 周波数（始）
    "FF": 3849.99,
    # 周波数（単位）
    "HZ": 2,
    # 免許人名称/登録人名称
    "NA": "楽天モバイル株式会社",
}

parm = urllib.parse.urlencode(api, encoding="shift-jis")

res = requests.get("https://www.tele.soumu.go.jp/musen/list", parm)
res.raise_for_status()

cr = csv.reader(res.text.splitlines(), delimiter=",")
data = list(cr)

df0 = pd.DataFrame(data).dropna(how="all")

# 最新の免許数
license_count_after = df0.iat[0,1]

# 前回の免許数を取得

# XMLファイル読み込み
# tree = ET.parse('license_count_before.xml')
# root = tree.getroot()

# 前回の免許数
# license_count_before = root[0].text

# データランダリング

#市区町村名
df1 = df0[2].str.split(r'奈良県', expand=True)
df2 = df1.drop(df1.columns[[0]], axis=1)
df2[1] = df1[1].str.replace("^(添上郡|山辺郡|生駒郡|磯城郡|宇陀郡|高市郡|北葛城郡|吉野郡)", "", regex=True)
df2 = df2.rename(columns={1:'市区町村名'})

df3 = df0.loc[:,[4,5]].rename(columns={4:'免許の年月日', 5:'免許人の氏名又は名称'})

df4 = df0[23].str.split(r'\\t|\\n', expand=True).rename(columns={0: "電波の型式(1)", 1: "周波数(1)", 2: "空中線電力(1)", 3: "電波の型式(2)", 4: "周波数(2)", 5: "空中線電力(2)", 6: "電波の型式(3)", 7: "周波数(3)", 8: "空中線電力(3)", 9: "電波の型式(4)", 10: "周波数(4)", 11: "空中線電力(4)"})

df5 = df2.join(df3)
df6 = df5.join(df4)

df6 = df6.drop(df6.index[0])

df6 = df6.fillna('')

# CSV出力
df6.to_csv("data/5G_All_List.csv", encoding="utf_8_sig", index=False)



