import os
import urllib.request
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

def fetch_rss_news(url):
    """Продвинутый сборщик новостей со скандинавских и российских лыжных сайтов"""
    try:
        # Усиленная маскировка под обычный домашний браузер
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=20) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        articles = []
        
        # Обходим элементы структуры RSS
        for item in root.findall('.//item')[:10]:
            title = item.find('title')
            link = item.find('link')
            desc = item.find('description')
            
            title_text = title.text.strip() if (title is not None and title.text) else ''
            link_text = link.text.strip() if (link is not None and link.text) else ''
            desc_text = desc.text.strip() if (desc is not None and desc.text) else ''
            
            # Очищаем описание от HTML-тегов, если они там есть
            if desc_text:
                desc_text = ET.fromstring(f"<p>{desc_text}</p>").itertext()
                desc_text = "".join(desc_text)[:250]
                
            if title_text:
                articles.append({
                    "title": title_text,
                    "summary": desc_text if desc_text else "Посмотреть подробности на сайте источника.",
                    "link": link_text
                })
        return articles
    except Exception as e:
        print(f"⚠️ Пропущена лента {url} из-за особенности структуры: {e}")
        return []

def run_agent():
    # 1. Подключаем прямые официальные RSS-каналы указанных сайтов
    urls = [
        "https://langd.se",         # Швеция
        "https://langrenn.com",     # Норвегия
        "https://openski.ru"            # Россия
    ]

    # 2. Собираем новости со всех трех целевых ресурсов
    all_news = []
    print("🎿 Запуск ИИ-агента по скандинавским и российским лыжным базам...")
    for url in urls:
        source_articles = fetch_rss_news(url)
        print(f"📖 {url} успешно отдал {len(source_articles)} статей.")
        all_news.extend(source_articles)

    if not all_news:
        print("❌ ОШИБКА: Ни один целевой сайт не отдал данные. Проверь блокировки.")
        return

    # Превращаем собранные данные в структурированный текст для ИИ
    raw_news_text = ""
    for idx, a in enumerate(all_news[:20]): # Передаем топ-20 свежих статей
        raw_news_text += f"Новость №{idx}\nЗаголовок: {a['title']}\nОписание: {a['summary']}\nСсылка: {a['link']}\n---\n"

    api_key = os.environ.get("OPENAI_API_KEY")
    ai_success = False
    ai_result_json = ""

    # 3. Переводим и фильтруем через OpenAI (если баланс пополнен)
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            print("🧠 Передаю скандинавские тексты на перевод и фильтрацию в OpenAI...")
            
            interests = "Собери результаты гонок, трансферы, интервью, разборы. Не публикуй биатлон и рекламу магазинов."
            if os.path.exists('interests.txt'):
                with open('interests.txt', 'r', encoding='utf-8') as f:
                    interests = f.read()

            system_instruction = f"""
            Ты — главный редактор лыжного портала, эксперт в лыжных гонках (Cross-Country Skiing).
            Перед тобой список заголовков и описаний на шведском, норвежском и русском языках.
            
            Выполни задачи:
            1. Отбери новости по правилам: {interests}.
            2. Полностью переведи заголовки и выжимку на качественный, понятный русский язык. 
            3. Если шведский и норвежский сайты пишут про одно и то же событие — объедини их в ОДНУ запись.
            4. Верни ответ СТРОГО в формате JSON-массива: [{"title": "Заголовок на русском", "summary": "Выжимка 2-3 предложения на русском", "link": "оригинальная ссылка"}].
            Не пиши пометки ```json, отдавай только чистый текст структуры.
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": raw_news_text}
                ],
                temperature=0.2
            )
            ai_result_json = response.choices.message.content.strip()
            if ai_result_json and ai_result_json != "[]":
                ai_success = True
                print("✅ OpenAI успешно перевел шведские/норвежские новости!")
        except Exception as e:
            print(f"⚠️ Ошибка OpenAI ({e}). Работает резервный режим без ИИ...")

    # 4. Резервный режим на случай отсутствия связи с OpenAI (только лыжные ключевые слова)
    if not ai_success:
        ski_keywords = ["ski", "langd", "löp", "vm", "sm", "гонк", "лыж", "кубок", "большунов", "клэбо", "лыжн", "lopp"]
        filtered = []
        for a in all_news:
            text_to_check = (a['title'] + a['summary']).lower()
            if any(kw in text_to_check for kw in ski_keywords):
                filtered.append(a)
        
        # Если ничего не отфильтровалось, выводим свежие статьи как есть
        if not filtered:
            filtered = all_news[:8]
            
        ai_result_json = json.dumps(filtered, ensure_ascii=False)

    # 5. Перезаписываем наш сайт-лендинг
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Лыжный Эксперт — ИИ Дайджест</title>
        <script src="https://jsdelivr.net"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 font-sans antialiased">
        <div class="max-w-4xl mx-auto py-12 px-4">
            <header class="mb-12 text-center border-b border-slate-800 pb-8">
                <span class="text-5xl">🎿</span>
                <h1 class="text-4xl font-black text-white mt-3 tracking-tight">XC Skiing AI Agent</h1>
                <p class="text-slate-400 mt-2 text-lg">Эксклюзивные переводы из Швеции, Норвегии и России без спама</p>
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
                        article.className = 'p-6 bg-slate-800/60 rounded-2xl border border-slate-700/50 hover:border-blue-500/50 transition duration-300 backdrop-blur-sm';
                        article.innerHTML = `
                            <h2 class="text-2xl font-bold text-white hover:text-blue-400 transition">
                                <a href="${{item.link}}" target="_blank">${{item.title}}</a>
                            </h2>
                            <p class="mt-3 text-slate-300 leading-relaxed text-base">${{item.summary}}</p>
                            <div class="mt-4 border-t border-slate-700/50 pt-3 flex justify-between items-center">
                                <a href="${{item.link}}" target="_blank" class="text-sm font-semibold text-blue-400 hover:text-blue-300 transition">Перейти к оригиналу →</a>
                            </div>
                        `;
                        container.appendChild(article);
                    }});
                }} else {{
                    container.innerHTML = '<p class="text-center text-slate-400 text-lg">На целевых сайтах пока нет свежих новостей по вашим фильтрам.</p>';
                }}
            }} catch(e) {{
                document.getElementById('news-container').innerHTML = '<p class="text-center text-red-400">Ошибка разбора структуры данных.</p>';
            }}
        </script>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    print("💾 Чистый лыжный index.html успешно обновлен!")

if __name__ == "__main__":
    run_agent()
