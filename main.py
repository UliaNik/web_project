import logging
import sqlite3
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler
import datetime
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

TOKEN = 'BOT_TOKEN'


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
        f"Когда нужно выполнять задание {context.user_data['task_name']}?")
    return 2


def second_response(update, context):
    task_name = context.user_data['task_name']
    given_time = update.message.text
    logger.info(given_time)
    update.message.reply_text(f"Задача {task_name} создана!")
    create_task(update, context, task_name, given_time)
    return ConversationHandler.END


def stop(update, context):
    update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


def create_task1(update, context, task_name, given_time):
    task_name = 'task'
    task_type = ''
    task_set_time = ''
    task_do_time = datetime.datetime.strptime('12:26', '%H:%M')
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
