import os
import feedparser
from openai import OpenAI

def run_agent():
    # 1. Читаем адреса сайтов (из файла sources.txt)
    if not os.path.exists('sources.txt'):
        print("Файл sources.txt не найден!")
        return
        
    with open('sources.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    # 2. Читаем твои интересы для фильтрации (из файла interests.txt)
    interests = "Собери главные новости про лыжные гонки." # На всякий случай, если файл пустой
    if os.path.exists('interests.txt'):
        with open('interests.txt', 'r', encoding='utf-8') as f:
            interests = f.read()

    # 3. Собираем свежие новости из всех лент
    all_news = []
    print(f"Начинаю обход {len(urls)} источников...")
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            # Берем первые 7 последних новостей с каждого сайта, чтобы не перегружать ИИ
            for entry in feed.entries[:7]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                
                all_news.append(f"Заголовок: {title}\nОписание: {summary}\nСсылка: {link}\n---")
        except Exception as e:
            print(f"Ошибка при чтении {url}: {e}")

    if not all_news:
        print("Не удалось собрать ни одной новости.")
        return

    # Объединяем собранные новости в один большой текст для отправки в ИИ
    raw_news_text = "\n".join(all_news)

    # 4. Просим ИИ отфильтровать дубли, перевести и сделать выжимку
    # GitHub автоматически подставит ключ OpenAI из настроек, которые мы сделаем позже
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Ошибка: Не найден OPENAI_API_KEY в переменных окружения.")
        return

    client = OpenAI(api_key=api_key)

    # Составляем строгую инструкцию (Промпт) для ИИ-модели
    system_instruction = f"""
    Ты — профессиональный спортивный аналитик и переводчик, эксперт в лыжных гонках.
    Твоя задача — изучить сырой список новостей (там есть тексты на шведском, норвежском и русском).
    
    Сделай следующее:
    1. Отфильтруй новости строго по правилам пользователя:
       {interests}
    2. Удали дубликаты. Если несколько сайтов пишут об одном и том же событии, объедини их в ОДНУ качественную новость.
    3. Переведи всё на качественный русский язык.
    4. Оформи результат строго в формате JSON (массив объектов), где у каждой новости будут поля:
       "title" (понятный заголовок на русском),
       "summary" (краткая выжимка сути в 2-3 предложениях на русском),
       "link" (ссылка на оригинал, если объединил дубли — оставь любую одну рабочую ссылку).
       
    Отвечай ТОЛЬКО чистым JSON без лишнего текста и без кавычек ```json.
    """

    print("Отправляю новости на анализ в ИИ...")
    response = client.chat.completions.create(
        model="gpt-4o-mini", # Быстрая, умная и очень дешевая модель
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Вот список свежих новостей:\n\n{raw_news_text}"}
        ],
        temperature=0.3 # Низкая температура, чтобы ИИ не выдумывал новости от себя
    )

    ai_result = response.choices.message.content.strip()

    # 5. Генерируем красивую HTML-страницу лендинга с результатами
    # Чтобы не усложнять, мы превратим ответ ИИ в структурированный сайт
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
                <div class="inline-block mt-4 px-3 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
                    Обновлено автоматически
                </div>
            </header>
            
            <main id="news-container" class="space-y-6">
                <!-- Новости будут вставлены сюда с помощью скрипта -->
            </main>
            
            <footer class="mt-16 text-center text-xs text-slate-400 border-t border-slate-200 pt-6">
                Создано твоим персональным ИИ-агентом на GitHub Pages
            </footer>
        </div>

        <script>
            // Передаем данные из ИИ напрямую в JavaScript на странице
            const newsData = {ai_result};
            
            const container = document.getElementById('news-container');
            
            if (Array.isArray(newsData) && newsData.length > 0) {{
                newsData.forEach(item => {{
                    const article = document.createElement('article');
                    article.className = 'p-6 bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition duration-200';
                    article.innerHTML = `
                        <h2 class="text-xl font-bold text-slate-900 hover:text-blue-600 transition">
                            <a href="${{item.link}}" target="_blank">${{item.title}}</a>
                        </h2>
                        <p class="mt-2 text-slate-600 leading-relaxed">${{item.summary}}</p>
                        <div class="mt-4">
                            <a href="${{item.link}}" target="_blank" class="text-sm font-semibold text-blue-500 hover:text-blue-700">Читать источник →</a>
                        </div>
                    `;
                    container.appendChild(article);
                }});
            }} else {{
                container.innerHTML = '<p class="text-center text-slate-500">Свежих новостей по выбранным критериям пока нет.</p>';
            }}
        </script>
    </body>
    </html>
    """

    # Сохраняем получившийся сайт в файл index.html
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("Успех! Файл index.html обновлен свежими новостями.")

if __name__ == "__main__":
    run_agent()
