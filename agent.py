
   
               
      
     
   
            
         
                    import os
import feedparser
from openai import OpenAI

def run_agent():
    # 1. Читаем адреса сайтов (из файла sources.txt)
    if not os.path.exists('sources.txt'):
        print("❌ ОШИБКА: Файл sources.txt не найден!")
        return
        
    with open('sources.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    # 2. Читаем твои интересы для фильтрации (из файла interests.txt)
    interests = "Собери главные новости про лыжные гонки."
    if os.path.exists('interests.txt'):
        with open('interests.txt', 'r', encoding='utf-8') as f:
            interests = f.read()

    # 3. Собираем свежие новости из всех лент
    all_news = []
    print(f"🔄 Начинаю обход {len(urls)} источников...")
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            print(f"📖 Читаю ленту: {url} (Найдено статей: {len(feed.entries)})")
            for entry in feed.entries[:7]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                all_news.append(f"Заголовок: {title}\nОписание: {summary}\nСсылка: {link}\n---")
        except Exception as e:
            print(f"⚠️ Предупреждение: Ошибка при чтении {url}: {e}")

    if not all_news:
        print("❌ ОШИБКА: Не удалось собрать ни одной новости из источников. Проверь ссылки.")
        return

    raw_news_text = "\n".join(all_news)

    # 4. Проверяем ключ OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ ОШИБКА: Не найден OPENAI_API_KEY в Секретах GitHub!")
        return

    try:
        client = OpenAI(api_key=api_key)

        system_instruction = f"""
        Ты — профессиональный спортивный аналитик и переводчик, эксперт в лыжных гонках.
        Твоя задача — изучить сырой список новостей (там есть тексты на шведском, норвежском и русском).
        
        Сделай следующее:
        1. Отфильтруй новости строго по правилам пользователя: {interests}
        2. Удали дубликаты. Объедини похожие новости в одну.
        3. Переведи всё на качественный русский язык.
        4. Оформи результат строго в формате JSON (массив объектов), где у каждой новости будут поля: "title", "summary", "link".
        Отвечай ТОЛЬКО чистым JSON массивом, без разметки ```json.
        """

        print("🧠 Отправляю новости на анализ в ИИ...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Вот список свежих новостей:\n\n{raw_news_text}"}
            ],
            temperature=0.3
        )

        ai_result = response.choices.message.content.strip()
        print("✅ ИИ успешно вернул ответ.")
        
    except Exception as e:
        print(f"❌ ОШИБКА при запросе к OpenAI: {e}")
        print("Подсказка: Проверь, привязан ли баланс (карта) к твоему OpenAI API аккаунту.")
        return

    # 5. Генерируем HTML-страницу лендинга
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
                <p class="text-slate-500 mt-2">Свежие новости Скандинавии и России без дублей и спама</p>
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
                        article.className = 'p-6 bg-white rounded-2xl shadow-sm border border-slate-100';
                        article.innerHTML = `
                            <h2 class="text-xl font-bold text-slate-900"><a href="${{item.link}}" target="_blank">${{item.title}}</a></h2>
                            <p class="mt-2 text-slate-600">${{item.summary}}</p>
                        `;
                        container.appendChild(article);
                    }});
                }} else {{
                    container.innerHTML = '<p class="text-center text-slate-500">Нет новостей по вашим фильтрам.</p>';
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
    print("💾 Файл index.html успешно обновлен!")

if __name__ == "__main__":
    run_agent()
