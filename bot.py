#телеграм бот для работы библиотекаря в библиотеке
import telebot
from telebot import types
import main
#этот файл будет подключаться в другом файле
#поэтому нам нужно создать объект бота
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

в файле для работы с базой данных имеются функции:
__init__(self)
__del__(self)
clear_db(self)
add_user(self, name, email, status)
add_book(self, name, authors, genre, count, price, date)
add_new_book(self, name, genre, count, price)
add_authors(self, authors, book_id)
add_fill(self, book_id, date, count)
issue_book(self, user_id, book_id, date, days)
extend_book(self, operation_id, days)
return_book(self, operation_id, date)
find_books_by_author(self, author)
find_books_by_name(self, name)
generate_warning(self)
exclude_users(self)
generate_penalty(self)
compensate_penalty(self, user_id, book_id)
get_operation_id(self, user_id, book_id)

нам нужно написать только функции для работы с телеграмм ботом

'''

class Bot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.db = Database()
        self.users = {}
        self.books = {}
        self.authors = {}
        self.fill = {}
        self.operations = {}
        self.users = self.db.get_users()
        self.books = self.db.get_books()
        self.authors = self.db.get_authors()
        self.fill = self.db.get_fill()
        self.operations = self.db.get_operations()
        self.bot.polling()

    def __del__(self):
        self.db.close()

    def main(self):
        @self.bot.message_handler(commands=['start'])
        def start_message(message):
            self.bot.send_message(message.chat.id, 'Привет! Я бот библиотекаря. Чтобы узнать, что я могу, введите /help')

        @self.bot.message_handler(commands=['help'])
        def help_message(message):
            self.bot.send_message(message.chat.id, 'Я могу:\n'
                                                   '/add_user - добавить пользователя\n'
                                                   '/add_book - добавить книгу\n'
                                                   '/issue_book - выдать книгу\n'
                                                   '/extend_book - продлить книгу\n'
                                                   '/return_book - вернуть книгу\n'
                                                   '/find_books_by_author - найти книги по автору\n'
                                                   '/find_books_by_name - найти книги по названию\n'
                                                   '/generate_warning - сгенерировать предупреждение\n'
                                                   '/exclude_users - исключить пользователей\n'
                                                   '/generate_penalty - сгенерировать штраф\n'
                                                   '/compensate_penalty - возместить штраф\n'
                                                   '/get_operation_id - получить id операции\n')

        @self.bot.message_handler(commands=['add_user'])
        def add_user(message):
            self.bot.send_message(message.chat.id, 'Введите имя пользователя')
            self.bot.register_next_step_handler(message, add_user_name)

        def add_user_name(message):
            name = message.text
            self.bot.send_message(message.chat.id, 'Введите email пользователя')
            self.bot.register_next_step_handler(message, add_user_email)

        def add_user_email(message):
            email = message.text

            keyboard = types.InlineKeyboardMarkup()
            key_yes = types.InlineKeyboardButton(text='Студент', callback_data='student')
            keyboard.add(key_yes)
            key_no = types.InlineKeyboardButton(text='Преподаватель', callback_data='teacher')
            keyboard.add(key_no)
            self.bot.send_message(message.chat.id, 'Выберите статус пользователя', reply_markup=keyboard)
