# Imports
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import pytz
import json
import os
import time
import random


def get_last_run_value(json_filepath):
    """This function gets the last workflow run value"""
    with open(json_filepath) as f:
        last_run_values_dict = json.load(f)
        last_run_epoch       = last_run_values_dict["last_run_epoch"]
        
        return last_run_epoch


def scrape_tradingview(cutoff_epoch):
    values_list = []
    url = 'https://in.tradingview.com/markets/stocks-india/ideas/?sort=recent'

    i = 1
    flag = True

    while flag:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        page = requests.get(url, headers = headers)
        soup = BeautifulSoup(page.text, 'lxml')
        boxes = soup.find_all('div', class_='tv-widget-idea js-userlink-popup-anchor')

        for box in boxes:
            stock_name = box.find('div', class_='tv-widget-idea__symbol-info').text.strip()

            chart_box = box.find('picture')
            image_link = chart_box.find('img').get('data-src')

            title = box.find('div', class_='tv-widget-idea__title-row').text.strip()
            timeframe = box.find_all('span', class_='tv-widget-idea__timeframe')[-1].text.strip()
            description = box.find('p',
                                   class_='tv-widget-idea__description-row tv-widget-idea__description-row--clamped js-widget-idea__popup').text.strip()

            author_box = box.find('div', class_='tv-widget-idea__author-row')
            author_name = author_box.find('span', class_='tv-card-user-info__username').text.strip()
            post_epoch_time = float(author_box.find_all('span')[-1].get('data-timestamp'))

            try:
                tag = box.find('span', class_='content-PlSmolIm badge-idea-content-ZleujXqe').text.strip()
                if tag == 'Long':
                    tag = '\U0001F7E2'  # Green circle
                if tag == 'Short':
                    tag = '\U0001F534'  # Red circle
            except AttributeError:
                tag = 'Not Mentioned By Author'

            row = [stock_name, image_link, title, timeframe, author_name, post_epoch_time, tag, description]
            if post_epoch_time <= cutoff_epoch:
                flag = False
                break
            else:
                values_list.append(row)

        i += 1
        url = f'https://in.tradingview.com/markets/stocks-india/ideas/page-{str(i)}/?sort=recent'
        time.sleep(random.randint(1,4))

    df = pd.DataFrame(values_list,
                      columns=['stock_name', 'image_link', 'title', 'timeframe', 'author_name', 'post_epoch_time',
                               'tag', 'description'])
    df.drop_duplicates(inplace=True)

    return df

def send_to_telegram(df):
    ist          = pytz.timezone('Asia/Kolkata')
    datetime_ist = datetime.datetime.now(ist).strftime('%d-%b-%Y  %H:%M')
    chat_id      = os.environ['CHAT_ID']
    api_token    = os.environ['API_TOKEN']
    api_url      = f'https://api.telegram.org/bot{api_token}/sendPhoto'
    
    def get_followers_count(author_name):
        author_page      = requests.get(f"https://in.tradingview.com/u/{author_name}/")
        soup             = BeautifulSoup(author_page.text,'lxml')
        followers        = soup.find_all('span','tv-profile__social-item-value')[-1].text.strip()
        time.sleep(random.randint(1,4))
        return int(followers)
    
    def send_data(df):
        for i in range(len(df) - 1, -1, -1):
            description = f"""\n\n{df['stock_name'][i]}
            \n{'*' * 30}\n{df['title'][i]}
            \nTimeframe  : {df['timeframe'][i]}
            \nAuthor View: {df['tag'][i]}
            \n{'*' * 30}\nDescription:\n\n{df['description'][i]}
            \n\n{'*' * 30}\nAuthor  :  {df['author_name'][i]}\n{'-' * 50}
            """
            image_link = df['image_link'][i]

            requests.post(api_url, json={'chat_id': chat_id, 'caption': description, 'photo': image_link})
            
        print(f"{len(df)} Messages posted successfully in Telegram Channel at:   {datetime_ist}")

    if len(df) == 0:
        print(f"No any Idea posted since last run :   {datetime_ist}")
        
    elif len(df) > 8:
        # getting followers
        df['count_followers'] = df['author_name'].apply(get_followers_count)
        
        # sorting as per followers in descending order & reset index
        new_df = df.sort_values(by = 'count_followers', ascending = False)
        new_df.sort_values(by = 'post_epoch_time', ascending = False, inplace = True)
        new_df.reset_index(inplace = True, drop=True)
        
        # sending data
        send_data(new_df.iloc[0:8])
        
    else:
        send_data(df)


def dump_latest_run_value(json_filepath, dataframe):
    with open(json_filepath, 'w') as f:
        json.dump({'last_run_epoch':dataframe.iloc[0,5]},f)


if __name__ == '__main__':
    cutoff_epoch = get_last_run_value(json_filepath='last_run_value.json')
    df = scrape_tradingview(cutoff_epoch=cutoff_epoch)
    if len(df) > 0:
        dump_latest_run_value(json_filepath='last_run_value.json',dataframe=df)
    send_to_telegram(df)
