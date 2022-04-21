import logging
import sqlite3
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler, PollHandler
from telegram import ReplyKeyboardMarkup, Poll
import datetime
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

TOKEN = 'BOT_TOKEN'

DAYS_OF_WEEK = {'Понедельник': 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
                "Пятница": 4, "Суббота": 5, "Воскресенье": 6}

task_types_keyboard = [['Разовая', 'Регулярная']]
markup_1 = ReplyKeyboardMarkup(task_types_keyboard, one_time_keyboard=True)
how_regularly_keyboard = [['Каждый день', 'В определённые дни недели', 'Каждый месяц']]
markup_2 = ReplyKeyboardMarkup(how_regularly_keyboard, one_time_keyboard=True)


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


def start(update, context):
    update.message.reply_text(
        "Здравствуйте! Я ваш персональный бот для тайм-менеджмента. Я помогу вам эффективнее распоряжаться вашим временем"
        "Вот список того, что я умею:")
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS tasks(
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            type TEXT,
                            set_time TEXT,
                            do_time TEXT,
                            week_days TEXT,
                            finish_time TEXT,
                            is_finished INTEGER);""")


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def set_timer(update, context):
    chat_id = update.message.chat_id
    try:
        due = int(context.args[0])
        if due < 0:
            update.message.reply_text('Извините, не умеем возвращаться в прошлое')
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(task, due, context=chat_id, name=str(chat_id))

        text = f'Вернусь через {due} секунд!'
        if job_removed:
            text += ' Старая задача удалена.'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Использование: /set <секунд>')


def task(context):
    job = context.job
    context.bot.send_message(job.context, text='КУКУ!')


def unset(update, context):
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Таймер отменен!' if job_removed else 'У вас нет активных таймеров'
    update.message.reply_text(text)


def create_task(update, context):
    update.message.reply_text(
        "Давайте создадим новую задачу!\n"
        "Если вы передумаете, используйте команду /stop.\n"
        "Как называется задача?")
    return 1


def first_response(update, context):
    context.user_data['task_name'] = update.message.text
    update.message.reply_text(
        f"Эта задача разовая или регулярная?",
        reply_markup=markup_1)
    return 2


def second_response(update, context):
    context.user_data['task_type'] = update.message.text
    if context.user_data['task_type'] == 'Разовая':
        update.message.reply_text(
            f"Когда нужно выполнить {context.user_data['task_name']}?\n"
            f"Введите дату.")
        return 3
    else:
        update.message.reply_text(
            f"Как часто нужно выполнять {context.user_data['task_name']}?",
            reply_markup=markup_2)
    return 4


def third_response(update, context):
    context.user_data['task_finish_time'] = update.message.text
    update.message.reply_text(
        f"Во сколько нужно выполнить {context.user_data['task_name']}?\n"
        f"Введите время.")
    return 2


def fourth_response(update, context):
    context.user_data['task_do_time'] = update.message.text
    if context.user_data['task_do_time'] == 'В определённые дни недели':
        days_of_week_poll(update, context)
    if context.user_data['task_do_time'] == 'Каждый месяц':
        context.user_data['task_regularity'] = 'monthly'
        update.message.reply_text(
            f"По каким числам нужно выполнять {context.user_data['task_name']}?\n"
            f"Введите даты через пробел.")
        return 2
    else:
        context.user_data['task_regularity'] = 'daily'
    return 2


def days_of_week_poll(update, context):
    question = f"По каким дням нужно выполнять {context.user_data['task_name']}?"
    options = ['Понедельник', "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    context.bot.send_poll(chat_id=get_chat_id(update, context),
                          question=question, options=options, type=Poll.REGULAR,
                          allows_multiple_answers=True)
    days = get_answers(update)
    context.user_data['task_week_days'] = str([DAYS_OF_WEEK[x] for x in days])


def fifth_response(update, context):
    context.user_data['task_do_time'] = update.message.text
    if context.user_data['task_type'] == 'Цель':
        update.message.reply_text(
            f"До какого срока нужно выполнять {context.user_data['task_name']}?\n"
            f"Введите дату.")
        return 3
    update.message.reply_text(
        f"Какого типа эта задача {context.user_data['task_name']}?",
        reply_markup=markup_1)
    return 2


def stop(update, context):
    context.user_data['task_finish_time'] = context.user_data.get('task_finish_time') + ' ' + update.message.text
    create_task_in_db(update, context)
    update.message.reply_text("Задача создана!")
    return ConversationHandler.END


def create_task_in_db(update, context):
    task_name = context.user_data['task_name']
    task_type = context.user_data['task_type']
    task_set_time = ''
    task_do_time = datetime.datetime.strptime(context.user_data['task_do_time'], '%H:%M')
    task_is_finished = 0
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""INSERT INTO tasks(name,type,set_time,do_time,is_finished) 
                   VALUES(?,?,?,?,?)""", (task_name, task_type, task_set_time, str(task_do_time), task_is_finished))
    con.close()
    chat_id = update.message.chat_id
    context.job_queue.run_daily(remind, task_do_time, context=chat_id, name=task_name)


def finish_task(update, context):
    task_name = context.args[0]
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
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    cur.execute("""DELETE from tasks
                   WHERE name = ?""", (task_name,))
    con.close()


def unfinished_tasks(update, context):
    period = context.args[0]
    if period == 'today':
        time_2 = datetime.date.today()
        time_1 = datetime.date.today() - datetime.timedelta(days=1)
    con = sqlite3.connect("tasks_db.sqlite")
    cur = con.cursor()
    result = cur.execute("""SELECT name, do_time from tasks
                   WHERE ? < do_time < ?""", (time_1, time_2)).fetchall()
    con.close()
    for elem in result:
        update.message.reply_text(elem)


def remind(context):
    job = context.job
    context.bot.send_message(job.context, text=f'Напоминаю о задаче: {job.name}')


def main():
    updater = Updater('5128752008:AAHRm2yBZ9mZq8DTtvFBQXZe9Atd7I8R7xw')
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("unfinished_tasks", unfinished_tasks))
    dp.add_handler(CommandHandler("set", set_timer,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("unset", unset,
                                  pass_chat_data=True)
                   )
    conv_handler = ConversationHandler(
        # Точка входа в диалог.
        # В данном случае — команда /start. Она задаёт первый вопрос.
        entry_points=[CommandHandler('create_task', create_task)],

        # Состояние внутри диалога.
        # Вариант с двумя обработчиками, фильтрующими текстовые сообщения.
        states={
            # Функция читает ответ на первый вопрос и задаёт второй.
            1: [MessageHandler(Filters.text & ~Filters.command, first_response, pass_user_data=True)],
            # Функция читает ответ на второй вопрос и завершает диалог.
            2: [MessageHandler(Filters.text & ~Filters.command, second_response, pass_user_data=True)]
        },

        # Точка прерывания диалога. В данном случае — команда /stop.
        fallbacks=[CommandHandler('stop', stop)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
