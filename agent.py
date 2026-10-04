import os
import urllib.request
import xml.etree.ElementTree as ET
from openai import OpenAI

def fetch_rss_news(url):
    """Метод с маскировкой под настоящий браузер для обхода блокировок"""
    try:
        # Маскируемся под обычный браузер Chrome на Windows
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
            
        # Парсим XML (структуру RSS) вручную встроенными силами Python
        root = ET.fromstring(xml_data)
        articles = []
        
        # В RSS новости лежат внутри тегов <item>
        for item in root.findall('.//item')[:10]:
            title = item.find('title')
            link = item.find('link')
            desc = item.find('description')
            
            title_text = title.text if title is not None else ''
            link_text = link.text if link is not None else ''
            desc_text = desc.text if desc is not None else ''
            
            if title_text:
                articles.append(f"Заголовок: {title_text}\nОписание: {desc_text}\nСсылка: {link_text}\n---")
        return articles
    except Exception as e:
        print(f"⚠️ Ошибка при чтении ленты {url}: {e}")
        return []

def run_agent():
    # 1. Задаем жесткий список источников прямо в коде, чтобы не зависеть от файлов
    urls = [
        "https://www.sport.ru/rssfeeds/news.rss",        # Стабильная общая спортивная лента
        "https://barentsobserver.com"          # Скандинавский вестник на русском
    ]

    # 2. Читаем интересы пользователя
    interests = "Собери главные новости про лыжные гонки."
    if os.path.exists('interests.txt'):
        with open('interests.txt', 'r', encoding='utf-8') as f:
            interests = f.read()

    # 3. Собираем новости
    all_news = []
    print(f"🔄 Запуск обхода {len(urls)} источников с маскировкой под браузер...")
    
    for url in urls:
        news_from_source = fetch_rss_news(url)
        print(f"📖 Источник {url} отдал {len(news_from_source)} новостей.")
        all_news.extend(news_from_source)

    if not all_news:
        print("❌ ОШИБКА: Не удалось собрать ни одной новости даже с маскировкой. Защита сайтов заблокировала робота.")
        return

    raw_news_text = "\n".join(all_news)

    # 4. Обращаемся к OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ ОШИБКА: Не найден OPENAI_API_KEY в Секретах GitHub!")
        return

    try:
        client = OpenAI(api_key=api_key)

        system_instruction = f"""
        Ты — профессиональный спортивный аналитик, эксперт в лыжных гонках.
        Изучи сырой список спортивных новостей.
        
        Выполни задачи:
        1. Отфильтруй новости строго по правилам пользователя: {interests}
           (Оставляй ТОЛЬКО новости, прямо или косвенно связанные с зимними видами спорта, лыжными гонками, спортсменами скандинавских стран и России).
        2. Удали явные дубликаты.
        3. Оформи результат строго в формате JSON (массив объектов), где у каждой новости будут поля: "title", "summary", "link".
        Отвечай ТОЛЬКО чистым JSON массивом, без разметки ```json в начале и конце.
        """

        print("🧠 Отправляю собранное в OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Свежие новости:\n\n{raw_news_text}"}
            ],
            temperature=0.3
        )

        ai_result = response.choices.message.content.strip()
        print("✅ ИИ успешно отфильтровал и вернул JSON.")
        
    except Exception as e:
        print(f"❌ ОШИБКА при запросе к OpenAI: {e}")
        return

    # 5. Генерируем HTML-страницу
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
                <p class="text-slate-500 mt-2">Свежие и отфильтрованные новости лыжного спорта</p>
            </header>
            <main id="news-container" class="space-y-6"><!-- Новости --></main>
        </div>
        <script>
            try {{
                const newsData = {ai_result};
                const container = document.getElementById('news-container');
                if (Array.isArray(newsData) && newsData.length > 0) {{
                    newsData.forEach(item => {{
                        const article = document.createElement('article');
                        article.className = 'p-6 bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition';
                        article.innerHTML = `
                            <h2 class="text-xl font-bold text-slate-900"><a href="${{item.link}}" target="_blank" class="hover:text-blue-600">${{item.title}}</a></h2>
                            <p class="mt-2 text-slate-600 leading-relaxed">${{item.summary}}</p>
                            <div class="mt-3"><a href="${{item.link}}" target="_blank" class="text-sm font-semibold text-blue-500 hover:underline">Читать оригинал →</a></div>
                        `;
                        container.appendChild(article);
                    }});
                }} else {{
                    container.innerHTML = '<p class="text-center text-slate-500">Пока нет громких лыжных новостей, соответствующих фильтрам.</p>';
                }}
            }} catch(e) {{
                document.getElementById('news-container').innerHTML = '<p class="text-center text-red-500">Ошибка обработки данных ИИ.</p>';
            }}
        </script>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    print("💾 Файл index.html успешно создан и записан!")

if __name__ == "__main__":
    run_agent()
