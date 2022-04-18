Телеграм-бот [название]
Бот, который помогает с тайм-менеджментом. 

Задачи хранятся в базе данных sqlite. 
Параметры задачи: id - name - type - set_time - do_time - is_finished

Типы задач:
Дело. Разовая задача. Пример: позвонить другу.
Привычка. Регулярная задача без цели, относящаяся к распорядку дня. Пример: почистить зубы.
Цель. Разовая задача, которая требует регулярных действий. Пример: подготовиться к олимпиаде.


Список команд:
/start: приветствие, описание, список функций
/create_task: создать задачу, пользователь указывает название, тип, срок выполнения, частоту выполнения
/finish_task [имя задачи]: завершить задачу
/see_all_tasks [сегодня/вчера/завтра/дата]: вывести список задач на заданный день (задача - статус выполнения)
/unfinished_tasks: вывести список невыполненных задач
/delete_task [имя задачи]: удалить задачу, указанную пользователем
/change_task [имя задачи]: изменить время выполнения указанной задачи
/compare: получить от пользователя список дел, попарно выдать дела для сравнения по важности, построить и выдать в итоге список дел по важности

API:
портал открытых данных минкультуры россии -> культурные мероприятия
погода -> предупреждение для метеозависимых пользователей (меня) о необходимости уменьшить количество задач?
картинки котов?
цитаты?

Также:
спрашивать пользователя, через какой промежуток чистить базу данных?
сделать меню? как?
what can this bot do