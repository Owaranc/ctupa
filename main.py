import schedule
import threading
import pickle
import sqlite3
from datetime import date
import requests
import telebot
from bs4 import BeautifulSoup
import dbworker
import markups as markup
import time

bot = telebot.TeleBot("5959138234:AAGU86PO18TFlMJPzFk6iKASOy6K3M5hJdQ")

my_dict = {"Овен": "aries",
           "Телец": "taurus",
           "Близнецы": "gemini",
           "Рак": "cancer",
           "Лев": "leo",
           "Дева": "virgo",
           "Весы": "libra",
           "Скорпион": "scorpio",
           "Стрелец": "sagittarius",
           "Козерог": "capricorn",
           "Водолей": "aquarius",
           "Рыбы": "pisces",
           }


@bot.message_handler(commands=["start"])
def cmd_start(message):
    result = dbworker.check_user_exist(message.chat.id)
    if result is True:
        msg = "Зачем всё начинать сначала? Нажмите /help чтобы увидеть список доступных команд"
        bot.send_message(message.chat.id, text=msg)
    else:
        msg = """Привет! Прежде чем мы начнем, я бы хотел, чтобы вы выбрали свой знак зодиака.\
 Нажмите на кнопку ниже, чтобы выбрать свой знак зодиака"""
        bot.send_message(message.chat.id, text=msg, reply_markup=markup.initialization())


def initialization_complete(message, horoscope):
    msg = """Добро пожаловать {}. Вы можете нажать /subscribe , чтобы подписаться на наши ежедневные уведомления о\
 гороскопе или нажать /unsubscribe , если вы больше не хотите получать уведомления.\
 Даже если вы откажетесь от подписки, вы все равно сможете использовать команды бота.\
\n\nНажмите /help , чтобы увидеть перечень команд которые знает бот."""
    bot.edit_message_text(chat_id=message.chat.id,
                          message_id=message.message_id,
                          text=msg.format(horoscope))


@bot.message_handler(commands=["help"])
def cmd_help(message):
    msg = """*Доступные команды*\n\n/today - посмотрите гороскоп на сегодняшний день.\
    \n/settings - изменить знак зодиака\n/subscribe - подписаться на ежедневные уведомления\
    \n/unsubscribe - отказаться от подписки на ежедневные уведомления"""
    bot.send_message(message.chat.id, parse_mode="Markdown", text=msg)


@bot.message_handler(commands=["today"])
def get_horoscope_by_day(message):
    try:
        horoscope = dbworker.get_horoscope(message.chat.id)
        znak = my_dict[horoscope]
        res = requests.get(
            "https://1001goroskop.ru/?znak={}".format(znak))
        soup = BeautifulSoup(res.content, 'html.parser')
        data = soup.find('div', attrs={'class': 'date'})
        ddaattaa = soup.find('div', attrs={'itemprop': 'description'})
        date = data.i.text
        todays_horoscope = ddaattaa.p.text
        bot.send_message(message.chat.id, text=date + " - " + horoscope + "\n\n" + todays_horoscope)
    except:
        bot.send_message(message.chat.id, text="К сожалению гороскоп на сегодня не доступен.")


@bot.message_handler(commands=["subscribe"])
def subscribe(message):
    result = dbworker.check_subscribers_exist(message.chat.id)
    if result is True:
        msg = "Вы уже подписаны."
        bot.send_message(message.chat.id, text=msg)
    else:
        messageobj = pickle.dumps(message, pickle.HIGHEST_PROTOCOL)
        until = date.today()
        dbworker.add_to_subscribers(message.chat.id, messageobj, until)
        bot.send_message(message.chat.id, text="Готово! Вы подписались на ежедневные уведомления.")


'''
def send_message():
    while True:
        conn = sqlite3.connect("horoscope.db")
        cursor = conn.cursor()
        cursor.execute("SELECT UserID FROM subscribers")
        users = cursor.fetchall()
        message = "ghghgh"
        for user_id in users:
            try:
                bot.send_message(user_id[0], message)
            except Exception as e:
                print("Ошибка при отправке сообщения пользователю {}: {}".format(user_id, e))
        time.sleep(86400)


def run_bot():
    bot.polling()


def run_scheduler():
    schedule_thread = threading.Thread(target=send_message)
    schedule_thread.start()
'''


@bot.message_handler(commands=["unsubscribe"])
def unsubscribe(message):
    result = dbworker.check_subscribers_exist(message.chat.id)
    if result is False:
        msg = "У вас не было подписки. Чтобы подписаться нажмите /subscribe"
        bot.send_message(message.chat.id, text=msg)
    else:
        dbworker.remove_subscriber(message.chat.id)
        bot.send_message(message.chat.id, text="Вы отписались от ежедневных уведомлений.")


@bot.message_handler(commands=["settings"])
def settings(message):
    bot.send_message(message.chat.id, text="Чем бы вы хотели заняться?", reply_markup=markup.settings_menu())


def settings_change_horoscope(message):
    bot.edit_message_text(chat_id=message.chat.id,
                          message_id=message.message_id,
                          text="Выберите свой знак зодиака",
                          reply_markup=markup.change_horoscope())


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("horoscope_"):
        horoscope = call.data.split("_")[1]
        horoscope = horoscope.split(" ")[0]
        bot.answer_callback_query(call.id, text="Добро пожаловать " + horoscope + "!", show_alert=True)
        dbworker.initialize_user(call.message.chat.id, horoscope)
        initialization_complete(call.message, horoscope)
    elif call.data == "change_horoscope":
        bot.answer_callback_query(call.id)
        settings_change_horoscope(call.message)
    elif call.data.startswith("change_"):
        bot.answer_callback_query(call.id)
        horoscope = call.data.split("_")[1]
        horoscope = horoscope.split(" ")[0]
        dbworker.change_db_horoscope(call.message.chat.id, horoscope)
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text="Изменение завершено! Нажмите /today , чтобы просмотреть свой гороскоп.",
                              reply_markup=markup.horoscope_done_troll(horoscope))
    elif call.data == "hehe":
        bot.answer_callback_query(call.id, text="hehe")


def send_message():
    while True:
        conn = sqlite3.connect("horoscope.db")
        cursor = conn.cursor()
        cursor.execute("SELECT UserID FROM subscribers")
        users = cursor.fetchall()
        message = "ghghgh"
        for user_id in users:
            try:
                bot.send_message(user_id[0], message)
            except Exception as e:
                print("Ошибка при отправке сообщения пользователю {}: {}".format(user_id, e))
        time.sleep(86400)


def run_bot():
    bot.polling()


def run_scheduler():
    schedule.every().day.at("00:00").do(send_message)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    scheduler_thread = threading.Thread(target=run_scheduler)
    bot_thread.start()
    scheduler_thread.start()
