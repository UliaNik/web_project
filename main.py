import logging
import sqlite3
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler, PollAnswerHandler
from telegram import ReplyKeyboardMarkup, Poll
from dateutil.parser import *
from dateutil.tz import *
from datetime import *
import datetime
from dateutil.tz import gettz
from dateutil import parser
import requests
from timezonefinder import TimezoneFinder
import pytz
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

TOKEN = 'BOT_TOKEN'
DEFAULT = datetime.datetime(2003, 9, 25)
DAYS_OF_WEEK = {'Понедельник': 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
                "Пятница": 4, "Суббота": 5, "Воскресенье": 6}

task_types_keyboard = [['Разовая', 'Регулярная']]
markup_1 = ReplyKeyboardMarkup(task_types_keyboard, one_time_keyboard=True)
how_regularly_keyboard = [['Каждый день', 'В определённые дни недели', 'Каждый месяц']]
markup_2 = ReplyKeyboardMarkup(how_regularly_keyboard, one_time_keyboard=True)
task_types_2_keyboard = [['Конечная', 'Бесконечная']]
markup_3 = ReplyKeyboardMarkup(task_types_2_keyboard, one_time_keyboard=True)


def get_chat_id(update, context):
    chat_id = -1
    if update.message is not None:
        chat_id = update.message.chat.id
    elif update.callback_query is not None:
        chat_id = update.callback_query.message.chat.id
    elif update.poll is not None:
        chat_id = context.bot_data[update.poll.id]
    return chat_id


def get_answers(update):
    options = update.poll.options
    answers = []
    for option in options:
        if option.voter_count == 1:
            answers.append(option.text)
    return answers


def get_user_timezone(update, context):
    city = update.message.text
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&" \
                       f"geocode={city}&format=json"
    response = requests.get(geocoder_request)
    if response:
        json_response = response.json()
        toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        toponym_address = toponym["metaDataProperty"]["GeocoderMetaData"]["text"]
        ll = toponym["Point"]["pos"]
        tf = TimezoneFinder()
        tz = tf.timezone_at(lng=float(ll[0]), lat=float(ll[1]))
        context.chat_data['timezone'] = tz
        update.message.reply_text(
            "Спасибо! Часовой пояс определён.")
        return ConversationHandler.END
    update.message.reply_text(
        "Город с таким названием не найден. "
        "Проверьте, нет ли в названии опечаток, или выберите другой, близлежащий, город.")
    return 1


def start(update, context):
    update.message.reply_text(
        "Здравствуйте! Я ваш персональный бот для тайм-менеджмента. Я помогу вам эффективнее распоряжаться вашим временем"
        "Вот список того, что я умею:")
    con = sqlite3.connect("tasks_db.sqlite")
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
    if not context.chat_data.get('timezone', 0):
        update.message.reply_text(
            "Чтобы правильно работать, мне необходимо знать Ваш часовой пояс. В каком городе вы находитесь?")
        return 1
    return ConversationHandler.END


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def start_create_task(update, context):
    update.message.reply_text(
        "Давайте создадим новую задачу!\n"
        "Если вы передумаете, используйте команду /stop.\n"
        "Как называется задача?")
    return 1


def stop_create_task(update, context):
    update.message.reply_text(
        "Задача удалена")
    return ConversationHandler.END


def get_name(update, context):
    context.user_data['task_name'] = update.message.text
    update.message.reply_text(
        f"Эта задача разовая или регулярная?",
        reply_markup=markup_1)
    return 2


def get_if_regular(update, context):
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


def get_one_date(update, context):
    context.user_data['task_finish_time'] = update.message.text
    update.message.reply_text(
        f"Во сколько нужно выполнить {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 4


def get_one_time(update, context):
    context.user_data['task_finish_time'] = context.user_data.get('task_finish_time') + ' ' + update.message.text
    create_task_in_db(update, context)
    update.message.reply_text("Задача создана!")
    return ConversationHandler.END


def get_reg_regularity(update, context):
    context.user_data['task_do_time'] = update.message.text
    if context.user_data['task_do_time'] == 'Каждый месяц':
        context.user_data['task_regularity'] = 'monthly'
        update.message.reply_text(
            f"По каким числам нужно выполнять {context.user_data['task_name']}?\n"
            f"Введите даты через пробел.")
        return 6
    if context.user_data['task_do_time'] == 'В определённые дни недели':
        days_of_week_poll(update, context)
        context.user_data['task_regularity'] = 'week_daily'
    else:
        context.user_data['task_regularity'] = 'daily'
    update.message.reply_text(
        f"Во сколько нужно выполнять {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 7


def days_of_week_poll(update, context):
    question = f"По каким дням нужно выполнять {context.user_data['task_name']}?"
    options = ['Понедельник', "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    message = context.bot.send_poll(chat_id=get_chat_id(update, context),
                                    question=question, options=options, type=Poll.REGULAR,
                                    allows_multiple_answers=True)

    payload = {
        message.poll.id: {
            "questions": options,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)


def receive_poll_answer(update, context):
    answer = update.poll_answer
    poll_id = answer.poll_id
    questions = context.bot_data[poll_id]["questions"]
    selected_options = answer.option_ids
    days = []
    for question_id in selected_options:
        days.append(questions[question_id])
    context.user_data['task_days'] = str([DAYS_OF_WEEK[x] for x in days])


def get_reg_month_dates(update, context):
    context.user_data['task_days'] = update.message.text
    update.message.reply_text(
        f"Во сколько нужно выполнять {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 7


def get_reg_time(update, context):
    if context.user_data['task_do_time'] == 'Каждый месяц':
        context.user_data['task_do_time'] = context.user_data.get('task_do_time') + ' ' + update.message.text
    else:
        context.user_data['task_do_time'] = update.message.text
    update.message.reply_text(
        f"Эта задача конечная или бесконечная?", reply_markup=markup_3)
    return 8


def get_if_endless(update, context):
    context.user_data['task_is_endless'] = update.message.text
    if context.user_data['task_is_endless'] == 'Конечная':
        update.message.reply_text(
            f"Когда нужно перестать выполнять {context.user_data['task_name']}?\n"
            f"Введите дату.")
        return 9
    else:
        create_task_in_db(update, context)
        update.message.reply_text("Задача создана!")
        return ConversationHandler.END


def get_reg_end_date(update, context):
    context.user_data['task_finish_time'] = update.message.text
    create_task_in_db(update, context)
    update.message.reply_text("Задача создана!")
    return ConversationHandler.END


def create_task_in_db(update, context):
    task_name = context.user_data['task_name']
    task_is_regular = 1 if context.user_data['task_is_regular'] == 'Регулярная' else 0
    task_is_endless = 1 if context.user_data.get('task_is_endless', '') == 'Бесконечная' else 0
    task_set_time = datetime.datetime.now(gettz(context.chat_data['timezone']))
    tz_f = pytz.timezone(context.chat_data['timezone'])
    task_regularity = context.user_data.get('task_regularity', '')
    task_days = context.user_data.get('task_days', '')
    if task_is_regular:
        do_time_no_tz = datetime.datetime.strptime(str(datetime.date.today()) + " " + context.user_data['task_do_time'],
                                                   '%Y-%m-%d %H:%M')
        do_time_full_date = do_time_no_tz.astimezone(tz_f)
        task_do_time = datetime.datetime.strptime(str(do_time_full_date)[11:16], '%H:%M')
    else:
        task_do_time = ''
    if not task_is_endless:
        finish_time_no_tz = datetime.datetime.strptime(context.user_data['task_finish_time'], '%d.%m.%y %H:%M')
        task_finish_time = finish_time_no_tz.astimezone(tz_f)
    else:
        task_finish_time = ''
    task_is_finished = 0
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    res = cur.execute("""SELECT * from tasks
                         WHERE name = ? AND is_finished = 0""", (task_name,)).fetchall()
    if res:
        update.message.reply_text("Задача с таким названием уже существует!")
        con.close()
    else:
        cur.execute("""INSERT INTO tasks(name,is_regular,is_endless,regularity,
                       set_time,do_time,days,finish_time,is_finished) 
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (task_name, task_is_regular, task_is_endless, task_regularity,
                     str(task_set_time), str(task_do_time), task_days, str(task_finish_time),
                     task_is_finished))
        con.close()
        chat_id = update.message.chat_id
        if task_is_regular:
            if task_regularity == 'monthly':
                dates = [int(x) for x in task_days.split()]
                for date in dates:
                    context.job_queue.run_monthly(remind, task_do_time, day=date, context=chat_id, name=task_name)
            elif task_regularity == 'week_daily':
                week_days = tuple(int(x) for x in task_days)
                context.job_queue.run_daily(remind, task_do_time, days=week_days, context=chat_id, name=task_name)
            else:
                context.job_queue.run_daily(remind, task_do_time, context=chat_id, name=task_name)
        else:
            context.job_queue.run_once(remind, task_finish_time, context=chat_id, name=task_name)


def finish_task(update, context):  # нужно ли?
    task_name = context.args[0]
    job_removed = remove_job_if_exists(task_name, context)
    text = 'Задание завершено!' if job_removed else 'У вас нет такой задачи'
    update.message.reply_text(text)
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""UPDATE tasks
                   SET is_finished = 1
                   WHERE name = ?""", (task_name,))
    con.close()


def change_task(update, context):
    task_name = context.args[0]
    task_do_time = ''
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""UPDATE tasks
                   SET do_time = ?
                   WHERE name = ?""", (task_do_time, task_name))
    con.close()


def delete_task(update, context):
    task_name = context.args[0]
    job_removed = remove_job_if_exists(task_name, context)
    text = 'Задание удалено!' if job_removed else 'У вас нет такой задачи'
    update.message.reply_text(text)
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""DELETE from tasks
                   WHERE name = ?""", (task_name,))
    con.close()


def unfinished_tasks(update, context):
    period = context.args[0] + ' 23:59'
    time_1 = datetime.date.today() - datetime.timedelta(days=1)
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    result = cur.execute("""SELECT name, finish_time from tasks
                            WHERE datetime.datetime.strftime('%d.%m.%y %H:%M', finish_time) 
                            BETWEEN datetime.datetime.strftime('%d.%m.%y %H:%M', ?)
                            AND datetime.datetime.strftime('%d.%m.%y %H:%M', ?)""", (time_1, period)).fetchall()
    con.close()  # возникнет ошибка для регулярных бесконечных задач?
    for elem in result:
        update.message.reply_text(elem)


def remind(context):
    job = context.job
    context.bot.send_message(job.context, text=f'Напоминаю о задаче: {job.name}')


def main():
    updater = Updater('5128752008:AAHRm2yBZ9mZq8DTtvFBQXZe9Atd7I8R7xw')
    dp = updater.dispatcher
    # dp.add_handler(CommandHandler("start", start, pass_chat_data=True))
    dp.add_handler(CommandHandler("unfinished_tasks", unfinished_tasks))
    dp.add_handler(PollAnswerHandler(receive_poll_answer))
    conv_handler = ConversationHandler(

        entry_points=[CommandHandler('create_task', start_create_task)],

        states={
            1: [MessageHandler(Filters.text & ~Filters.command, get_name, pass_user_data=True)],
            2: [MessageHandler(Filters.text & ~Filters.command, get_if_regular, pass_user_data=True)],
            3: [MessageHandler(Filters.text & ~Filters.command, get_one_date, pass_user_data=True)],
            4: [MessageHandler(Filters.text & ~Filters.command, get_one_time, pass_user_data=True)],
            5: [MessageHandler(Filters.text & ~Filters.command, get_reg_regularity, pass_user_data=True)],
            6: [MessageHandler(Filters.text & ~Filters.command, get_reg_month_dates, pass_user_data=True)],
            7: [MessageHandler(Filters.text & ~Filters.command, get_reg_time, pass_user_data=True)],
            8: [MessageHandler(Filters.text & ~Filters.command, get_if_endless, pass_user_data=True)],
            9: [MessageHandler(Filters.text & ~Filters.command, get_reg_end_date, pass_user_data=True)],
        },

        fallbacks=[CommandHandler('stop', stop_create_task, pass_chat_data=True)]
    )

    dp.add_handler(conv_handler)
    greeting_handler = ConversationHandler(

        entry_points=[CommandHandler('start', start, pass_chat_data=True)],

        states={
            1: [MessageHandler(Filters.text & ~Filters.command, get_user_timezone, pass_chat_data=True)]
        },

        fallbacks=[CommandHandler('stop', stop_create_task, pass_chat_data=True)]
    )

    dp.add_handler(greeting_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()