import os
import urllib.request
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

def fetch_rss_news(url):
    """Безопасный сбор новостей с маскировкой под браузер"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        articles = []
        
        for item in root.findall('.//item')[:15]:
            title = item.find('title')
            link = item.find('link')
            desc = item.find('description')
            
            title_text = title.text if title is not None else ''
            link_text = link.text if link is not None else ''
            desc_text = desc.text if desc is not None else ''
            
            if title_text:
                articles.append({
                    "title": title_text,
                    "summary": desc_text[:200] + "..." if len(desc_text) > 200 else desc_text,
                    "link": link_text
                })
        return articles
    except Exception as e:
        print(f"⚠️ Пропущена лента из-за ошибки: {e}")
        return []

def run_agent():
    # 1. Используем 100% стабильную и чистую спортивную RSS-ленту
    urls = [
        "https://www.sport.ru/rssfeeds/news.rss"
    ]

    # 2. Собираем новости
    all_news = []
    print("🔄 Запуск обхода спортивных источников...")
    for url in urls:
        all_news.extend(fetch_rss_news(url))

    if not all_news:
        print("❌ ОШИБКА: Не удалось собрать новости.")
        return

    # Превращаем собранное в текст для ИИ
    raw_news_text = ""
    for a in all_news[:10]:
        raw_news_text += f"Новость: {a['title']}\nОписание: {a['summary']}\nСсылка: {a['link']}\n---\n"

    # 3. Пробуем отправить в OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    ai_success = False
    ai_result_json = ""

    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            print("🧠 Отправляю собранное в OpenAI...")
            
            # Читаем фильтры интересов
            interests = "Оставляй новости про лыжные гонки, зимний спорт, российских и скандинавских лыжников."
            if os.path.exists('interests.txt'):
                with open('interests.txt', 'r', encoding='utf-8') as f:
                    interests = f.read()

            system_instruction = f"""
            Ты — эксперт в лыжных гонках. Из списка новостей оставь ТОЛЬКО те, которые соответствуют фильтру: {interests}.
            Удали дубликаты. Оформи результат строго в формате JSON: [{"title": "...", "summary": "...", "link": "..."}].
            Не используй разметку ```json. Отвечай только чистым массивом.
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": raw_news_text}
                ],
                temperature=0.3
            )
            ai_result_json = response.choices.message.content.strip()
            ai_success = True
            print("✅ ИИ успешно обработал новости!")
        except Exception as e:
            print(f"⚠️ Ошибка OpenAI ({e}). Включаю аварийный режим без ИИ...")

    # Если ИИ не сработал (нет денег на балансе), используем собранные новости напрямую
    if not ai_success:
        # Фильтруем новости по ключевым словам вручную (аварийный режим)
        keywords = ["лыж", "лыжн", "гонк", "большунов", "клэбо", "непряева", "коростелев", "коростелёв"]
        filtered = []
        for a in all_news:
            text_to_check = (a['title'] + a['summary']).lower()
            if any(kw in text_to_check for kw in keywords):
                filtered.append(a)
        
        # Если ручной фильтр ничего не нашёл, берём просто первые 5 спортивных новостей
        if not filtered:
            filtered = all_news[:5]
            
        ai_result_json = json.dumps(filtered, ensure_ascii=False)

    # 4. Генерируем HTML-страницу
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Лыжный ИИ-Дайджест</title>
        <script src="https://jsdelivr.net"></script>
    </head>
    <body class="bg-slate-50 text-slate-800 font-sans">
        <div class="max-w-4xl mx-auto py-12 px-4">
            <header class="mb-12 text-center">
                <span class="text-4xl">🎿</span>
                <h1 class="text-4xl font-black text-slate-900 mt-2 tracking-tight">Лыжный ИИ-Агент</h1>
                <p class="text-slate-500 mt-2">Свежие новости из мира лыжных гонок</p>
            </header>
            <main id="news-container" class="space-y-6"><!-- Новости --></main>
        </div>
        <script>
            try {{
                const newsData = {ai_result_json};
                const container = document.getElementById('news-container');
                if (Array.isArray(newsData) && newsData.length > 0) {{
                    newsData.forEach(item => {{
                        const article = document.createElement('article');
                        article.className = 'p-6 bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition duration-200';
                        article.innerHTML = `
                            <h2 class="text-xl font-bold text-slate-900"><a href="${{item.link}}" target="_blank" class="hover:text-blue-600">${{item.title}}</a></h2>
                            <p class="mt-2 text-slate-600">${{item.summary}}</p>
                            <div class="mt-3"><a href="${{item.link}}" target="_blank" class="text-sm font-semibold text-blue-500 hover:underline">Читать источник →</a></div>
                        `;
                        container.appendChild(article);
                    }});
                }} else {{
                    container.innerHTML = '<p class="text-center text-slate-500">Пока нет новостей по выбранным критериям.</p>';
                }}
            }} catch(e) {{
                document.getElementById('news-container').innerHTML = '<p class="text-center text-red-500">Ошибка отображения.</p>';
            }}
        </script>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    print("💾 Файл index.html успешно обновлен!")

if __name__ == "__main__":
    run_agent()
