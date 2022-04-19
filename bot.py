from time import sleep
import telebot
import folium
import storage
import datetime
import logging
import os
import cherrypy
import pandas
import requests
from flask import Flask, request
from flask_sslify import SSLify


TOKEN = "5219218963:AAFRuxk0G7RrYGAq6su7M5beww1RHl6KokY"
APP_NAME = "catchstickbot"

API_TOKEN = '5219218963:AAFRuxk0G7RrYGAq6su7M5beww1RHl6KokY'

WEBHOOK_HOST = '217.25.89.150'
WEBHOOK_PORT = 8443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Path to the ssl private key

# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (API_TOKEN)

open("logs.txt", "w").write("")

logging.basicConfig(filename="logs.txt", level=logging.INFO)

bot = telebot.TeleBot(TOKEN)

class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if 'content-length' in cherrypy.request.headers and \
           'content-type' in cherrypy.request.headers and \
           cherrypy.request.headers['content-type'] == 'application/json':
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)


already_clicked = False

def update_map():
    mapp = folium.Map(location=[54.859989, 82.972914], zoom_start=1)
    for sig in storage.get_all_sigs():
        folium.Marker(location=[float(sig["latitude"]), float(sig["longitude"])], popup="Stick: {}\nStatus: {}".format(
            str(sig['num']), str(sig["status"])), icon=folium.Icon(color='gray')).add_to(mapp)
    mapp.save("map.html")


@bot.message_handler(commands=["quit"])
def quit(message):
    start(message)


@bot.message_handler(commands=["getlogs"])
def getlogs(message):
    if str(message.from_user.id) == "732877680":
        f = open("logs.txt")
        bot.send_message(message.from_user.id, "Логи:",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_document(message.from_user.id, f)
        f.close()

@bot.message_handler(commands=["clearlogs"])
def getlogs(message):
    if str(message.from_user.id) == "732877680":
        with open("logs.log", "w") as f:
            f.write("")
        bot.reply_to(message, "Cleared logs")

@bot.message_handler(commands=["my_sigs"])
def gms(message):
    my_sigs = storage.get_all_sigs_byid(message.from_user.id)
    fin_mes = "Номер: {}\nФИО: {}\nДата {}\nМестоположение:\nlongitude {},\nlatitude {}\nСтатус: {}"
    for sig in my_sigs:
        bot.send_message(message.from_user.id, fin_mes.format(
            sig['num'], sig['fio'], sig['time'], sig['longitude'], sig["latitude"], sig["status"]))
    update_map()
    f = open("map.html")
    bot.send_message(message.from_user.id, "Карта заявок:",
                     reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.send_document(message.from_user.id, f)
    f.close()


@bot.message_handler(commands=["start"])
def start(message):
    hello_message = '''
    Привет! Я помогу тебе зарегестрировать твою находку!\nПомни: на каждую находку отдельный сигнал ;)
    '''
    bot.send_message(message.from_user.id, hello_message,
                     reply_markup=telebot.types.ReplyKeyboardRemove())
    ask_message = '''
    Выбери действие
    '''
    keyboard = [
        [
            telebot.types.InlineKeyboardButton(
                "Зарегестрировать", callback_data='reg_find'),
            telebot.types.InlineKeyboardButton(
                "Мои заявки+карта", callback_data='my_sigs'),
        ]
    ]
    reply_markup = telebot.types.InlineKeyboardMarkup(keyboard)
    bot.send_message(message.from_user.id, ask_message,
                     reply_markup=reply_markup)


@bot.callback_query_handler(func=lambda c: c.data == 'reg_find')
def find_reg(callback_query):
    global already_clicked
    if already_clicked:
        bot.answer_callback_query(callback_query.id)
        return
    already_clicked = True
    bot.answer_callback_query(callback_query.id)
    message = bot.send_message(callback_query.from_user.id, 'Введите свое ФИО',
                               reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, ask_geo)


def ask_geo(message):
    fio = message.text
    ask_pos_mes = '''
    Нажимая кнопку под этим сообщением я даю свое согласие на обработку моих персональных данных и отправляю боту свое местоположение.\n\n
P.S не забудь включить доступ к местоположению на телефоне
    '''
    keyboard = telebot.types.ReplyKeyboardMarkup()
    button_1 = telebot.types.KeyboardButton(
        "Отправить геоданные", request_location=True)
    keyboard.add(button_1)

    bot.send_message(message.from_user.id, ask_pos_mes, reply_markup=keyboard)
    bot.register_next_step_handler(message, fin_reg, fio)


def fin_reg(message, fio):
    global already_clicked
    new_num = len(storage.get_all_sigs())+1
    now_time = datetime.datetime.now()
    storage.new_sig(message.from_user.id, new_num, fio,
                    now_time, str(message.location.longitude), str(message.location.latitude))

    logging.info("----------------\n""New sig by {} ({}): ".format(str(message.from_user.id), message.from_user.username)+"Номер: {}\nФИО: {}\nДата {}\nМестоположение:\nlongitude {},\nlatitude {}\nСтатус: {}".format(
        str(new_num), fio, now_time, str(message.location.longitude), str(message.location.latitude), "registered")+"\n----------------")

    fin_mes = "Номер: {}\nФИО: {}\nДата {}\nМестоположение:\nlongitude {},\nlatitude {}\nСтатус: {}".format(
        str(new_num), fio, now_time, str(message.location.longitude), str(message.location.latitude), "registered")
    bot.send_message(message.from_user.id, "Регистрация завершена. Ваша заявка:\n\n" +
                     fin_mes, reply_markup=telebot.types.ReplyKeyboardRemove())
    update_map()
    f = open("map.html")
    bot.send_message(message.from_user.id, "Карта заявок:")
    bot.send_document(message.from_user.id, f)
    f.close()
    already_clicked = False

@bot.callback_query_handler(func=lambda c: c.data == 'my_sigs')
def get_my_sigs(callback_query):
    bot.answer_callback_query(callback_query.id)
    my_sigs = storage.get_all_sigs_byid(callback_query.from_user.id)
    fin_mes = "Номер: {}\nФИО: {}\nДата {}\nМестоположение:\nlongitude {},\nlatitude {}\nСтатус: {}"
    for sig in my_sigs:
        bot.send_message(callback_query.from_user.id, fin_mes.format(
            sig['num'], sig['fio'], sig['time'], sig['longitude'], sig["latitude"], sig["status"]))
    update_map()
    f = open("map.html")
    bot.send_message(callback_query.from_user.id, "Карта заявок:",
                     reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.send_document(callback_query.from_user.id, f)
    f.close()


@bot.message_handler(commands=["org"])
def ask_password_org(message):
    bot.reply_to(message, "Введите пароль или /quit для выхода",
                 reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, org_panel)


def org_panel(message, not_entering=False):
    if message.text == "/quit":
        start(message)
    elif message.text != "orgpass" and (not not_entering):
        bot.reply_to(message, "Неверный пароль")
        ask_password_org(message)
    else:
        if not not_entering:
            logging.info("----------------\n"+"Entered orgpanel by {} ({})".format(
                str(message.from_user.id), message.from_user.username)+"\n----------------")

        ask_message = '''
        Выберите действие. Для выхода введите /quit
        '''
        keyboard = [
            [
                telebot.types.InlineKeyboardButton(
                    "Сменить статус находки", callback_data='change_status'),
            ]
        ]
        reply_markup = telebot.types.InlineKeyboardMarkup(keyboard)
        bot.send_message(message.from_user.id, ask_message,
                         reply_markup=reply_markup)


@bot.callback_query_handler(func=lambda c: c.data == 'change_status')
def change_stat(callback_query):
    bot.answer_callback_query(callback_query.id)
    message = bot.send_message(callback_query.from_user.id, "Введите номер находки",
                               reply_markup=telebot.types.ReplyKeyboardRemove())

    def choose_stat(message):
        sig = storage.get_sig(message.text)
        if sig is None:
            bot.reply_to(message, "Такой заявки нет",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
            org_panel(message, True)
        else:
            keyboard = telebot.types.ReplyKeyboardMarkup()
            button_1 = telebot.types.KeyboardButton(
                "accepted")
            keyboard.add(button_1)
            button_2 = telebot.types.KeyboardButton(
                "sent for testing")
            keyboard.add(button_2)
            bot.reply_to(message, "Выберите статус", reply_markup=keyboard)

            def fin_change_stat(message, num, sig):
                storage.change_status(num, message.text)
                logging.info("Change status by {} ({}): ".format(str(message.from_user.id), message.from_user.username)+"Номер: {}\nФИО: {}\nДата {}\nМестоположение:\nlongitude {},\nlatitude {}\nСтатус: {}".format(
                    sig['num'], sig['fio'], sig['time'], sig['longitude'], sig['latitude'], sig['status'])+" -> {}\n----------------".format(message.text))
                bot.reply_to(message, 'Статус изменен',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
                org_panel(message, True)

            bot.register_next_step_handler(
                message, fin_change_stat, message.text, sig)

    bot.register_next_step_handler(message, choose_stat)


@bot.message_handler(commands=["admin"])
def ask_password_admin(message):
    bot.reply_to(message, "Введите пароль или /quit для выхода",
                 reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, admin_panel)


def admin_panel(message, not_entering=False):
    if message.text == "/quit":
        start(message)
    elif message.text != "adminpass" and not not_entering:
        bot.reply_to(message, "Неверный пароль")
        ask_password_admin(message)
    else:
        if not not_entering:
            logging.info("----------------\n"+"Entered adminpanel by {} ({})".format(
                str(message.from_user.id), message.from_user.username)+"\n----------------")
        ask_message = '''
        Выберите действие. Для выхода введите /quit
        '''
        keyboard = [
            [
                telebot.types.InlineKeyboardButton(
                    "Сменить статус находки", callback_data='change_status_admin'),
                telebot.types.InlineKeyboardButton(
                    "Получить базу данных", callback_data='get_storage')
            ]
        ]
        reply_markup = telebot.types.InlineKeyboardMarkup(keyboard)
        bot.send_message(message.from_user.id, ask_message,
                         reply_markup=reply_markup)


@bot.callback_query_handler(func=lambda c: c.data == 'change_status_admin')
def change_stat(callback_query):
    bot.answer_callback_query(callback_query.id)
    message = bot.send_message(callback_query.from_user.id, "Введите номер находки",
                               reply_markup=telebot.types.ReplyKeyboardRemove())

    def choose_stat(message):
        sig = storage.get_sig(message.text)
        if sig is None:
            bot.reply_to(message, "Такой заявки нет",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
            org_panel(message, True)
        else:
            keyboard = telebot.types.ReplyKeyboardMarkup()
            button_1 = telebot.types.KeyboardButton(
                "accepted")
            keyboard.add(button_1)
            button_2 = telebot.types.KeyboardButton(
                "sent for testing")
            keyboard.add(button_2)

            button_3 = telebot.types.KeyboardButton(
                "testing")
            keyboard.add(button_3)

            button_3 = telebot.types.KeyboardButton(
                "nothing found")
            keyboard.add(button_3)

            button_4 = telebot.types.KeyboardButton(
                "tick found")
            keyboard.add(button_4)

            bot.reply_to(message, "Выберите статус", reply_markup=keyboard)

            def fin_change_stat(message, num, sig):
                storage.change_status(num, message.text)
                logging.info("Change status by {} ({}): ".format(str(message.from_user.id), message.from_user.username)+"Номер: {}\nФИО: {}\nДата {}\nМестоположение:\nlongitude {},\nlatitude {}\nСтатус: {}".format(
                    sig['num'], sig['fio'], sig['time'], sig['longitude'], sig['latitude'], sig['status'])+" -> {}\n----------------".format(message.text))
                bot.reply_to(message, 'Статус изменен',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
                admin_panel(message, True)

            bot.register_next_step_handler(
                message, fin_change_stat, message.text, sig)

    bot.register_next_step_handler(message, choose_stat)


@bot.callback_query_handler(func=lambda c: c.data == 'get_storage')
def get_storage(callback_query):
    bot.answer_callback_query(callback_query.id)
    # data = pandas.read_csv("storage.csv", index_col=False, encoding='utf-8')
    # data.to_excel("storage.xlsx", index=False, encoding='utf-8')
    f = open('storage.xlsx', "rb")
    bot.send_message(callback_query.from_user.id, "База данных:",
                     reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.send_document(callback_query.from_user.id, f)
    f.close()
    logging.info("----------------\n"+"Got storage by {} ({})".format(
        str(callback_query.from_user.id), callback_query.from_user.username)+"\n----------------")

bot.remove_webhook()

# Set webhook
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

# Disable CherryPy requests log
access_log = cherrypy.log.access_log
for handler in tuple(access_log.handlers):
    access_log.removeHandler(handler)

# Start cherrypy server
cherrypy.config.update({
    'server.socket_host'    : WEBHOOK_LISTEN,
    'server.socket_port'    : WEBHOOK_PORT,
    'server.ssl_module'     : 'builtin',
    'server.ssl_certificate': WEBHOOK_SSL_CERT,
    'server.ssl_private_key': WEBHOOK_SSL_PRIV
})

cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})
