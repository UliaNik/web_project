import logging
import sqlite3
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup
import datetime
from dateutil.tz import gettz
import requests
from timezonefinder import TimezoneFinder
import pytz
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

TOKEN = 'BOT_TOKEN'
DAYS_OF_WEEK = {'Понедельник': 0, "Вторник": 1, "Среда": 2, "Четверг": 3,  # потребуется, чтобы делать из ответа
                "Пятница": 4, "Суббота": 5, "Воскресенье": 6}              # пользователя параметр для run_daily


task_types_keyboard = [['Разовая', 'Регулярная']]  # клавиатуры для создания задачи
markup_1 = ReplyKeyboardMarkup(task_types_keyboard, one_time_keyboard=True)
how_regularly_keyboard = [['Каждый день', 'В определённые дни недели', 'Каждый месяц']]
markup_2 = ReplyKeyboardMarkup(how_regularly_keyboard, one_time_keyboard=True)
task_types_2_keyboard = [['Конечная', 'Бесконечная']]
markup_3 = ReplyKeyboardMarkup(task_types_2_keyboard, one_time_keyboard=True)


def start_change_tz(update, context):  # начало разговора, чтобы задать новый часовой пояс
    update.message.reply_text(
        "Введите новую локацию.")
    return 1


def get_user_timezone(update, context):  # вычисляет часовой пояс в формате Etc/GMT из города, введенного
    city = update.message.text           # пользователеи
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&" \
                       f"geocode={city}&format=json"
    response = requests.get(geocoder_request)
    if response:
        json_response = response.json()
        toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        toponym_address = toponym["metaDataProperty"]["GeocoderMetaData"]["text"]
        ll = toponym["Point"]["pos"].split()  # получаем координаты объекта
        tf = TimezoneFinder()
        time = pytz.timezone(tf.timezone_at(lng=float(ll[0]), lat=float(ll[1]))).localize(
            datetime.datetime(2011, 1, 1)).strftime('%z')  # вычисляем часовой пояс
        if time[0] == '-':
            tz = 'Etc/GMT+' + time[2]
        else:
            tz = 'Etc/GMT-' + time[2]
        context.chat_data['timezone'] = tz  # сохраняем часовой пояс
        update.message.reply_text(
            "Спасибо! Часовой пояс определён.")
        return ConversationHandler.END
    update.message.reply_text(  # если геокодер ничего не нашел, просим пользователя ввести локацию еще раз
        "Город с таким названием не найден. "
        "Проверьте, нет ли в названии опечаток, или выберите другой, близлежащий, город.")
    return 1


def check_if_finish(context):  # проверяет для конечных задач, не пора ли им заканчиваться
    today = datetime.date.today()
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    result = cur.execute("""SELECT name FROM tasks
                            WHERE is_endless = 0
                            AND finish_time = ?""", (today,)).fetchall()
    if result:
        for elem in result:
            remove_job_if_exists(elem, context)
            cur.execute("""UPDATE tasks
                           SET is_finished = 1
                           WHERE name = ?""", (elem,))
            con.commit()
    con.close()


def start(update, context):  # запуск, пояснение
    update.message.reply_text(
        "Здравствуйте! Я ваш персональный бот для тайм-менеджмента. Я помогу вам эффективнее распоряжаться вашим временем\n\n"
        "Вот список того, что я умею:\n"
        "/start: приветствие, описание, список функций\n"
        "/create_task: создать задачу \n"
        "/finish_task [имя задачи]: завершить задачу\n"
        "/delete_task [имя задачи]: удалить задачу\n"
        "/all_tasks [дата]: вывести список задач на заданный день\n"
        "/unfinished_tasks[дата]: вывести список невыполненных задач на заданный день\n\n"
        "ВАЖНО: вводите даты в формате %d.%m.%y (30.01.22) \n"
        "       время - в формате %H:%M (13:56)")
    con = sqlite3.connect("tasks_db.sqlite")  # создаем базу данных, если бот запускается в первый раз
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS tasks(
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            is_regular INTEGER,
                            is_endless INTEGER,
                            regularity TEXT,
                            set_time TEXT,
                            do_time TEXT,
                            days TEXT,
                            finish_time TEXT,
                            is_finished INTEGER);""")
    con.close()
    chat_id = update.message.chat_id
    time = datetime.time(hour=00, minute=1)
    if not context.chat_data.get('timezone', 0):  # если запускается впервые, просим у пользователя локацию и
                                                  # вычисляем часовой пояс, а также ежедневно проверяем конечные
                                                  # задачи
        context.job_queue.run_daily(check_if_finish, time, context=chat_id, name='check_if_finish')
        update.message.reply_text(
            "Чтобы правильно работать, мне необходимо знать Ваш часовой пояс. В каком городе вы находитесь?")
        return 1
    return ConversationHandler.END


def remove_job_if_exists(name, context):  # удаляем работу, если существует
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def start_create_task(update, context):  # начало диалога для создания задачи
    update.message.reply_text(
        "Давайте создадим новую задачу!\n"
        "Если вы передумаете, используйте команду /stop.\n"
        "Как называется задача?")
    return 1


def stop_conversation(update, context):  # остановка (для всех диалогов)
    fox_request = f"https://randomfox.ca/floof"
    response = requests.get(fox_request)   # отправляем картинку лисы
    json_response = response.json()
    url = json_response["image"]
    chat_id = update.message.chat_id
    context.bot.send_photo(chat_id=chat_id,
                           photo=url, caption="Действие прекращено.")
    return ConversationHandler.END


def get_name(update, context):  # получаем имя задачи, проверяем, нет ли такого в базе данных
    context.user_data['task_name'] = update.message.text
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    res = cur.execute("""SELECT name from tasks
                         WHERE name = ? AND is_finished = 0""", (context.user_data['task_name'],)).fetchone()
    if res:
        update.message.reply_text("Задача с таким названием уже существует! Придумайте другое название.")
        con.close()
        return 1
    update.message.reply_text(
        f"Эта задача разовая или регулярная?",
        reply_markup=markup_1)
    return 2


def get_if_regular(update, context):  # в зависимости от типа задачи отправляем по разным веткам диалога
    context.user_data['task_is_regular'] = update.message.text
    if context.user_data['task_is_regular'] == 'Разовая':
        update.message.reply_text(
            f"Когда нужно выполнить {context.user_data['task_name']}?\n"
            f"Введите дату.")
        return 3
    else:
        update.message.reply_text(
            f"Как часто нужно выполнять {context.user_data['task_name']}?",
            reply_markup=markup_2)
    return 5


def get_one_date(update, context):  # получаем дату выполнения для разовой задачи
    context.user_data['task_finish_time'] = update.message.text
    update.message.reply_text(
        f"Во сколько нужно выполнить {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 4


def get_one_time(update, context):  # получаем время выполнения для разовой задачи, завершаем диалог
    context.user_data['task_finish_time'] = context.user_data.get('task_finish_time') + ' ' + update.message.text
    create_task_in_db(update, context)   # записываем в базу данных и создаем job
    fox_request = f"https://randomfox.ca/floof"   # отправляем картинку лисы
    response = requests.get(fox_request)
    json_response = response.json()
    url = json_response["image"]
    chat_id = update.message.chat_id
    context.bot.send_photo(chat_id=chat_id,
                           photo=url, caption="Задача создана!")
    return ConversationHandler.END


def get_reg_regularity(update, context):  # получаем регулярность (ежедневно, по определенным дням недели, ежемесячно)
    context.user_data['task_do_time'] = update.message.text  # для регулярных задач
    if context.user_data['task_do_time'] == 'Каждый месяц':  # в зависимости от типа отправляем по разным веткам диалога
        context.user_data['task_regularity'] = 'monthly'
        update.message.reply_text(
            f"По каким числам нужно выполнять {context.user_data['task_name']}?\n"
            f"Введите даты через пробел.")
        return 6
    if context.user_data['task_do_time'] == 'В определённые дни недели':
        context.user_data['task_regularity'] = 'week_daily'
        update.message.reply_text(
            f"По каким дням недели нужно выполнять {context.user_data['task_name']}?\n"
            f"Введите названия дней недели через пробел.")
        return 7
    else:
        context.user_data['task_regularity'] = 'daily'
    update.message.reply_text(
        f"Во сколько нужно выполнять {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 8


def get_week_days(update, context):   # получаем дни недели, по которым должна выполняться еженедельная задача
    days = update.message.text.split()  # сначала пыталась реализовать через Poll, но застопорилось, и сделала проще
    task_days = ''
    for elem in days:
        td = DAYS_OF_WEEK.get(elem.capitalize(), '')
        if td == '':
            update.message.reply_text(
                "Что-то пошло не так.\n"
                "Возможно, вы допустили опечатку в названии дня недели.\n"
                "Попробуйте ещё раз.")
            return 7
        task_days += str(td)
    context.user_data['task_days'] = task_days
    update.message.reply_text(
        f"Во сколько нужно выполнять {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 8


def get_reg_month_dates(update, context):   # получаем числа, по которым должны выполняться ежемесячные задачи
    task_days = update.message.text.split()
    td = []
    for date in task_days:   # если пользователь ввел однозначное число, то дописываем нолик
        if len(date) == 1:   # потому что в базе данных будет храниться строкой
            date = '0' + date  # будем сравнивать like %06%, не like %6%
        td.append(date)
    context.user_data['task_days'] = ' '.join(td)
    update.message.reply_text(
        f"Во сколько нужно выполнять {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 8


def get_reg_time(update, context):  # ветки для регулярных задач сошлись, получаем время выполнения
    context.user_data['task_do_time'] = update.message.text
    update.message.reply_text(
        f"Эта задача конечная или бесконечная?", reply_markup=markup_3)
    return 9


def get_if_endless(update, context):  # если бесконечная, заканчиваем диалог, конечная - спрашиваем конечную дату
    context.user_data['task_is_endless'] = update.message.text
    if context.user_data['task_is_endless'] == 'Конечная':
        update.message.reply_text(
            f"Когда нужно перестать выполнять {context.user_data['task_name']}?\n"
            f"Введите дату.")
        return 10
    else:
        create_task_in_db(update, context)  # записываем в базу данных и создаем job
        fox_request = f"https://randomfox.ca/floof"  # картинка лисы
        response = requests.get(fox_request)
        json_response = response.json()
        url = json_response["image"]
        chat_id = update.message.chat_id
        context.bot.send_photo(chat_id=chat_id,
                               photo=url, caption="Задача создана!")
        return ConversationHandler.END


def get_reg_end_date(update, context):  # получаем для конечной задачи конечную дату, завершаем диалог
    context.user_data['task_finish_time'] = update.message.text
    create_task_in_db(update, context)  # записываем в базу данных и создаем job
    fox_request = f"https://randomfox.ca/floof"  # картинка лисы
    response = requests.get(fox_request)
    json_response = response.json()
    url = json_response["image"]
    chat_id = update.message.chat_id
    context.bot.send_photo(chat_id=chat_id,
                           photo=url, caption="Задача создана!")
    return ConversationHandler.END


def create_task_in_db(update, context):  # записываем в базу данных и создаем job
    task_name = context.user_data['task_name']  # получаем все данные, сохраненные за диалог
    task_is_regular = 1 if context.user_data['task_is_regular'] == 'Регулярная' else 0
    task_is_endless = 1 if context.user_data.get('task_is_endless', '') == 'Бесконечная' else 0
    task_set_time = datetime.datetime.now(gettz(context.chat_data['timezone']))
    tz_f = pytz.timezone(context.chat_data['timezone'])
    task_regularity = context.user_data.get('task_regularity', '')
    task_days = context.user_data.get('task_days', '')
    if task_is_regular:  # для бд записываем дату+время, для создания job - только время
        do_time_no_tz = datetime.datetime.strptime(str(datetime.date.today()) + " " + context.user_data['task_do_time'],
                                                   '%Y-%m-%d %H:%M')
        task_do_time = do_time_no_tz.astimezone(tz_f)  # поправляем часовой пояс
        task_do_time_short = datetime.datetime.strptime(str(task_do_time)[11:16], '%H:%M')
    else:
        task_do_time = ''
    if not task_is_endless:
        if task_is_regular:  # для регулярной задачи - только дату, для разовой - дату+время
            finish_time_no_tz = datetime.datetime.strptime(context.user_data['task_finish_time'] + " " + "00:00",
                                                           '%d.%m.%y %H:%M')
        else:
            finish_time_no_tz = datetime.datetime.strptime(context.user_data['task_finish_time'], '%d.%m.%y %H:%M')
        task_finish_time = finish_time_no_tz.astimezone(tz_f)
    else:
        task_finish_time = ''
    task_is_finished = 0
    con = sqlite3.connect("tasks_db.sqlite")  # записываем в базу данных
    cur = con.cursor()
    cur.execute("""INSERT INTO tasks(name,is_regular,is_endless,regularity,
                       set_time,do_time,days,finish_time,is_finished) 
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                (task_name, task_is_regular, task_is_endless, task_regularity,
                 str(task_set_time), str(task_do_time), task_days, str(task_finish_time),
                 task_is_finished))
    con.commit()
    con.close()
    chat_id = update.message.chat_id
    if task_is_regular:  # создаем job
        if task_regularity == 'monthly':
            dates = [int(x) for x in task_days.split()]
            for date in dates:
                context.job_queue.run_monthly(remind, task_do_time_short, day=date, context=chat_id, name=task_name)
        elif task_regularity == 'week_daily':
            week_days = tuple(int(x) for x in task_days)
            context.job_queue.run_daily(remind, task_do_time_short, days=week_days, context=chat_id, name=task_name)
        else:
            context.job_queue.run_daily(remind, task_do_time_short, context=chat_id, name=task_name)
    else:
        context.job_queue.run_once(remind, task_finish_time, context=chat_id, name=task_name)
    context.user_data.clear()


def finish_task(update, context):  # завершаем задачу
    task_name = context.args[0]
    job_removed = remove_job_if_exists(task_name, context)
    text = 'Задание завершено!' if job_removed else 'У вас нет такой задачи'
    update.message.reply_text(text)
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""UPDATE tasks
                   SET is_finished = 1
                   WHERE name = ?""", (task_name,))
    con.commit()
    con.close()


def delete_task(update, context):  # удаляем задачу
    task_name = context.args[0]
    job_removed = remove_job_if_exists(task_name, context)
    text = 'Задание удалено!' if job_removed else 'У вас нет такой задачи'
    update.message.reply_text(text)
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""DELETE from tasks
                   WHERE name = ?""", (task_name,))
    con.commit()
    con.close()


def unfinished_tasks(update, context):  # выводим все незавершенные задачи на какую-то дату
    tz_f = pytz.timezone(context.chat_data['timezone'])
    given_date = context.args[0]
    period = given_date + ' 23:59'
    time_no_tz = datetime.datetime.strptime(period, '%d.%m.%y %H:%M')
    time_2 = time_no_tz.astimezone(tz_f)  # границы даты
    time_1 = time_2 - datetime.timedelta(days=1)
    week_day = time_no_tz.weekday()
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    # выбираем разовые задачи
    result_1 = cur.execute("""SELECT name, finish_time  
                              FROM tasks
                              WHERE is_finished = 0
                              AND strftime('%Y-%m-%d %H:%M', finish_time) 
                              BETWEEN strftime('%Y-%m-%d %H:%M', ?)
                              AND strftime('%Y-%m-%d %H:%M', ?)""", (time_1, time_2)).fetchall()
    # выбираем регулярные бесконечные ежедневные задачи
    result_2 = cur.execute("""SELECT name, do_time 
                              FROM tasks
                              WHERE is_regular = 1
                              AND is_finished = 0 
                              AND regularity = ?
                              AND is_endless = 1""", ('daily',)).fetchall()
    # выбираем регулярные бесконечные ежемесячные задачи
    result_3 = cur.execute("""SELECT name, do_time 
                              FROM tasks
                              WHERE is_regular = 1 
                              AND is_finished = 0 
                              AND regularity = ?
                              AND days LIKe ?
                              AND is_endless = 1""", ('monthly', '%' + given_date[:2] + '%')).fetchall()
    # выбираем регулярные бесконечные еженедельные задачи
    result_4 = cur.execute("""SELECT name, do_time FROM tasks
                              WHERE is_regular = 1 
                              AND regularity = ?
                              AND days LIKE ?
                              AND is_finished = 0
                              AND is_endless = 1""",
                           ('week_daily', '%' + str(week_day) + '%')).fetchall()
    # выбираем регулярные конечные ежедневные задачи (проверяя, что к тому времени они не закончатся)
    result_5 = cur.execute("""SELECT name, do_time FROM tasks
                                  WHERE is_regular = 1 
                                  AND regularity = ?
                                  AND is_finished = 0
                                  AND is_endless = 0
                                  AND strftime('%Y-%m-%d %H:%M', finish_time) 
                                  > strftime('%Y-%m-%d %H:%M', ?)""", ('daily', time_1.date())).fetchall()
    # выбираем регулярные конечные ежемесячные задачи (проверяя, что к тому времени они не закончатся)
    result_6 = cur.execute("""SELECT name, do_time FROM tasks
                                  WHERE is_regular = 1 
                                  AND regularity = ?
                                  AND days LIKE ?
                                  AND is_finished = 0
                                  AND is_endless = 0
                                  AND strftime('%Y-%m-%d %H:%M', finish_time) 
                                  > strftime('%Y-%m-%d %H:%M', ?)""", ('monthly', '%' + given_date[:2] + '%',
                                                                       time_1.date())).fetchall()
    # выбираем регулярные конечные еженедельные задачи (проверяя, что к тому времени они не закончатся)
    result_7 = cur.execute("""SELECT name, do_time FROM tasks
                                  WHERE is_regular = 1 
                                  AND regularity = ?
                                  AND days LIKE ?
                                  AND is_finished = 0
                                  AND is_endless = 0
                                  AND strftime('%Y-%m-%d %H:%M', finish_time) 
                                  > strftime('%Y-%m-%d %H:%M', ?)""",
                           ('week_daily', '%' + str(week_day) + '%')).fetchall()
    con.close()
    text = [f'Незавершённые задачи {given_date}:']
    result = result_2 + result_1 + result_3 + result_4 + result_5 + result_6 + result_7
    # сортируем в хронологическом порядке
    result.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S%z').time())
    for elem in result:  # выводим результаты поиска: название - время по часовому поясу пользователя
        time_no_tz = datetime.datetime.strptime(elem[1], '%Y-%m-%d %H:%M:%S%z')
        time = time_no_tz.astimezone(tz_f)
        text.append(f"{elem[0]} - {str(time)[11:16]}")
    update.message.reply_text('\n'.join(text))


def all_tasks(update, context):  # выводим все задачи на заданную дату
    tz_f = pytz.timezone(context.chat_data['timezone'])
    given_date = context.args[0]
    period = given_date + ' 23:59'
    time_no_tz = datetime.datetime.strptime(period, '%d.%m.%y %H:%M')
    time_2 = time_no_tz.astimezone(tz_f)
    time_1 = time_2 - datetime.timedelta(days=1)
    week_day = time_no_tz.weekday()
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    # выбираем разовые задачи
    result_1 = cur.execute("""SELECT name, finish_time FROM tasks
                              WHERE is_regular = 0
                              AND strftime('%Y-%m-%d %H:%M', finish_time) 
                              BETWEEN strftime('%Y-%m-%d %H:%M', ?)
                              AND strftime('%Y-%m-%d %H:%M', ?)""", (time_1, time_2)).fetchall()
    # выбираем регулярные бесконечные ежедневные задачи
    result_2 = cur.execute("""SELECT name, do_time 
                              FROM tasks
                              WHERE is_regular = 1
                              AND is_endless = 1 
                              AND regularity = ?""", ('daily',)).fetchall()
    # выбираем регулярные бесконечные ежемесячные задачи
    result_3 = cur.execute("""SELECT name, do_time 
                              FROM tasks
                              WHERE is_regular = 1 
                              AND is_endless = 1 
                              AND regularity = ?
                              AND days LIKe ?""", ('monthly', '%' + given_date[:2] + '%')).fetchall()
    # выбираем регулярные бесконечные еженедельные задачи
    result_4 = cur.execute("""SELECT name, do_time FROM tasks
                              WHERE is_regular = 1 
                              AND regularity = ?
                              AND days LIKE ?
                              AND is_endless = 1""",
                           ('week_daily', '%' + str(week_day) + '%')).fetchall()
    # выбираем регулярные конечные ежедневные задачи (проверяя, что к тому времени они не закончатся)
    result_5 = cur.execute("""SELECT name, do_time FROM tasks
                              WHERE is_regular = 1 
                              AND regularity = ?
                              AND is_endless = 0
                              AND strftime('%Y-%m-%d %H:%M', finish_time) 
                              > strftime('%Y-%m-%d %H:%M', ?)""", ('daily', time_1.date())).fetchall()
    # выбираем регулярные конечные ежемесячные задачи (проверяя, что к тому времени они не закончатся)
    result_6 = cur.execute("""SELECT name, do_time FROM tasks
                              WHERE is_regular = 1 
                              AND regularity = ?
                              AND days LIKE ?
                              AND is_endless = 0
                              AND strftime('%Y-%m-%d %H:%M', finish_time) 
                              > strftime('%Y-%m-%d %H:%M', ?)""", ('monthly', '%' + given_date[:2] + '%',
                                                                   time_1.date())).fetchall()
    # выбираем регулярные конечные еженедельные задачи (проверяя, что к тому времени они не закончатся)
    result_7 = cur.execute("""SELECT name, do_time FROM tasks
                              WHERE is_regular = 1 
                              AND regularity = ?
                              AND days LIKE ?
                              AND is_endless = 0
                              AND strftime('%Y-%m-%d %H:%M', finish_time) 
                              > strftime('%Y-%m-%d %H:%M', ?)""", ('week_daily', '%' + str(week_day) + '%',
                                                                   time_1.date())).fetchall()
    con.close()
    text = [f'Все задачи {given_date}:']
    result = result_2 + result_1 + result_3 + result_4 + result_5 + result_6 + result_7
    # сортируем в хронологическом порядке
    result.sort(key=lambda x: datetime.datetime.strptime(x[1], '%Y-%m-%d %H:%M:%S%z').time())
    for elem in result: # выводим результаты поиска: название - время по часовому поясу пользователя
        time_no_tz = datetime.datetime.strptime(elem[1], '%Y-%m-%d %H:%M:%S%z')
        time = time_no_tz.astimezone(tz_f)
        text.append(f"{elem[0]} - {str(time)[11:16]}")
    update.message.reply_text('\n'.join(text))


def remind(context):  # отправляет сообщение, когда подходит срок работы
    job = context.job
    context.bot.send_message(job.context, text=f'Напоминаю о задаче: {job.name}')


def main():
    updater = Updater('5349206650:AAGVXUMLqPGQboQd11817uEzOcfZtfxwA-U')
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("unfinished_tasks", unfinished_tasks))
    dp.add_handler(CommandHandler("all_tasks", all_tasks))
    dp.add_handler(CommandHandler("delete_task", delete_task))
    dp.add_handler(CommandHandler("finish_task", finish_task))
    conv_handler = ConversationHandler(

        entry_points=[CommandHandler('create_task', start_create_task)],

        states={
            1: [MessageHandler(Filters.text & ~Filters.command, get_name, pass_user_data=True)],
            2: [MessageHandler(Filters.text & ~Filters.command, get_if_regular, pass_user_data=True)],
            3: [MessageHandler(Filters.text & ~Filters.command, get_one_date, pass_user_data=True)],
            4: [MessageHandler(Filters.text & ~Filters.command, get_one_time, pass_user_data=True)],
            5: [MessageHandler(Filters.text & ~Filters.command, get_reg_regularity, pass_user_data=True)],
            6: [MessageHandler(Filters.text & ~Filters.command, get_reg_month_dates, pass_user_data=True)],
            7: [MessageHandler(Filters.text & ~Filters.command, get_week_days, pass_user_data=True)],
            8: [MessageHandler(Filters.text & ~Filters.command, get_reg_time, pass_user_data=True)],
            9: [MessageHandler(Filters.text & ~Filters.command, get_if_endless, pass_user_data=True)],
            10: [MessageHandler(Filters.text & ~Filters.command, get_reg_end_date, pass_user_data=True)],
        },

        fallbacks=[CommandHandler('stop', stop_conversation, pass_chat_data=True)]
    )

    dp.add_handler(conv_handler)
    greeting_handler = ConversationHandler(

        entry_points=[CommandHandler('start', start, pass_chat_data=True)],

        states={
            1: [MessageHandler(Filters.text & ~Filters.command, get_user_timezone, pass_chat_data=True)]
        },

        fallbacks=[CommandHandler('stop', stop_conversation, pass_chat_data=True)]
    )

    dp.add_handler(greeting_handler)
    change_tz_handler = ConversationHandler(

        entry_points=[CommandHandler('change_timezone', start_change_tz, pass_chat_data=True)],

        states={
            1: [MessageHandler(Filters.text & ~Filters.command, get_user_timezone, pass_chat_data=True)]
        },

        fallbacks=[CommandHandler('stop', stop_conversation, pass_chat_data=True)]
    )

    dp.add_handler(change_tz_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
