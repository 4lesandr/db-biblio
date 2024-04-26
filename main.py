'''
Требуется:
•	Поддержка оформления нового пользователя;
•	Поддержка пополнения основных фондов;
•	Поддержка выдачи/приема/продления (не более трех продлений) книг пользователям (на определенный срок);
•	Поддержка поиска книг по автору, названию;
•	Генерация текста ругательного письма, если просрочка по возврату больше 1 месяца;
•	Поддержка отчисления пользователей, если нет долгов и активности больше 1 года;
•	Генерация штрафной квитанции, если просрочка по возврату больше 1 года (штраф – тройная цена издания; штраф считается сразу оплаченным, а книга - утерянной); 
•	Поддержка возмещения стоимости утерянной книги (1:1) по заявлению пользователя, если просрочки нет или она не более года;
•	Поддержка списания утерянных и невозвращенных книг;
Отчеты: 
•	Наиболее популярные книги (за произв. период); 
•	Наиболее популярные авторы (за произв. период);
•	Количество прочитанных книг на человека в год (по всем польз. с упорядочиванием по количеству книг).
•	Обобщенная статистика по жанровым предпочтениям за год;
•	Фин. отчет за год (основные фонды (книги) + штрафы)

база данных biblio.db уже создана и заполнена данными

пишем на ООП
'''

import sqlite3 as sql
import datetime

class Library:
    def __init__(self):
        self.conn = sql.connect('biblio.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('PRAGMA foreign_keys = ON')
        self.conn.commit()

    def __del__(self):
        self.conn.close()

    #очистка базы данных
    def clear_db(self):
        self.cursor.execute('DELETE FROM issuance')
        self.cursor.execute('DELETE FROM fill')
        self.cursor.execute('DELETE FROM book_author')
        self.cursor.execute('DELETE FROM authors')
        self.cursor.execute('DELETE FROM books')
        self.cursor.execute('DELETE FROM users')
        self.conn.commit()

    def add_user(self, name, email, status):
        #текущий максимальный id
        self.cursor.execute('SELECT MAX(user_id) FROM users')
        user_id = self.cursor.fetchone()[0]
        if user_id is None:
            user_id = 0
        user_id += 1
        self.cursor.execute('INSERT INTO users (user_id, name, email, status) VALUES (?, ?, ?, ?)', (user_id, name, email, status))
        self.conn.commit()


    def add_book(self, name, authors, genre, count, price, date):
        # Проверяем, есть ли уже книга с таким названием
        self.cursor.execute('SELECT * FROM books WHERE name = ?', (name,))
        book = self.cursor.fetchone()

        if book is not None:
            # Если книга с таким названием уже есть, проверяем авторов
            self.cursor.execute('SELECT name FROM authors WHERE author_id IN (SELECT author_id FROM book_author WHERE book_id = ?)', (book[0],))
            existing_authors = [author[0] for author in self.cursor.fetchall()]

            # Если все авторы совпадают, обновляем количество
            if set(authors.split(', ')) == set(existing_authors):
                self.cursor.execute('UPDATE books SET count = count + ? WHERE book_id = ?', (count, book[0]))
                book_id = book[0]  # сохраняем id книги для дальнейшего использования
            else:
                # Если авторы не совпадают, добавляем новую книгу
                book_id = self.add_new_book(name, genre, count, price)
                self.add_authors(authors, book_id)
        else:
            # Если книги с таким названием еще нет, добавляем новую книгу
            book_id = self.add_new_book(name, genre, count, price)
            self.add_authors(authors, book_id)

        # Записываем все добавления в таблицу fill
        self.add_fill(book_id, date, count)

        self.conn.commit()

    def add_new_book(self, name, genre, count, price):
        self.cursor.execute('SELECT MAX(book_id) FROM books')
        book_id = self.cursor.fetchone()[0]
        if book_id is None:
            book_id = 0
        book_id += 1
        self.cursor.execute('INSERT INTO books (book_id, name, price, count, genre) VALUES (?, ?, ?, ?, ?)', (book_id, name, price, count, genre))
        return book_id

    def add_authors(self, authors, book_id):
        for author in authors.split(', '):
            self.cursor.execute('SELECT author_id FROM authors WHERE name = ?', (author,))
            result = self.cursor.fetchone()
            if result is None:
                self.cursor.execute('SELECT MAX(author_id) FROM authors')
                author_id = self.cursor.fetchone()[0]
                if author_id is None:
                    author_id = 0
                author_id += 1
                self.cursor.execute('INSERT INTO authors (author_id, name) VALUES (?, ?)', (author_id, author))
            else:
                author_id = result[0]
            self.cursor.execute('INSERT INTO book_author (book_id, author_id) VALUES (?, ?)', (book_id, author_id))

    def add_fill(self, book_id, date, count):
        self.cursor.execute('SELECT MAX(fill_id) FROM fill')
        fill_id = self.cursor.fetchone()[0]
        if fill_id is None:
            fill_id = 0
        fill_id += 1
        self.cursor.execute('INSERT INTO fill (fill_id, book_id, fill_date, count) VALUES (?, ?, ?, ?)', (fill_id, book_id, date, count))

    # Остальные функции остаются без изменений

    #выдача книги пользователю таблица issuance, в таблице books уменьшаем количество книги
    def issue_book(self, user_id, book_id, date, days):
        # Проверяем, есть ли у пользователя просрочки
        self.cursor.execute('SELECT COUNT(*) FROM issuance WHERE user_id = ? AND return_date_fact > return_date_plan', (user_id,))
        overdue_books = self.cursor.fetchone()[0]
        if overdue_books > 0:
            return 'У пользователя есть просрочки'

        # Проверяем, сколько книг на руках у пользователя
        self.cursor.execute('SELECT COUNT(*) FROM issuance WHERE user_id = ? AND return_date_fact IS NULL', (user_id,))
        books_on_hand = self.cursor.fetchone()[0]
        if books_on_hand >= 3:
            return 'У пользователя уже есть 3 книги'

        # Если проблем нет, продолжаем выдачу книги
        self.cursor.execute('SELECT count FROM books WHERE book_id = ?', (book_id,))
        count = self.cursor.fetchone()[0]
        if count == 0:
            return 'Книги нет в наличии'
        self.cursor.execute('UPDATE books SET count = count - 1 WHERE book_id = ?', (book_id,))

        self.cursor.execute('SELECT MAX(operation_id) FROM issuance')
        issuance_id = self.cursor.fetchone()[0]
        if issuance_id is None:
            issuance_id = 0
        issuance_id += 1
        self.cursor.execute('INSERT INTO issuance (operation_id, user_id, book_id, issue_date, return_date_plan, return_date_fact, status) VALUES (?, ?, ?, ?, ?, ?, ?)', (issuance_id, user_id, book_id, date, date + datetime.timedelta(days), None, 0))
        self.conn.commit()
        return 'Книга выдана'
    
    def extend_book(self, user_id, book_id, days):
        self.cursor.execute('SELECT operation_id, return_date_plan, return_date_fact, status FROM issuance WHERE user_id = ? AND book_id = ?', (user_id, book_id))
        data = self.cursor.fetchone()
        if data is None:
            return 'Операция не найдена'
        operation_id, return_date_plan, return_date_fact, status = data
        # Преобразуем строку в datetime.date
        return_date_plan = datetime.datetime.strptime(return_date_plan, '%Y-%m-%d').date()
        if return_date_fact is not None:
            return_date_fact = datetime.datetime.strptime(return_date_fact, '%Y-%m-%d').date()
            if return_date_fact > return_date_plan:
                return 'Книга просрочена, продление невозможно'
        if status >= 3:
            return 'Продление невозможно, книга уже была продлена 3 раза'
        return_date_plan += datetime.timedelta(days)
        status += 1
        self.cursor.execute('UPDATE issuance SET return_date_plan = ?, status = ? WHERE operation_id = ?', (return_date_plan, status, operation_id))
        self.conn.commit()
        return 'Книга продлена. Новая дата возврата: {}. Количество продлений: {}'.format(return_date_plan, status)
    
    def return_book(self, user_id, book_id, date):
        self.cursor.execute('SELECT operation_id FROM issuance WHERE user_id = ? AND book_id = ?', (user_id, book_id))
        data = self.cursor.fetchone()
        if data is None:
            return 'Операция не найдена'
        operation_id = data[0]
        self.cursor.execute('UPDATE issuance SET return_date_fact = ?, status = 4 WHERE operation_id = ?', (date, operation_id))
        self.cursor.execute('UPDATE books SET count = count + 1 WHERE book_id = ?', (book_id,))
        self.conn.commit()
        return 'Книга возвращена'
    
    #поиск книги по автору
    def find_books_by_author(self, author):
        self.cursor.execute('SELECT name FROM books WHERE book_id IN (SELECT book_id FROM book_author WHERE author_id IN (SELECT author_id FROM authors WHERE name = ?))', (author,))
        return self.cursor.fetchall()
    
    #поиск книги по названию
    def find_books_by_name(self, name):
        self.cursor.execute('SELECT book_id, name, count, genre FROM books WHERE name = ?', (name,))
        return self.cursor.fetchall()
        
    #генерация текста ругательного письма, если просрочка по возврату больше 1 месяца
    #'отсылка' письма print
    def generate_warning(self):
        self.cursor.execute('SELECT user_id, name, email FROM users WHERE user_id IN (SELECT user_id FROM issuance WHERE return_date_fact > return_date_plan + 30)')
        users = self.cursor.fetchall()
        for user in users:
            return (f'Пользователь {user[1]} ({user[2]}) просрочил возврат книги')

    #отчисление пользователей, если нет долгов и активности больше 1 года ставим статус 0
    def exclude_users(self):
        self.cursor.execute('UPDATE users SET status = 0 WHERE user_id IN (SELECT user_id FROM issuance WHERE return_date_fact IS NOT NULL AND return_date_fact > return_date_plan + 365)')
        self.conn.commit()

    #генерация штрафной квитанции, если просрочка по возврату больше 1 года (штраф – тройная цена издания; штраф считается сразу оплаченным, а книга - утерянной)
    #'отсылка' квитанции print, вычитаем кол-во книг из таблицы books, штраф записываем в таблицу fines, ставим статус 5 в таблице issuance
    #дату берем текущую
    def generate_penalty(self):
        #проверка всех операций на просрочку
        self.cursor.execute('SELECT operation_id, user_id, book_id, issue_date FROM issuance WHERE return_date_fact IS NULL AND issue_date < date("now", "-1 year")')
        data = self.cursor.fetchall()
        for operation_id, user_id, book_id, issue_date in data:
            self.cursor.execute('SELECT price FROM books WHERE book_id = ?', (book_id,))
            price = self.cursor.fetchone()[0]
            self.cursor.execute('INSERT INTO fines (operation_id, date, size) VALUES (?, ?, ?)', (operation_id, datetime.datetime.now().date(), price*3))
            self.cursor.execute('UPDATE books SET count = count - 1 WHERE book_id = ?', (book_id,))
            self.cursor.execute('UPDATE issuance SET status = 5 WHERE operation_id = ?', (operation_id,))
            #устанавливаем дату сдачи книги текущей
            self.cursor.execute('UPDATE issuance SET return_date_fact = ? WHERE operation_id = ?', (datetime.datetime.now().date(), operation_id))
        self.conn.commit()
            
    #штраф 1:1 по заявлению пользователя, если просрочки нет или она не более года
    #штраф записываем в таблицу fines, ставим статус 5 в таблице issuance, вычитаем кол-во книг из таблицы books
    def compensate_penalty(self, user_id, book_id):
        #fines включает в себя operation_id, date, size
        self.cursor.execute('SELECT operation_id, issue_date FROM issuance WHERE user_id = ? AND book_id = ?', (user_id, book_id))
        data = self.cursor.fetchone()
        if data is None:
            return 'Операция не найдена'
        operation_id, issue_date = data
        issue_date = datetime.datetime.strptime(issue_date, '%Y-%m-%d').date()
        if datetime.datetime.now().date() - issue_date > datetime.timedelta(365):
            return 'Штраф не может быть возмещен'
        self.cursor.execute('SELECT price FROM books WHERE book_id = ?', (book_id,))
        price = self.cursor.fetchone()[0]
        self.cursor.execute('INSERT INTO fines (operation_id, date, size) VALUES (?, ?, ?)', (operation_id, datetime.datetime.now().date(), price*3))
        self.cursor.execute('UPDATE books SET count = count - 1 WHERE book_id = ?', (book_id,))
        self.cursor.execute('UPDATE issuance SET status = 5 WHERE operation_id = ?', (operation_id,))
        #устанавливаем дату сдачи книги текущей
        self.cursor.execute('UPDATE issuance SET return_date_fact = ? WHERE operation_id = ?', (datetime.datetime.now().date(), operation_id))
        self.conn.commit()


    #получение id операции по id пользователя и id книги
    def get_operation_id(self, user_id, book_id):
        self.cursor.execute('SELECT operation_id FROM issuance WHERE user_id = ? AND book_id = ?', (user_id, book_id))
        return self.cursor.fetchone()[0]
    
    #получение id пользователя по имени
    def find_user_id_by_name(self, name):
        self.cursor.execute('SELECT user_id FROM users WHERE name = ?', (name,))
        return self.cursor.fetchone()[0]
    
    '''Отчеты: 
    •	Наиболее популярные книги (за произв. период); 
    •	Наиболее популярные авторы (за произв. период);
    •	Количество прочитанных книг на человека в год (по всем польз. с упорядочиванием по количеству книг).
    •	Обобщенная статистика по жанровым предпочтениям за год;
    •	Фин. отчет за год (основные фонды (книги) + штрафы)
    '''
    #наиболее популярные книги за произвольный период
    def popular_books(self, date1, date2):
        self.cursor.execute('SELECT name, COUNT(*) FROM books WHERE book_id IN (SELECT book_id FROM issuance WHERE return_date_fact IS NOT NULL AND return_date_fact BETWEEN ? AND ?) GROUP BY name ORDER BY COUNT(*) DESC')
        return self.cursor.fetchall()
    
    #наиболее популярные авторы за произвольный период
    def popular_authors(self, date1, date2):
        self.cursor.execute('SELECT name, COUNT(*) FROM authors WHERE author_id IN (SELECT author_id FROM book_author WHERE book_id IN (SELECT book_id FROM issuance WHERE return_date_fact IS NOT NULL AND return_date_fact BETWEEN ? AND ?)) GROUP BY name ORDER BY COUNT(*) DESC')
        return self.cursor.fetchall()
    
    #количество прочитанных книг на человека в год
    def books_per_user(self):
        self.cursor.execute('SELECT name, COUNT(*) FROM users WHERE user_id IN (SELECT user_id FROM issuance) GROUP BY name ORDER BY COUNT(*) DESC')
        return self.cursor.fetchall()
    
    #статистика по жанрам за выбранный период
    def genre_statistics(self, date1, date2):
        self.cursor.execute('SELECT genre, COUNT(*) FROM books WHERE book_id IN (SELECT book_id FROM issuance WHERE return_date_fact IS NOT NULL AND return_date_fact BETWEEN ? AND ?) GROUP BY genre', (date1, date2))
        return self.cursor.fetchall()
    
    
    #финансовый отчет учитваем пополнение основных фондов (fill: fill_id, bppk_id, fill_date, count) и штрафы за период на вход 2 даты
    def financial_report(self, date1, date2):
        self.cursor.execute('SELECT SUM(price) FROM books WHERE book_id IN (SELECT book_id FROM issuance WHERE return_date_fact IS NOT NULL AND return_date_fact BETWEEN ? AND ?)', (date1, date2))
        income = self.cursor.fetchone()[0]
        self.cursor.execute('SELECT SUM(size) FROM fines WHERE date BETWEEN ? AND ?', (date1, date2))
        fines = self.cursor.fetchone()[0]
        return income, fines
    
    #получение списка пользователей
    def get_users(self):
        self.cursor.execute('SELECT * FROM users')
        return self.cursor.fetchall()
    
    #получение списка книг
    def get_books(self):
        self.cursor.execute('SELECT * FROM books')
        return self.cursor.fetchall()
    
    #получение списка операций
    def get_operations(self):
        self.cursor.execute('SELECT * FROM issuance')
        return self.cursor.fetchall()
    
    #получение списка авторов
    def get_authors(self):
        self.cursor.execute('SELECT * FROM authors')
        return self.cursor.fetchall()
    
    


import telebot
from telebot import types
'''•	Генерация текста ругательного письма, если просрочка по возврату больше 1 месяца;
•	Поддержка отчисления пользователей, если нет долгов и активности больше 1 года;
•	Генерация штрафной квитанции, если просрочка по возврату больше 1 года (штраф – тройная цена издания; штраф считается сразу оплаченным, а книга - утерянной); 
•	Поддержка возмещения стоимости утерянной книги (1:1) по заявлению пользователя, если просрочки нет или она не более года;
•	Поддержка списания утерянных и невозвращенных книг;
'''

class BiblioBot:
    def __init__(self, library):
        self.library = library
        self.bot = telebot.TeleBot("6335866021:AAGaa9U3MnSlo1CcxFBNUhjHbwKQz2DDMGo")

        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.send_welcome(message)

        @self.bot.message_handler(commands=['help'])
        def help(message):
            self.send_help(message)

        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message):
            self.handle_commands(message)

    def send_welcome(self, message):
        self.bot.send_message(message.chat.id, "Привет! Я бот для работы с библиотекой. Используй /help, чтобы увидеть список доступных команд.")

    def send_help(self, message):
        help_text = """
        Список доступных команд:
        /add_user - Добавить нового пользователя
        /add_book - Добавить новую книгу
        /issue_book - Выдать книгу пользователю
        /return_book - Вернуть книгу в библиотеку
        /extend_book - Продлить срок выдачи книги
        /find_books_by_author - Найти книги по автору
        /find_books_by_name - Найти книгу по названию
        /find_user - Найти id пользователя по имени
        /generate_warning - Сгенерировать ругательное письмо
        /exclude_users - Отчислить пользователей
        /generate_penalty - Сгенерировать штрафную квитанцию
        /compensate_penalty - Возместить штраф
        Отчеты:
        /popular_books - Наиболее популярные книги
        /popular_authors - Наиболее популярные авторы
        /books_per_user - Количество прочитанных книг на человека
        /genre_statistics - Статистика по жанрам
        /financial_report - Финансовый отчет
        """
        self.bot.send_message(message.chat.id, help_text)

    def handle_commands(self, message):
        command = message.text.lower()
        if command == '/add_user':
            self.add_user(message)
        elif command == '/add_book':
            self.add_book(message)
        elif command == '/issue_book':
            self.issue_book(message)
        elif command == '/return_book':
            self.return_book(message)
        elif command == '/extend_book':
            self.extend_book(message)
        elif command == '/find_books_by_author':
            self.find_books_by_author(message)
        elif command == '/find_books_by_name':
            self.find_books_by_name(message)
        elif command == '/find_user':
            self.get_user_id_by_name(message)
        elif command == '/generate_warning':
            self.generate_warning(message)
        elif command == '/exclude_users':
            self.exclude_users(message)
        elif command == '/generate_penalty':
            self.generate_penalty(message)
        elif command == '/compensate_penalty':
            self.compensate_penalty(message)
        elif command == '/popular_books':
            self.popular_books(message)
        elif command == '/popular_authors':
            self.popular_authors(message)
        elif command == '/books_per_user':
            self.books_per_user(message)
        elif command == '/genre_statistics':
            self.genre_statistics(message)
        elif command == '/financial_report':
            self.financial_report(message)
    
        else:
            self.bot.send_message(message.chat.id, "Команда не распознана. Используй /help для просмотра списка доступных команд.")



    def add_user(self, message):
        self.bot.send_message(message.chat.id, "Введите имя пользователя")
        self.bot.register_next_step_handler(message, self.add_user_email)

    def add_user_email(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.name = message.text
        self.bot.send_message(message.chat.id, "Введите email пользователя")
        self.bot.register_next_step_handler(message, self.add_user_status)

    def add_user_status(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.email = message.text
        self.bot.send_message(message.chat.id, "Введите статус пользователя")
        self.bot.register_next_step_handler(message, self.add_user_final)

    def add_user_final(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.status = message.text
        self.library.add_user(self.name, self.email, self.status)
        self.bot.send_message(message.chat.id, "Пользователь добавлен")

    


    def add_book(self, message):
        self.bot.send_message(message.chat.id, "Введите название книги")
        self.bot.register_next_step_handler(message, self.add_book_authors)

    def add_book_authors(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.name = message.text
        self.bot.send_message(message.chat.id, "Введите автора книги")
        self.bot.register_next_step_handler(message, self.add_book_genre)

    def add_book_genre(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.authors = message.text
        self.bot.send_message(message.chat.id, "Введите жанр книги")
        self.bot.register_next_step_handler(message, self.add_book_count)

    def add_book_count(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.genre = message.text
        self.bot.send_message(message.chat.id, "Введите количество книг")
        self.bot.register_next_step_handler(message, self.add_book_price)

    def add_book_price(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.count = int(message.text)
        self.bot.send_message(message.chat.id, "Введите цену книги")
        self.bot.register_next_step_handler(message, self.add_book_date)

    def add_book_date(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.price = int(message.text)
        self.date = datetime.datetime.now().date()
        self.library.add_book(self.name, self.authors, self.genre, self.count, self.price, self.date)
        self.bot.send_message(message.chat.id, "Книга добавлена")



    def issue_book(self, message):
        self.bot.send_message(message.chat.id, "Введите id пользователя")
        self.bot.register_next_step_handler(message, self.issue_book_book_id)

    def issue_book_book_id(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.user_id = int(message.text)
        self.bot.send_message(message.chat.id, "Введите id книги")
        self.bot.register_next_step_handler(message, self.issue_book_date)

    def issue_book_date(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.book_id = int(message.text)
        self.date = datetime.datetime.now().date()
        self.bot.send_message(message.chat.id, "Введите количество дней на выдачу")
        self.bot.register_next_step_handler(message, self.issue_book_final)

    def issue_book_final(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.days = int(message.text)
        result = self.library.issue_book(self.user_id, self.book_id, self.date, self.days)
        self.bot.send_message(message.chat.id, result)



    def return_book(self, message):
        self.bot.send_message(message.chat.id, "Введите id пользователя")
        self.bot.register_next_step_handler(message, self.return_book_book_id)

    def return_book_book_id(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.user_id = int(message.text)
        self.bot.send_message(message.chat.id, "Введите id книги")
        self.bot.register_next_step_handler(message, self.return_book_date)

    def return_book_date(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.book_id = int(message.text)
        self.date = datetime.datetime.now().date()
        result = self.library.return_book(self.user_id, self.book_id, self.date)
        self.bot.send_message(message.chat.id, result)


    def extend_book(self, message):
        self.bot.send_message(message.chat.id, "Введите id пользователя")
        self.bot.register_next_step_handler(message, self.extend_book_book_id)

    def extend_book_book_id(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.user_id = int(message.text)
        self.bot.send_message(message.chat.id, "Введите id книги")
        self.bot.register_next_step_handler(message, self.extend_book_days)

    def extend_book_days(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.book_id = int(message.text)
        self.bot.send_message(message.chat.id, "Введите количество дней на продление")
        self.bot.register_next_step_handler(message, self.extend_book_final)

    def extend_book_final(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.days = int(message.text)
        result = self.library.extend_book(self.user_id, self.book_id, self.days)
        self.bot.send_message(message.chat.id, result)

    
    
    def find_books_by_author(self, message):
        self.bot.send_message(message.chat.id, "Введите автора")
        self.bot.register_next_step_handler(message, self.find_books_by_author_final)

    def find_books_by_author_final(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        author = message.text
        books = self.library.find_books_by_author(author)
        if books:
            for book in books:
                self.bot.send_message(message.chat.id, book[0])
        else:
            self.bot.send_message(message.chat.id, "Книг не найдено")

    
    #возвращает список книг и их количество по названию
    def find_books_by_name(self, message):
        self.bot.send_message(message.chat.id, "Введите название книги")
        self.bot.register_next_step_handler(message, self.find_books_by_name_final)

    def find_books_by_name_final(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        name = message.text
        books = self.library.find_books_by_name(name)
        if books:
            for book in books:
                self.bot.send_message(message.chat.id, f"ID: {book[0]}, Название: {book[1]}, Количество: {book[2]}, Жанр: {book[3]}")
        else:
            self.bot.send_message(message.chat.id, "Книг не найдено")


        

    
    def generate_warning(self, message):
        warning = self.library.generate_warning()
        self.bot.send_message(message.chat.id, warning)

    def exclude_users(self, message):
        self.library.exclude_users()
        self.bot.send_message(message.chat.id, "Пользователи отчислены")

    def generate_penalty(self, message):
        self.library.generate_penalty()
        self.bot.send_message(message.chat.id, "Штрафы выставлены")

    def compensate_penalty(self, message):
        self.bot.send_message(message.chat.id, "Введите id пользователя")
        self.bot.register_next_step_handler(message, self.compensate_penalty_book_id)

    def compensate_penalty_book_id(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        self.user_id = int(message.text)
        self.bot.send_message(message.chat.id, "Введите id книги")
        self.bot.register_next_step_handler(message, self.compensate_penalty_final)

    def compensate_penalty_final(self, message):
        if '/' in message.text:
            self.bot.send_message(message.chat.id, "Ошибка: сообщение не должно содержать символ '/'")
            return
        book_id = int(message.text)
        self.library.compensate_penalty(self.user_id, book_id)
        self.bot.send_message(message.chat.id, "Штраф возмещен")

    def get_user_id_by_name(self, message):
        self.bot.send_message(message.chat.id, "Введите имя пользователя")
        self.bot.register_next_step_handler(message, self.get_user_id_by_name_final)

    def get_user_id_by_name_final(self, message):
        user_id = self.library.find_user_id_by_name(message.text)
        self.bot.send_message(message.chat.id, f"ID пользователя: {user_id}")

    def popular_books(self, message):
        books = self.library.popular_books()
        for book in books:
            self.bot.send_message(message.chat.id, f"Название: {book[0]}, Количество: {book[1]}")

    def popular_authors(self, message):
        authors = self.library.popular_authors()
        for author in authors:
            self.bot.send_message(message.chat.id, f"Автор: {author[0]}, Количество: {author[1]}")

    def books_per_user(self, message):
        users = self.library.books_per_user()
        for user in users:
            self.bot.send_message(message.chat.id, f"Пользователь: {user[0]}, Количество: {user[1]}")

    def genre_statistics(self, message):
        genres = self.library.genre_statistics()
        for genre in genres:
            self.bot.send_message(message.chat.id, f"Жанр: {genre[0]}, Количество: {genre[1]}")

    def financial_report(self, message):
        income, fines = self.library.financial_report()
        self.bot.send_message(message.chat.id, f"Доход: {income}, Штрафы: {fines}")

    
    def run(self):
        self.bot.polling()


def main():
    library = Library()
    bot = BiblioBot(library)
    bot.run()


if __name__ == '__main__':
    main()

