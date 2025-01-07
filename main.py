import datetime
import json
import ssl
from urllib import request, parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import plotly.figure_factory as ff

#地方公共団体コード
PrefCode = {
    '滋賀県':25000,
    '京都府':26000,
    '大阪府':27000,
    '兵庫県':28000,
    '奈良県':29000,
    '和歌山県':30000
}

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
    "HCV": '',
    # 免許人名称/登録人名称
    "NA": "楽天モバイル",
}

# 都道府県別、mmWaveとsub6の総件数を格納する辞書を定義
# リストのindex0をミリ波、index1をsub6とする
total_number = {
    '滋賀県':[0, 0],
    '京都府':[0, 0],
    '大阪府':[0, 0],
    '兵庫県':[0, 0],
    '奈良県':[0, 0],
    '和歌山県':[0, 0],
}

def musen_api(d):

    # APIリクエスト条件にShift_JIS(CP943C)を指定する様に記載があるが取得件数0件となる為utf-8を指定
    params = parse.urlencode(d, encoding="utf-8")

    # ヘッダーが無いと403Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    } 

    req = request.Request(f'https://www.tele.soumu.go.jp/musen/list?{params}', headers=headers)

    ctx = ssl.create_default_context()

    ctx.options |= 0x4

    with request.urlopen(req, context=ctx) as res:
        return json.loads(res.read())

def band_select(d, start, end, unit):

    d["FF"] = start
    d["TF"] = end
    d["HZ"] = unit

    data = musen_api(d)

    totalCount = int(data['musenInformation']['totalCount'])

    df = pd.json_normalize(data, "musen").rename(columns={"listInfo.tdfkCd": "name"})

    se = df.value_counts("name")

    return se, totalCount

# 空のDataFrame作成
df = pd.DataFrame()

# 辞書のPrefCodeをループで取り取り出してデータ取得

for k, v in PrefCode.items():

    Rakuten_5G['HCV'] = v

    # mmWave(データ、総件数)
    se_mmWave, mmWave_total_number = band_select(Rakuten_5G, 26.5, 29.5, 3)

    # Sub6(データ、総件数)
    se_sub6, sub6_total_number= band_select(Rakuten_5G, 3300, 4200, 2)

    # total_numberに総件数を代入
    total_number[k][0] = mmWave_total_number

    total_number[k][1] = sub6_total_number

    # 結合
    df0 = (
        pd.concat([se_mmWave.rename("ミリ波"), se_sub6.rename("sub6")], axis=1)
        .rename_axis("場所")
        .reset_index()
    )

    # 都道府県毎のDataFrameを縦に結合
    df = pd.concat([df, df0], axis=0)

# 市区町村リスト

df_code = pd.read_csv(
    "city_list.csv",
    dtype={"団体コード": int, "都道府県名": str, "郡名": str, "市区町村名": str},
    ).set_index('団体コード')

df_code["市区町村名"] = df_code["郡名"].fillna("") + df_code["市区町村名"].fillna("")

df_code.drop("郡名", axis=1, inplace=True)

# 空の市区町村名の列に都道府県名を追記
df_code.loc[250007, '市区町村名'] = '滋賀県'
df_code.loc[260002, '市区町村名'] = '京都府'
df_code.loc[270008, '市区町村名'] = '大阪府'
df_code.loc[280003, '市区町村名'] = '兵庫県'
df_code.loc[290009, '市区町村名'] = '奈良県'
df_code.loc[300004, '市区町村名'] = '和歌山県'

df_code.reset_index(inplace=True)

df_code["場所"] = df_code["都道府県名"] + df_code["市区町村名"]

# df0とdf_codeをmerge
df1 = pd.merge(df_code, df, on=["場所"], how="left")

df1["団体コード"] = df1["団体コード"].astype("Int64")

df1.set_index("団体コード", inplace=True)

df1["ミリ波"] = df1["ミリ波"].fillna(0).astype(int)

df1["sub6"] = df1["sub6"].fillna(0).astype(int)

# 都道府県毎のミリ波とsub6の合計を追記
df1.at[250007, 'ミリ波'] = total_number['滋賀県'][0]
df1.at[250007, 'sub6'] = total_number['滋賀県'][1]

df1.at[260002, 'ミリ波'] = total_number['京都府'][0]
df1.at[260002, 'sub6'] = total_number['京都府'][1]

df1.at[270008, 'ミリ波'] = total_number['大阪府'][0]
df1.at[270008, 'sub6'] = total_number['大阪府'][1]

df1.at[280003, 'ミリ波'] = total_number['兵庫県'][0]
df1.at[280003, 'sub6'] = total_number['兵庫県'][1]

df1.at[290009, 'ミリ波'] = total_number['奈良県'][0]
df1.at[290009, 'sub6'] = total_number['奈良県'][1]

df1.at[300004, 'ミリ波'] = total_number['和歌山県'][0]
df1.at[300004, 'sub6'] = total_number['和歌山県'][1]

df1.sort_index(inplace=True)

# df1["市区町村名"]に含まれる郡名を削除
df1["市区町村名"] = df1["市区町村名"].str.replace("^(|三島郡|与謝郡|久世郡|乙訓郡|伊都郡|佐用郡|加古郡|北葛城郡|南河内郡|吉野郡|多可郡|宇陀郡|山辺郡|川辺郡|愛知郡|揖保郡|日高郡|有田郡|東牟婁郡|泉北郡|泉南郡|海草郡|犬上郡|生駒郡|相楽郡|磯城郡|神崎郡|綴喜郡|美方郡|船井郡|蒲生郡|西牟婁郡|豊能郡|赤穂郡|高市郡)", "", regex=True)

df2 = df1.reindex(columns=["都道府県名", "市区町村名", "ミリ波", "sub6"])

df3 = df2.copy() #df2は最新データとしてCSVで保存

# 前回の値を読み込み
old_data = pd.read_csv('data/Rakuten_5G_kinki.csv')

old_data.set_index('団体コード', inplace=True)

df3['増減数1'] = df3['ミリ波'] - old_data['ミリ波']

df3['増減数2'] = df3['sub6'] - old_data['sub6']

df3 = df3[['市区町村名', 'ミリ波', '増減数1', 'sub6', '増減数2']]

df3 = df3.fillna(0).astype({'増減数1': int, '増減数2': int})

df_diff = df3.query('増減数1 != 0 | 増減数2 != 0')

# 差分がある時、SNS送信用の画像とテキストファイルを作成
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

    # 文章作成
    text = '【5G免許更新】\n\n'

    # 都道府県の合計行を抽出
    df_pref = df_diff.query('市区町村名 == "滋賀県" or 市区町村名 == "京都府" or 市区町村名 == "大阪府" or 市区町村名 == "兵庫県" or 市区町村名 == "奈良県" or 市区町村名 == "奈良県" or 市区町村名 == "和歌山県"')

    pref = []

    for i, row in df_pref.iterrows():
        pref.append(f"{row.iloc[0]}: 更新あり")

    text += "\n".join(pref)

    text += '\n\n奈良県の状況\nhttps://script.google.com/macros/s/AKfycbzY-8ioQp6RiLnleR110Vq-1Yx9ODXtkXeMFwGY92-NxfIDQRU4s4t6sPBIvd9EOGUzRw/exec\n\n#楽天モバイル #近畿 #bot'

    print(text)

    with open('data/text.text', 'w', encoding='UTF-8') as f:
        f.write(text)

    # 日時をXMLファイルに書き込み保存
    with open('data/LastUpdate_kinki.xml', 'w', encoding='UTF-8') as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8" ?><musen_5G><date>{now.strftime("%Y/%m/%d %H:%M")}</date></musen_5G>')
    
# 奈良県の更新がある場合はデータ保存
if len(df_diff.query('市区町村名 == "奈良県" ')) > 0:

    print('奈良県 更新あり')

    # df2から奈良県を抽出して奈良県用のCSVを保存
    df_nara = df2[df2['都道府県名'] == '奈良県']

    df_nara.drop(['都道府県名'], axis=1, inplace=True)

    df_nara.reset_index(drop=True, inplace=True)

    # CSV保存
    df_nara.to_csv('data/Rakuten_5G_nara.csv', encoding="utf_8_sig", index=False)

    # 現在の時刻をXMLファイルに書き込み保存
    with open('data/LastUpdate_nara.xml', 'w', encoding='UTF-8') as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8" ?><musen_5G><date>{now.strftime("%Y/%m/%d %H:%M")}</date></musen_5G>')

else:
    print('奈良県 更新なし')

# CSV保存
df2.to_csv('data/Rakuten_5G_kinki.csv', encoding="utf_8_sig", index=True)
