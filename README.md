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
/unfinished_tasks [дата]: вывести список невыполненных задач
/delete_task [имя задачи]: удалить задачу, указанную пользователем
/change_task [имя задачи]: изменить время выполнения указанной задачи

API:
Яндекс.Карты API Геокодера - вычислять координаты локации пользователя, чтобы определить часовой пояс
https://randomfox.ca/ - фотографии лисичек

Библиотеки:
APScheduler==3.6.3
backports.zoneinfo==0.2.1
cachetools==4.2.2
certifi==2021.10.8
charset-normalizer==2.0.12
geographiclib==1.52
idna==3.3
numpy==1.22.3
python-dateutil==2.8.2
python-telegram-bot==13.11
pytz==2022.1
pytz-deprecation-shim==0.1.0.post0
requests==2.27.1
six==1.16.0
timezonefinder==5.2.0
tornado==6.1
tzdata==2022.1
tzlocal==4.2
urllib3==1.26.9
