#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market monitoring script for IT companies positioning analysis
Собирает данные о компаниях из открытых источников
"""

import requests
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from pathlib import Path
import time

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

COMPANIES = {
    'axenix': {'names': ['Axenix', 'Аксеникс'], 'news_urls': ['https://axenix.io/news']},
    'bell': {'names': ['Bell Integrator', 'Белл'], 'news_urls': ['https://www.bell-sw.com/news']},
    'glowbyte': {'names': ['Glowbyte', 'Гловбайт'], 'news_urls': ['https://glowbyte.com/ru/news']},
    'ibs': {'names': ['IBS', 'АйБиЭс'], 'news_urls': ['https://www.ibs.ru/news']},
    'icl': {'names': ['ICL', 'АйСиЭл'], 'news_urls': ['https://www.icl.ru/news']},
    'neoflex': {'names': ['Neoflex', 'Неофлекс'], 'news_urls': ['https://neoflex.ru/news']},
    'madrobot': {'names': ['RedMadRobot', 'МадРобот'], 'news_urls': ['https://www.redmadrobot.com/news']},
    'krok': {'names': ['Крок'], 'news_urls': ['https://www.croc.ru/news']},
    'lanit': {'names': ['Ланит'], 'news_urls': ['https://www.lanit.ru/press']},
    'softline': {'names': ['Softline', 'Софтлайн'], 'news_urls': ['https://www.softline.ru/news']},
    'rarus': {'names': ['Рарус'], 'news_urls': ['https://rarus.ru/news']},
    'goodsforecast': {'names': ['GoodsForecast'], 'news_urls': []},
    'justai': {'names': ['JustAI'], 'news_urls': []},
    'knowledge': {'names': ['Knowledge Space'], 'news_urls': []},
    'rubbles': {'names': ['Rubbles'], 'news_urls': []},
    'ayteko': {'names': ['Ай-Теко'], 'news_urls': []},
    'aston': {'names': ['Астон'], 'news_urls': []},
    'b1': {'names': ['Б1'], 'news_urls': []},
    'drt': {'names': ['ДРТ'], 'news_urls': []},
    'itbasis': {'names': ['ИТ Базис'], 'news_urls': []},
    'kept': {'names': ['Кепт'], 'news_urls': []},
    'korus': {'names': ['Корус'], 'news_urls': []},
    'napoleon': {'names': ['Наполеон ИТ'], 'news_urls': []},
    'novardis': {'names': ['Новардис'], 'news_urls': []},
    'optimakros': {'names': ['Оптимакрос'], 'news_urls': []},
    'first_bit': {'names': ['Первый Бит'], 'news_urls': []},
    'rexoft': {'names': ['Рексофт'], 'news_urls': []},
    'todo': {'names': ['ТеДо'], 'news_urls': []},
    'philosophy': {'names': ['Философия ИТ'], 'news_urls': []},
    'yakov': {'names': ['Яков и партнеры'], 'news_urls': []},
    'auxo': {'names': ['Auxo'], 'news_urls': []},
}

TOPICS = ['облачные решения', 'облако', 'devops', 'цифровизация', 'импортозамещение', 'автоматизация', 'ai', 'ml', 'кибербезопасность', 'безопасность', 'критическая инфраструктура', 'данные', 'аналитика', 'интеграция']

class MarketMonitor:
    def __init__(self):
        self.data = {
            'timestamp': datetime.now().isoformat(),
            'week': datetime.now().isocalendar()[1],
            'companies': defaultdict(lambda: {
                'mentions': 0,
                'sources': defaultdict(int),
                'sentiment': {'positive': 0, 'neutral': 0, 'negative': 0},
                'topics': defaultdict(int),
                'articles': []
            }),
            'total_mentions': 0
        }
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    def fetch_habr(self):
        print("📰 Fetching Habr...")
        try:
            response = self.session.get("https://habr.com/rss/hubs/all/?fl=ru", timeout=10)
            response.encoding = 'utf-8'
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:100]:
                title = (item.find('title') or type('', (), {'text': ''})()).text or ""
                desc = (item.find('description') or type('', (), {'text': ''})()).text or ""
                url = (item.find('link') or type('', (), {'text': ''})()).text or ""
                text = (title + " " + desc).lower()
                for company_key, company_data in COMPANIES.items():
                    for name in company_data['names']:
                        if name.lower() in text:
                            sentiment = self.simple_sentiment(text)
                            self.data['companies'][company_key]['mentions'] += 1
                            self.data['companies'][company_key]['sources']['Habr'] += 1
                            self.data['companies'][company_key]['sentiment'][sentiment] += 1
                            self.extract_topics(company_key, text)
                            self.data['companies'][company_key]['articles'].append({
                                'source': 'Habr', 'title': title[:100], 'url': url, 'sentiment': sentiment, 'date': ''})
                            break
        except Exception as e:
            print(f"  ⚠️ Warning: {e}")
    
    def fetch_vcru(self):
        print("📰 Fetching VC.ru...")
        try:
            response = self.session.get("https://vc.ru/rss/", timeout=10)
            response.encoding = 'utf-8'
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:80]:
                title = (item.find('title') or type('', (), {'text': ''})()).text or ""
                desc = (item.find('description') or type('', (), {'text': ''})()).text or ""
                url = (item.find('link') or type('', (), {'text': ''})()).text or ""
                text = (title + " " + desc).lower()
                for company_key, company_data in COMPANIES.items():
                    for name in company_data['names']:
                        if name.lower() in text:
                            sentiment = self.simple_sentiment(text)
                            self.data['companies'][company_key]['mentions'] += 1
                            self.data['companies'][company_key]['sources']['VC.ru'] += 1
                            self.data['companies'][company_key]['sentiment'][sentiment] += 1
                            self.extract_topics(company_key, text)
                            self.data['companies'][company_key]['articles'].append({
                                'source': 'VC.ru', 'title': title[:100], 'url': url, 'sentiment': sentiment, 'date': ''})
                            break
        except Exception as e:
            print(f"  ⚠️ Warning: {e}")
    
    def fetch_google_news(self):
        print("🗞️ Fetching Google News...")
        try:
            for company_key, company_data in COMPANIES.items():
                name = company_data['names'][0]
                url = f"https://news.google.com/rss/search?q={name}&hl=ru&gl=RU&ceid=RU:ru"
                try:
                    response = self.session.get(url, timeout=10)
                    response.encoding = 'utf-8'
                    root = ET.fromstring(response.content)
                    for item in root.findall('.//item')[:20]:
                        title = (item.find('title') or type('', (), {'text': ''})()).text or ""
                        link = (item.find('link') or type('', (), {'text': ''})()).text or ""
                        sentiment = self.simple_sentiment(title.lower())
                        self.data['companies'][company_key]['mentions'] += 1
                        self.data['companies'][company_key]['sources']['Google News'] += 1
                        self.data['companies'][company_key]['sentiment'][sentiment] += 1
                        self.extract_topics(company_key, title.lower())
                        self.data['companies'][company_key]['articles'].append({
                            'source': 'Google News', 'title': title[:100], 'url': link, 'sentiment': sentiment, 'date': ''})
                    time.sleep(1)
                except:
                    pass
        except Exception as e:
            print(f"  ⚠️ Warning: {e}")
    
    def simple_sentiment(self, text):
        pos = sum(1 for w in ['успешно', 'отличный', 'лучший', 'растет', 'лидер'] if w in text)
        neg = sum(1 for w in ['провал', 'проблем', 'худший', 'падение', 'отстает'] if w in text)
        return 'positive' if pos > neg else 'negative' if neg > pos else 'neutral'
    
    def extract_topics(self, company_key, text):
        for topic in TOPICS:
            if topic in text:
                self.data['companies'][company_key]['topics'][topic] += 1
    
    def run(self):
        print("\n🚀 Starting market monitoring...")
        print(f"📅 Week {self.data['week']}\n")
        self.fetch_habr()
        self.fetch_vcru()
        self.fetch_google_news()
        for company_key, company_data in self.data['companies'].items():
            self.data['total_mentions'] += company_data['mentions']
        self.save_results()
        print("\n✅ Completed!")
    
    def save_results(self):
        output_data = {
            'timestamp': self.data['timestamp'],
            'week': self.data['week'],
            'total_mentions': self.data['total_mentions'],
            'companies': {}
        }
        for company_key, company_data in self.data['companies'].items():
            if company_data['mentions'] > 0:
                output_data['companies'][company_key] = {
                    'mentions': company_data['mentions'],
                    'sources': dict(company_data['sources']),
                    'sentiment': company_data['sentiment'],
                    'topics': dict(company_data['topics']),
                    'top_articles': sorted(company_data['articles'], key=lambda x: x.get('date', ''), reverse=True)[:10]
                }
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        with open(data_dir / 'companies_data.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"📊 Data saved: {self.data['total_mentions']} mentions")

if __name__ == '__main__':
    MarketMonitor().run()
