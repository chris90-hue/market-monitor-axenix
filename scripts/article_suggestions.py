#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Article Suggestions Generator
Генерирует рекомендации для статей на основе аналитики позиционирования
Использует Claude API для анализа и генерирования идей
"""

import json
import os
from datetime import datetime
from pathlib import Path
import anthropic

class ArticleSuggestionsGenerator:
    def __init__(self):
        # Инициализируем Anthropic клиент
        # API key загружается из переменной окружения ANTHROPIC_API_KEY
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        self.data = None
        self.week_number = None
        
    def load_data(self):
        """Загружает собранные данные о мониторинге"""
        try:
            with open('data/companies_data.json', 'r', encoding='utf-8') as f:
                self.data = json.load(f)
                self.week_number = self.data.get('week', datetime.now().isocalendar()[1])
                print(f"✅ Данные загружены (Неделя {self.week_number})")
        except FileNotFoundError:
            print("❌ Файл data/companies_data.json не найден")
            return False
        return True
    
    def analyze_data(self):
        """Анализирует данные и подготавливает контекст для Claude"""
        axenix_data = self.data['companies'].get('axenix', {})
        
        # Найти топ конкурентов
        competitors = sorted(
            [(k, v) for k, v in self.data['companies'].items() if k != 'axenix'],
            key=lambda x: x[1].get('mentions', 0),
            reverse=True
        )[:5]
        
        # Найти trending topics
        all_topics = {}
        for company_data in self.data['companies'].values():
            for topic, count in company_data.get('topics', {}).items():
                all_topics[topic] = all_topics.get(topic, 0) + count
        
        trending_topics = sorted(
            all_topics.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Найти где Axenix отстаёт
        axenix_topics = axenix_data.get('topics', {})
        gaps = []
        for topic, total_count in trending_topics:
            axenix_count = axenix_topics.get(topic, 0)
            if total_count > 0:
                axenix_percentage = (axenix_count / total_count) * 100
                if axenix_percentage < 30 and total_count > 20:  # Значимый gap
                    gaps.append({
                        'topic': topic,
                        'axenix_mentions': axenix_count,
                        'total_mentions': total_count,
                        'gap_percentage': 100 - axenix_percentage
                    })
        
        gaps = sorted(gaps, key=lambda x: x['gap_percentage'], reverse=True)[:5]
        
        # Найти источники где Axenix слаб
        axenix_sources = axenix_data.get('sources', {})
        competitor_sources = {}
        for comp_key, comp_data in competitors[:3]:
            for source, count in comp_data.get('sources', {}).items():
                competitor_sources[source] = competitor_sources.get(source, 0) + count
        
        # Сентимент анализ
        axenix_sentiment = axenix_data.get('sentiment', {})
        total_mentions = sum(axenix_sentiment.values())
        sentiment_positive = (axenix_sentiment.get('positive', 0) / total_mentions * 100) if total_mentions > 0 else 0
        
        analysis = {
            'axenix': {
                'mentions': axenix_data.get('mentions', 0),
                'sentiment_positive': round(sentiment_positive, 1),
                'topics': dict(sorted(axenix_topics.items(), key=lambda x: x[1], reverse=True)[:5])
            },
            'competitors': [
                {
                    'name': k,
                    'mentions': v.get('mentions', 0),
                    'key_topics': dict(sorted(v.get('topics', {}).items(), key=lambda x: x[1], reverse=True)[:3])
                }
                for k, v in competitors[:3]
            ],
            'trending_topics': [{'topic': t, 'mentions': c} for t, c in trending_topics[:8]],
            'gaps': gaps,
            'total_market_mentions': self.data.get('total_mentions', 0)
        }
        
        return analysis
    
    def generate_suggestions(self, analysis):
        """Генерирует рекомендации для статей используя Claude API"""
        
        # Подготавливаем промпт с анализом
        prompt = f"""
Ты - опытный content strategist для IT компании Axenix.

На основе следующей аналитики позиционирования компании на рынке, 
генерируй 5-7 уникальных идей для статей блога, которые помогут 
Axenix укрепить позиции и привлечь аудиторию.

АНАЛИТИКА:

Позиция Axenix:
- Всего упоминаний на рынке: {analysis['axenix']['mentions']} (из {analysis['total_market_mentions']} всего)
- Позитивный сентимент: {analysis['axenix']['sentiment_positive']}%
- Основные темы позиционирования: {', '.join(analysis['axenix']['topics'].keys())}

Топ конкуренты:
{chr(10).join([f"- {c['name']}: {c['mentions']} упоминаний, темы: {', '.join(c['key_topics'].keys())}" for c in analysis['competitors']])}

Тренды на рынке (что обсуждают все):
{chr(10).join([f"- {t['topic']}: {t['mentions']} упоминаний" for t in analysis['trending_topics']])}

ВОЗМОЖНОСТИ (где Axenix может выиграть):
{chr(10).join([f"- {g['topic']}: конкуренты говорят на +{g['gap_percentage']:.0f}% больше, есть пробел!" for g in analysis['gaps']])}

ЗАДАЧА:
Выдай 5-7 идей для статей, которые:
1. Используют тренды, о которых говорят (но Axenix слабо)
2. Позиционируют Axenix как эксперта
3. Привлекают целевую аудиторию
4. Имеют потенциал для SEO трафика
5. Соответствуют позиционированию компании

ФОРМАТ ОТВЕТА (JSON):
Верни только валидный JSON без лишних символов:
{{
    "articles": [
        {{
            "title": "Название статьи (максимум 80 символов)",
            "description": "Короткое описание (2-3 предложения)",
            "target_audience": "Кто должен читать (1 фраза)",
            "key_topics": ["тема1", "тема2", "тема3"],
            "suggested_outline": [
                "Вводная часть: почему это актуально",
                "Основной контент пункт 1",
                "Основной контент пункт 2",
                "Best practices",
                "Case study или пример",
                "Заключение и CTA"
            ],
            "estimated_word_count": 2500,
            "seo_keywords": "ключевое слово, ключевое слово, ключевое слово",
            "why_this_matters": "Почему Axenix должна написать эту статью (конкурентное преимущество)",
            "priority": "HIGH/MEDIUM"
        }}
    ]
}}

Помни: все статьи должны быть полезными, экспертными и соответствовать позиционированию Axenix.
"""
        
        print("🤖 Генерирую идеи через Claude API...")
        
        try:
            message = self.client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text
            
            # Парсим JSON из ответа
            try:
                # Ищем JSON в ответе
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    suggestions = json.loads(json_str)
                else:
                    raise ValueError("JSON не найден в ответе")
            except json.JSONDecodeError as e:
                print(f"⚠️ Ошибка парсинга JSON: {e}")
                print("Использую сырой ответ")
                suggestions = {"articles": [], "raw_response": response_text}
            
            return suggestions
            
        except Exception as e:
            print(f"❌ Ошибка при обращении к Claude API: {e}")
            return None
    
    def save_suggestions(self, suggestions, analysis):
        """Сохраняет рекомендации в Markdown файл"""
        
        # Создаём папку если её нет
        suggestions_dir = Path('suggestions')
        suggestions_dir.mkdir(exist_ok=True)
        
        # Название файла
        filename = suggestions_dir / f'week_{self.week_number}.md'
        
        # Формируем Markdown
        markdown_content = f"""# 📝 Content Recommendations - Week {self.week_number}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## 📊 Market Analysis Summary

### Axenix Position
- **Total Mentions:** {analysis['axenix']['mentions']} ({analysis['axenix']['mentions'] / analysis['total_market_mentions'] * 100:.1f}% of market)
- **Positive Sentiment:** {analysis['axenix']['sentiment_positive']}%
- **Main Topics:** {', '.join(analysis['axenix']['topics'].keys())}

### Top Competitors
"""
        
        for comp in analysis['competitors']:
            markdown_content += f"- **{comp['name'].upper()}**: {comp['mentions']} mentions | Topics: {', '.join(comp['key_topics'].keys())}\n"
        
        markdown_content += f"""
### Market Trends (Top Topics)
"""
        for trend in analysis['trending_topics'][:5]:
            markdown_content += f"- {trend['topic']}: **{trend['mentions']}** mentions\n"
        
        markdown_content += f"""
### Opportunities (Gaps to Fill)
Where competitors talk more than Axenix:
"""
        for gap in analysis['gaps'][:3]:
            markdown_content += f"- **{gap['topic']}**: {gap['gap_percentage']:.0f}% gap (competitors mention +{gap['gap_percentage']:.0f}% more)\n"
        
        markdown_content += """
---

## 💡 Article Ideas

"""
        
        if suggestions and 'articles' in suggestions:
            for i, article in enumerate(suggestions['articles'], 1):
                markdown_content += f"""
### #{i}. {article.get('title', 'Untitled')}

**Priority:** {article.get('priority', 'MEDIUM')}

**Description:** {article.get('description', '')}

**Target Audience:** {article.get('target_audience', '')}

**Why This Matters:** {article.get('why_this_matters', '')}

**Key Topics:** {', '.join(article.get('key_topics', []))}

**SEO Keywords:** {article.get('seo_keywords', '')}

**Estimated Word Count:** {article.get('estimated_word_count', 2500)} слов

**Suggested Outline:**
"""
                for outline_point in article.get('suggested_outline', []):
                    markdown_content += f"- {outline_point}\n"
                
                markdown_content += "\n---\n"
        
        else:
            markdown_content += """
⚠️ Suggestions could not be generated. Check API key and try again.
"""
        
        # Сохраняем файл
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✅ Suggestions saved to {filename}")
        return str(filename)
    
    def run(self):
        """Запускает весь процесс"""
        print("\n🚀 Starting Article Suggestions Generator...\n")
        
        # Загружаем данные
        if not self.load_data():
            return False
        
        # Анализируем
        print("📈 Analyzing market data...")
        analysis = self.analyze_data()
        
        print(f"   Axenix mentions: {analysis['axenix']['mentions']}")
        print(f"   Market share: {analysis['axenix']['mentions'] / analysis['total_market_mentions'] * 100:.1f}%")
        print(f"   Key gaps: {len(analysis['gaps'])} opportunities found")
        
        # Генерируем
        suggestions = self.generate_suggestions(analysis)
        
        if not suggestions:
            print("❌ Failed to generate suggestions")
            return False
        
        # Сохраняем
        filename = self.save_suggestions(suggestions, analysis)
        
        print(f"\n✅ Content recommendations ready!")
        print(f"📂 File: {filename}")
        
        return True


if __name__ == '__main__':
    generator = ArticleSuggestionsGenerator()
    success = generator.run()
    exit(0 if success else 1)
