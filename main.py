import datetime
import urllib.parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import plotly.figure_factory as ff

Rakuten_5G = {
    # 1:免許情報検索  2: 登録情報検索
    "ST": 1,
    # 詳細情報付加 0:なし 1:あり
    "DA": 0,
    # スタートカウント
    "SC": 1,
    # 取得件数
    "DC": 3,
    # 出力形式 1:CSV 2:JSON 3:XML
    "OF": 2,
    # 無線局の種別
    "OW": "FB",
    # 所轄総合通信局
    "IT": "E",
    # 都道府県/市区町村
    "HCV": 29000,
    # 免許人名称/登録人名称
    "NA": "楽天モバイル",
}

def musen_api(d):

    parm = urllib.parse.urlencode(d, encoding="shift-jis")
    r = requests.get("https://www.tele.soumu.go.jp/musen/list", parm)

    return r.json()

def band_select(d, start, end, unit):

    d["FF"] = start
    d["TF"] = end
    d["HZ"] = unit

    data = musen_api(d)

    totalCount = int(data['musenInformation']['totalCount'])

    df = pd.json_normalize(data, "musen").rename(columns={"listInfo.tdfkCd": "name"})

    se = df.value_counts("name")

    return se, totalCount

# mmWave(データ、総件数)
se_mmWave, mmWave_total_number = band_select(Rakuten_5G, 26.5, 29.5, 3)

# Sub6(データ、総件数)
se_sub6, sub6_total_number= band_select(Rakuten_5G, 3300, 4200, 2)

# 結合
df0 = (
    pd.concat([se_mmWave.rename("ミリ波"), se_sub6.rename("sub6")], axis=1)
    .rename_axis("場所")
    .reset_index()
)

# 市区町村リスト

df_code = pd.read_csv(
    "city_list.csv",
    dtype={"団体コード": int, "都道府県名": str, "郡名": str, "市区町村名": str},
)

df_code["市区町村名"] = df_code["郡名"].fillna("") + df_code["市区町村名"]
df_code.drop("郡名", axis=1, inplace=True)

df_code["場所"] = df_code["都道府県名"] + df_code["市区町村名"]

# df0と市区町村リストをマージ
df1 = pd.merge(df_code, df0, on=["場所"], how="left")
df1["団体コード"] = df1["団体コード"].astype("Int64")

df1.set_index("団体コード", inplace=True)
df1.sort_index(inplace=True)

# df1["市区町村名"]に含まれる郡名を削除
df1["市区町村名"] = df1["市区町村名"].str.replace("^(添上郡|山辺郡|生駒郡|磯城郡|宇陀郡|高市郡|北葛城郡|吉野郡)", "", regex=True)

df1["ミリ波"] = df1["ミリ波"].fillna(0).astype(int)

df1["sub6"] = df1["sub6"].fillna(0).astype(int)

df2 = df1.reindex(columns=["市区町村名", "ミリ波", "sub6"])

df2.reset_index(inplace=True, drop=True)

df3 = df2.copy() #df2は最新データとしてCSVで保存

# 前回の値を読み込み
old_data = pd.read_csv('data/Rakuten_5G.csv')

df3['増減数1'] = df3['ミリ波'] - old_data['ミリ波']

df3['増減数2'] = df3['sub6'] - old_data['sub6']

df3 = df3[['市区町村名', 'ミリ波', '増減数1', 'sub6', '増減数2']]

df3 = df3.fillna(0).astype({'増減数1': int, '増減数2': int})

df_diff = df3.query('増減数1 != 0 | 増減数2 != 0')

# 差分がある時、画像とテキストファイルを作成
if len(df_diff) > 0:

        # 今日の年月日を取得 
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)

        fig = ff.create_table(df_diff)

        # 下部に余白を付けて更新日を表記
        fig.update_layout(
            title_text = now.strftime("%Y年%m月%d日") + ' 時点のデータです。',
            title_x = 0.98,
            title_y = 0.025,
            title_xanchor = 'right',
            title_yanchor = 'bottom',
            # 余白の設定
            margin = dict(l = 0, r = 0, t = 0, b = 45)
        ) 

        # タイトルフォントサイズ
        fig.layout.title.font.size = 10
        
        # scale=10だと400 Bad Request
        fig.write_image('data/diff.png', engine='kaleido', scale=1)


        # 前回の免許数を取得

        # XMLファイル読み込み
        tree = ET.parse('data/license_total_number_before.xml')
        
        root = tree.getroot()

        # ミリ波、前回免許数
        mmWave_count_before = root.find('mmwave_count').text

        #  sub6、前回免許数
        sub6_count_before = root.find('sub6_count').text


        # send_sns.pyで使うファイルを作成
        text = f"5G免許更新\n\nミリ波:{mmWave_count_before}→{mmWave_total_number}\nsub6:{sub6_count_before}→{sub6_total_number}\n\n発見状況\nhttps://script.google.com/macros/s/AKfycbzY-8ioQp6RiLnleR110Vq-1Yx9ODXtkXeMFwGY92-NxfIDQRU4s4t6sPBIvd9EOGUzRw/exec\n5G免状数は基地局数とは等しくありません\n\n#楽天モバイル #奈良 #bot"
        with open('data/text.text', 'w', encoding='UTF-8') as f:
            f.write(text)

        # 最新の免許数と現在の時刻をXMLファイルに書き込み保存
        with open('data/license_total_number_before.xml', 'w', encoding='UTF-8') as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8" ?><musen_5G><mmwave_count>{mmWave_total_number}</mmwave_count><sub6_count>{sub6_total_number}</sub6_count><date>{now.strftime("%Y/%m/%d %H:%M")}</date></musen_5G>')

# CSV保存
df2.to_csv('data/Rakuten_5G.csv', encoding="utf_8_sig", index=False)
