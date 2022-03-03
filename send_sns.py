import datetime
import os
import xml.etree.ElementTree as ET

from linebot import LineBotApi
from linebot.models import TextSendMessage, ImageSendMessage
import tweepy

# xmlファイルから最終更新日を取得
tree = ET.parse('data/license_total_number_before.xml')
date = datetime.datetime.strptime(tree.find('date').text, '%Y/%m/%d %H:%M').date()

# 最終更新日が今日だったらSNSに送信
if date != datetime.date.today():

    # テキストファイル読み込み
    with open('data/text.text', 'r') as f:
        text = f.read()
    
    # Twitter

    api_key = os.environ["API_KEY"]
    api_secret = os.environ["API_SECRET_KEY"]
    access_token = os.environ["ACCESS_TOKEN"]
    access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]

    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_token_secret)

    '''api = tweepy.API(auth)
    media_ids = []
    res_media_ids = api.media_upload("data/diff.png")
    media_ids.append(res_media_ids.media_id)
    api.update_status(status = text, media_ids = media_ids)'''

    # LINE
    line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])

    line_bot_api.broadcast(
        messages = [
            TextSendMessage(text = text),

        ]
    )
