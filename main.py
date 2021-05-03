import time
import configparser
from itertools import groupby

import paho.mqtt.client as mqtt
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


keys = {'погода': '1', 'теплицы': '2', 'приборы': '3'}


def maketree(group, items, path):
    def sep(s):
        return s.split('/', 1)

    head = [i for i in items if len(sep(i)) == 2]
    tail = [i for i in items if len(sep(i)) == 1]
    if len(tail) == 1:
        return group, tail[0]
    gv = groupby(sorted(head), lambda i: sep(i)[0])
    return group, dict([(i, path) for i in tail] + [maketree(g, [sep(i)[1] for i in v], '') for g, v in gv])


# Telegram process
def get_keyb():
    return [[InlineKeyboardButton('Погода', callback_data='1'),
            InlineKeyboardButton('Теплицы', callback_data='2')]]


def get_data_text(text, alldata):
    try:
        key = keys[text.lower()]
    except:
        return 'err'
    return get_data(key, alldata)


def get_data(key, alldata):
    tree = dict([maketree('tree', list(k + '/' + v for k, v in alldata.items()), '')])['tree']
    if key == '1':
        try:
            rez = tree['air']['outdoor']['1']['temp'] + ' °C\n' \
                + tree['air']['outdoor']['1']['humidity'] + ' %\n' \
                + tree['air']['outdoor']['1']['pressure'] + ' mmHg\n' \
                + tree['air']['outdoor']['1']['upd']
            return rez
        except:
            return 'Нет данных'
    elif key == '2':
        rez = ''
        try:
            for n, f in sorted(tree['air']['greenhouse'].items(), key=lambda item: int(item[0])):
                rez += '№ %s:   %s \n' % (n, f['temp'])
            rez += tree['air']['greenhouse']['1']['upd']
            return rez
        except:
            return 'Нет данных'
    elif key == '3':
        return '40'
    else:
        return 'Error'


def text(update, context):
    keyboard = get_keyb()
    reply_markup = InlineKeyboardMarkup(keyboard)
    rez = get_data_text(update.message.text, alldata)
    if rez == 'err':
        update.message.reply_text('>', reply_markup=reply_markup)
    else:
        update.message.reply_text(rez)


def button(update, context):
    query = update.callback_query
    query.answer()
    keyboard = get_keyb()
    reply_markup = InlineKeyboardMarkup(keyboard)
    rez = get_data(query.data, alldata)
    query.edit_message_text(text=rez, reply_markup=reply_markup)


def error(update, context):
    print('Update caused error ', time.strftime('%Y-%m-%d %H:%M:%S'), update, context.error)


# MQTT process
def on_connect(client, userdata, flags, rc):
    for topic in TOPICS.split(','):
        client.subscribe(topic)


def on_message(client, userdata, msg):
    alldata.update({str(msg.topic): str(msg.payload)[2:-1]})


def readmqtt():
    client = mqtt.Client()
    client.username_pw_set(username=NAME, password=PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(IP, PORT, 60)
    client.loop_forever()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('./settings.ini')
    TOKEN = config['TELEGRAM']['token']
    NAME = config['MQTT']['username']
    PASS = config['MQTT']['password']
    IP = config['MQTT']['ip']
    PORT = int(config['MQTT']['port'])
    TOPICS = config['MQTT']['topics']

    alldata = {}
    while 1:
        try:
            updater = Updater(TOKEN, use_context=True)
            dp = updater.dispatcher
            dp.add_handler(CommandHandler("start", text))
            dp.add_handler(CallbackQueryHandler(button))
            dp.add_handler(MessageHandler(Filters.text, text))
            dp.add_error_handler(error)
            updater.start_polling()
            readmqtt()
            updater.idle()
        except:
            print('Connection error')
            time.sleep(5)
