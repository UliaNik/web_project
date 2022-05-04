Телеграм-бот [название]
Бот, который помогает с тайм-менеджментом. 

Задачи хранятся в базе данных sqlite. 
Параметры задачи: id INTEGER PRIMARY KEY,
                  name TEXT,
                  is_regular INTEGER,
                  is_endless INTEGER,
                  regularity TEXT,
                  set_time TEXT,
                  do_time TEXT,
                  days TEXT,
                  finish_time TEXT,
                  is_finished INTEGER

Список команд:
/start: приветствие, описание, список функций
/create_task: создать задачу, пользователь указывает название, тип, срок выполнения, частоту выполнения
/finish_task [имя задачи]: завершить задачу
/all_tasks [дата]: вывести список задач на заданный день (задача - статус выполнения)
/unfinished_tasks[дата]: вывести список невыполненных задач
/delete_task [имя задачи]: удалить задачу, указанную пользователем
/change_task [имя задачи]: изменить время выполнения указанной задачи

API:
Яндекс.Карты API Геокодера - вычислять координаты локации пользователя, чтобы определить часовой пояс
https://randomfox.ca/ - фотографии лисичек

Библиотеки:
