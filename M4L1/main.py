import sqlite3
    
# Создаем подключение к базе данных
connection = sqlite3.connect('films.db')

# Создание курсора для выполнения SQL-запросов
cursor = connection.cursor()

# Закрываем соединение с базой данных после использования
connection.close()