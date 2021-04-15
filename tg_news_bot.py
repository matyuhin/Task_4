import sqlite3
import telebot
from telebot import types
from newsapi import NewsApiClient


token = ""  # Токен бота
api_key = ""  # Ключ newsapi.org
newsapi = NewsApiClient(api_key=api_key)
bot = telebot.TeleBot(token, parse_mode=None)
command_add_category = ('добавить категорию', 'добавить категории')
command_del_category = ('удалить категорию', 'удалить категории')
command_show_category = ('показать категории', 'показать категории')
command_add_keyword = ('добавить ключевые слова', 'добавить ключевое слово')
command_del_keyword = ('удалить ключевые слова', 'удалить ключевое слово')
command_show_keyword = ('показать ключевые слова')
command_show_news = ('показать новости')
help_text = """
Доступные команды:

 - <b>Добавить категорию &lt;название категорий через пробел&gt;</b> - Подписаться на категорию
   Доступны следующие категории: <b>business, entertainment, general, health, science, sports, technology</b>
 - <b>Удалить категорию &lt;название категорий через пробел&gt;</b> - Удалить категории из подписок
 - <b>Показать категории</b> - Вывести список категорий, на которые вы подписаны

 - <b>Добавить ключевые слова &lt;ключевые слова через пробел&gt;</b> - Подписаться на ключевые слова
 - <b>Удалить ключевые слова &lt;ключевые слова через пробел&gt;</b> - Удалить ключевые слова из подписок
 - <b>Показать ключевые слова</b> - Вывести список ключевых слов, на которые вы подписаны

 - <b>Показать новости</b> - Показать подборку новостей
"""


def create_db():
    """Подключение к БД и создание таблиц"""
    try:
        sqlite_connection = sqlite3.connect('telenews.db')
        sqlite_create_table_users = '''CREATE TABLE IF NOT EXISTS users (
                                        id INTEGER PRIMARY KEY,
                                        name TEXT NOT NULL);'''
        sqlite_create_table_category = '''CREATE TABLE IF NOT EXISTS categories (
                                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            name TEXT NOT NULL,
                                            user_id INTEGER SECONDARY KEY);'''
        sqlite_create_table_keywords = '''CREATE TABLE IF NOT EXISTS keywords (
                                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            name TEXT NOT NULL,
                                            user_id INTEGER SECONDARY KEY);'''

        cursor = sqlite_connection.cursor()
        print("База данных подключена к SQLite")
        cursor.execute(sqlite_create_table_users)
        cursor.execute(sqlite_create_table_category)
        cursor.execute(sqlite_create_table_keywords)
        sqlite_connection.commit()
        print("Таблица SQLite создана")
        cursor.close()
    except sqlite3.Error as error:
        print("Ошибка при подключении к sqlite", error)
    finally:
        if (sqlite_connection):
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")

@bot.message_handler(commands=['help'])
def help_message(message):
    msg = bot.reply_to(message, help_text, parse_mode="html")

@bot.message_handler(commands=['Показать категории'])
def show_news_message(message):
    msg = bot.reply_to(message, help_text, parse_mode="html")


@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    rows = []
    try:
        sqlite_connection = sqlite3.connect('telenews.db')
        cursor = sqlite_connection.cursor()
        sqlite_show_with_param = """SELECT name FROM users WHERE id = ?"""
        data_tuple = (user_id,)
        cursor.execute(sqlite_show_with_param, data_tuple)
        rows = cursor.fetchall()
        sqlite_connection.commit()
        cursor.close()
    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")
        if len(rows) !=0:
            msg = bot.reply_to(message, f"Привет {rows[0][0]}")
        else:
            msg = bot.reply_to(message, "Напишите Ваше имя")
            bot.register_next_step_handler(msg, add_user)


def add_user(message):
    """Добавление пользователя в базу"""
    user_id = message.from_user.id
    name = message.text
    try:
        sqlite_connection = sqlite3.connect('telenews.db')
        cursor = sqlite_connection.cursor()
        sqlite_show_with_param = """SELECT name FROM users WHERE id = ?"""
        data_tuple = (user_id,)
        cursor.execute(sqlite_show_with_param, data_tuple)
        rows = cursor.fetchall()
        print(rows)

        sqlite_insert_with_param = """INSERT INTO users
                                      (id, name)
                                      VALUES (?, ?);"""
        data_tuple = (user_id, name)
        cursor.execute(sqlite_insert_with_param, data_tuple)
        sqlite_connection.commit()
        print("Запись успешно вставлена в таблицу users ", cursor.rowcount)
        cursor.close()

    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")
        bot.send_message(message.from_user.id, f"""Привет, {name}!
Я помогу тебе получать только самые важные новости. 
Загляни в /help, чтобы посмотреть, что я умею""")


def get_news(query):
    """Получение подборки новостей"""
    list_keywords = show_keyword(query)
    list_category = show_category(query)
    list_sources = []
    list_news = []
    if len(list_category) > 0:
        for category in list_category:
            sources = newsapi.get_sources(category=category)
            print()
            for source in sources['sources']:
                list_sources.append(source['id'])
        response = newsapi.get_everything(
                                          q=' OR '.join(list_keywords),
                                          sources=','.join(list_sources),
                                          sort_by='relevancy',
                                          page_size=10
                                          )
    elif len(list_keywords) > 0:
        response = newsapi.get_everything(
            q=' OR '.join(list_keywords),
            sort_by='relevancy',
            page_size=10
        )
    else:
        response = {"articles": []}

    if len(response["articles"]) < 10:
        count_news = len(response["articles"])
    else:
        count_news = 10
    if len(response["articles"]) > 0:
        for i in range(count_news):
            list_news.append({
                "title": response["articles"][i]["title"],
                "description": response["articles"][i]["description"],
                "url": response["articles"][i]["url"],
                "urlToImage": response["articles"][i]["urlToImage"],
                "publishedAt": response["articles"][i]["publishedAt"],
                "content": response["articles"][i]["content"],
            })
    return list_news


def show_keyword(query):
    """Просмотр списка ключевых слов из базы"""
    user_id = query['user_id']
    list_keyword = []
    rows = []
    try:
        sqlite_connection = sqlite3.connect('telenews.db')
        cursor = sqlite_connection.cursor()
        sqlite_show_with_param = """SELECT name FROM keywords WHERE user_id = ?"""
        data_tuple = (user_id,)
        cursor.execute(sqlite_show_with_param, data_tuple)
        rows = cursor.fetchall()
        sqlite_connection.commit()
        cursor.close()
    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")
        if len(rows) > 0:
            for item in rows:
                list_keyword.append(item[0])
    return list_keyword


def add_keyword(query):
    """Добавление ключевых слов в базу"""
    user_id = query['user_id']
    keywords = query['options']
    print(show_keyword(query))
    failed = []
    for keyword in keywords:
        if not check_exist('keywords', keyword, user_id):
            try:
                sqlite_connection = sqlite3.connect('telenews.db')
                cursor = sqlite_connection.cursor()
                sqlite_insert_with_param = """INSERT INTO keywords
                                                  (name, user_id)
                                                  VALUES (?, ?);"""
                data_tuple = (keyword, user_id)
                cursor.execute(sqlite_insert_with_param, data_tuple)
                sqlite_connection.commit()
                print(f"Запись {keyword} успешно добавлена в таблицу keyword", cursor.rowcount)
                cursor.close()
            except sqlite3.Error as error:
                print("Ошибка при работе с SQLite", error)
            finally:
                if sqlite_connection:
                    sqlite_connection.close()
                    print("Соединение с SQLite закрыто")
        else:
            failed.append(f"Вы уже подписаны на ключевые слова {keyword}\n")
    return failed


def del_keyword(query):
    """Удаление ключевых слов из базы"""
    user_id = query['user_id']
    keywords = query['options']
    failed = []
    for keyword in keywords:
        if check_exist('keywords', keyword, user_id):
            try:
                sqlite_connection = sqlite3.connect('telenews.db')
                cursor = sqlite_connection.cursor()
                sqlite_delete_with_param = """DELETE FROM keywords WHERE name = ? AND user_id = ?"""
                data_tuple = (keyword, user_id)
                cursor.execute(sqlite_delete_with_param, data_tuple)
                sqlite_connection.commit()
                print(f"Запись {keyword} успешно удалена из таблицы keywords", cursor.rowcount)
                cursor.close()
            except sqlite3.Error as error:
                print("Ошибка при работе с SQLite", error)
            finally:
                if sqlite_connection:
                    sqlite_connection.close()
                    print("Соединение с SQLite закрыто")
        else:
            failed.append(f"Вы не подписаны на ключевые слова {keyword}\n")
    return failed


def show_category(query):
    """Просмотр списка категорий из базы"""
    user_id = query['user_id']
    list_category = []
    rows = []
    try:
        sqlite_connection = sqlite3.connect('telenews.db')
        cursor = sqlite_connection.cursor()
        sqlite_show_with_param = """SELECT name FROM categories WHERE user_id = ?"""
        data_tuple = (user_id,)
        cursor.execute(sqlite_show_with_param, data_tuple)
        rows = cursor.fetchall()
        sqlite_connection.commit()
        cursor.close()
    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")
        if len(rows) > 0:
            for item in rows:
                list_category.append(item[0])
    return list_category


def add_category(query):
    """Добавление категории в базу"""
    user_id = query['user_id']
    categories = query['options']
    list_category = ("business", "entertainment", "general", "health", "science", "sports", "technology")
    failed = []
    for category in categories:
        if category in list_category:
            if not check_exist('categories', category, user_id):
                try:
                    sqlite_connection = sqlite3.connect('telenews.db')
                    cursor = sqlite_connection.cursor()
                    sqlite_insert_with_param = """INSERT INTO categories
                                                      (name, user_id)
                                                      VALUES (?, ?);"""
                    data_tuple = (category, user_id)
                    cursor.execute(sqlite_insert_with_param, data_tuple)
                    sqlite_connection.commit()
                    print(f"Запись {category} успешно добавлена в таблицу category", cursor.rowcount)
                    cursor.close()
                except sqlite3.Error as error:
                    print("Ошибка при работе с SQLite", error)
                finally:
                    if sqlite_connection:
                        sqlite_connection.close()
                        print("Соединение с SQLite закрыто")
            else:
                failed.append(f"Вы уже подписаны на категорию {category}\n")
        else:
            failed.append(f"Недопустимые категории: {category}.  Загляни в /help\n")
    return failed

def del_category(query):
    """Удаление категории из базы"""
    user_id = query['user_id']
    categories = query['options']
    failed = []
    for category in categories:
        if check_exist('categories', category, user_id):
            try:
                sqlite_connection = sqlite3.connect('telenews.db')
                cursor = sqlite_connection.cursor()
                sqlite_delete_with_param = """DELETE FROM categories WHERE name = ? AND user_id = ?"""
                data_tuple = (category, user_id)
                cursor.execute(sqlite_delete_with_param, data_tuple)
                sqlite_connection.commit()
                print(f"Запись {category} успешно удалена из таблицы categories", cursor.rowcount)
                cursor.close()
            except sqlite3.Error as error:
                print("Ошибка при работе с SQLite", error)
            finally:
                if sqlite_connection:
                    sqlite_connection.close()
                    print("Соединение с SQLite закрыто")
        else:
            failed.append(f"Вы не подписаны на категорию {category}\n")
    return failed


def parse_msg(message):
    words = message.text.lower().split()
    key = ('ключевые', 'ключевое')
    if len(words) > 1:
        if words[1] in key:
            count_command = 3
        else:
            count_command = 2
        query = {"command": ' '.join(words[:count_command]), "options": words[count_command:],
                 "user_id": message.from_user.id}
    else:
        query = {'command': 'Неверная команда'}
    return query

def check_exist(table, name, user_id):
    list_category = []
    rows = []
    try:
        sqlite_connection = sqlite3.connect('telenews.db')
        cursor = sqlite_connection.cursor()
        sqlite_show_with_param = f"""SELECT name FROM {table} WHERE name = ? AND user_id = ?"""
        data_tuple = (name, user_id)
        cursor.execute(sqlite_show_with_param, data_tuple)
        rows = cursor.fetchall()
        sqlite_connection.commit()
        cursor.close()
    except sqlite3.Error as error:
        print("Ошибка при работе с SQLite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")
        if len(rows) > 0:
            for item in rows:
                list_category.append(item[0])
    if len(list_category):
        return True
    else:
        return False



@bot.message_handler(func=lambda message: True)
def answer_to_message(message):
    query = parse_msg(message)
    print(query['command'])
    if query['command'] in command_add_category:
        failed = add_category(query)
        if len(failed):
            bot.send_message(message.from_user.id,''.join(failed))
        else:
            bot.send_message(message.from_user.id, f"Категории: {', '.join(query['options'])} добавлены в ваши подписки")
    elif query['command'] in command_del_category:
        failed_del_category = del_category(query)
        if len(failed_del_category):
            bot.send_message(message.from_user.id,''.join(failed_del_category))
        else:
            bot.send_message(message.from_user.id, f"Категории: {', '.join(query['options'])} удалены из ваших подписок")
    elif query['command'] in command_show_category:
        list_category = show_category(query)
        if len(list_category) > 0:
            bot.send_message(message.from_user.id, f"Вы подписаны на следующие категории: {', '.join(list_category)}")
        else:
            bot.send_message(message.from_user.id, f"Вы не подписаны ни на одну категорию")
    elif query['command'] in command_add_keyword:
        failed_add_keyword = add_keyword(query)
        if len(failed_add_keyword):
            bot.send_message(message.from_user.id, ''.join(failed_add_keyword))
        else:
            bot.send_message(message.from_user.id, f"Ключевые слова: {', '.join(query['options'])} добавлены в ваши подписки")
    elif query['command'] in command_del_keyword:
        failed_del_keyword = del_keyword(query)
        if len(failed_del_keyword):
            bot.send_message(message.from_user.id, ''.join(failed_del_keyword))
        else:
            bot.send_message(message.from_user.id, f"Ключевые слова {', '.join(query['options'])} удалены из ваших подписок")
    elif query['command'] in command_show_keyword:
        list_keyword = show_keyword(query)
        if len(list_keyword) > 0:
            bot.send_message(message.from_user.id, f"Вы подписаны на следующие ключевые слова: {', '.join(list_keyword)}")
        else:
            bot.send_message(message.from_user.id,f"У вас нет ключевых слов!")
    elif query['command'] in command_show_news:
            list_news = get_news(query)
            if len(list_news) > 0:
                for i in range(len(list_news)):
                    title = list_news[i]["title"]
                    description = list_news[i]["description"]
                    url = list_news[i]["url"]
                    urlToImage = list_news[i]["urlToImage"]
                    publishedAt = list_news[i]["publishedAt"]
                    content = list_news[i]["content"]
                    markup = types.InlineKeyboardMarkup()
                    btn_more = types.InlineKeyboardButton(text='Подробнее', url=url)
                    markup.add(btn_more)
                    if list_news[i]["urlToImage"]:
                        try:
                            bot.send_photo(message.from_user.id, urlToImage,
                                       f"{title} \n\n {description}\n",reply_markup=markup)
                        except Exception:
                            print("Ошибка")
                            bot.send_message(message.from_user.id,
                                             f"{title}\n\n{description}\n",reply_markup=markup,
                                             disable_web_page_preview=True)
                    else:
                        bot.send_message(message.from_user.id,
                                         f"{title}\n\n{description}\n",reply_markup=markup,
                                         disable_web_page_preview=True)
            else:
                bot.send_message(message.from_user.id, f"К сожалению, по вашим подпискам нет новостей:-( ")
    else:
        bot.send_message(message.from_user.id, f"Команда не поддерживается. Загляни в /help")


create_db()
bot.polling()
