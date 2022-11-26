# Imports
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import datetime

# Get current date & time
current_time = datetime.datetime.now()


# Scraping function
def scrape_tradingview():
    values_list = []
    url         = 'https://in.tradingview.com/markets/stocks-india/ideas/?sort=recent'
    curr_time   = time.time()
    cutoff_time = curr_time - 3600
    i = 1
    flag = True
    
    while flag:
        page   = requests.get(url)
        soup   = BeautifulSoup(page.text,'lxml')       
        boxes  = soup.find_all('div',class_= 'tv-widget-idea js-userlink-popup-anchor')
        
        for box in boxes:
            stock_name      = box.find('div', class_ = 'tv-widget-idea__symbol-info').text.strip()
            
            chart_box       = box.find('picture')
            image_link      = chart_box.find('img').get('data-src')
            
            title           = box.find('div', class_ = 'tv-widget-idea__title-row').text.strip()
            timeframe       = box.find_all('span', class_ = 'tv-widget-idea__timeframe')[-1].text.strip()
            description     = box.find('p', class_ = 'tv-widget-idea__description-row tv-widget-idea__description-row--clamped js-widget-idea__popup').text.strip()
            
            author_box      = box.find('div', class_ = 'tv-widget-idea__author-row')
            author_name     = author_box.find('span', class_ = 'tv-card-user-info__username').text.strip()
            post_epoch_time = float(author_box.find_all('span')[-1].get('data-timestamp'))
    
            if post_epoch_time < cutoff_time:
                flag = False
                break
        
            try:
                tag = box.find('span', class_ = 'content-TRXznVu1 badge-idea-content-fWzOPd3k').text.strip()
                if tag == 'Long':
                    tag = '\U0001F7E2' # Green circle
                if tag == 'Short':
                    tag = '\U0001F534' # Red circle
            except AttributeError:
                tag = 'Not Mentioned By Author'
            
            
            row = [stock_name, image_link, title, timeframe, author_name, post_epoch_time, tag, description]
            values_list.append(row)
            
            
        i += 1
        url = f'https://in.tradingview.com/markets/stocks-india/ideas/page-{str(i)}/?sort=recent'
           
       
    df = pd.DataFrame(values_list, columns = ['stock_name','image_link','title', 'timeframe','author_name', 'post_epoch_time', 'tag', 'description'])
    
    return df


def send_to_telegram(df):

    api_token = '5800902618:AAEiZQ26G_4YUbS9eHafJohhZID3fsCEYLc'
    chat_id   = '@test_channel_bot24'
    api_url   = f'https://api.telegram.org/bot{api_token}/sendPhoto'
    
    if len(df) > 0:
        for i in range(len(df)-1,-1,-1):
            posted = datetime.datetime.fromtimestamp(int(df['post_epoch_time'][i])).strftime("%d %b %Y -- %I:%M")
            
            description = f"""\n\n{df['stock_name'][i]}
            \n{'*'*30}\n{df['title'][i]}
            \nTimeframe  : {df['timeframe'][i]}
            \nAuthor View: {df['tag'][i]}
            \n{'*'*30}\nDescription:\n\n{df['description'][i]}
            \n\n{'*'*30}\nAuthor  :  {df['author_name'][i]}
            \nPosted  :  {posted}\n{'-'*50}
            """
            image_link = df['image_link'][i]
    
            # sending row data to telegram
            requests.post(api_url, json={'chat_id': chat_id,'caption' : description, 'photo':image_link})
            
        print("Messages posted successfully in Telegram Channel: ", current_time)
    else:
        print("No any Idea posted in last 1 Hour : ",current_time)


if __name__ == '__main__':
    # Run the scraper
    df = scrape_tradingview()
    send_to_telegram(df)
