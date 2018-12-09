#!/usr/bin/env python3

# todo: send Fake Typing Indicator as loading
# todo: /debug mode

import os
import sys
import requests
from requests.exceptions import RequestException
import urllib.parse as urlparse
from json import dumps as json_dump
from json import loads as json_parse
from random import randint

import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from http.server import BaseHTTPRequestHandler, HTTPServer
from cowpy import cow

with open('pid', 'w') as pid_file:
    pid_file.write('%d\n' % os.getpid())


def printf(*args):
    print(*args, flush=True)


printf('setup')


TOKEN = sys.argv[1]  # get token from command-line
SUPER_USERS = [
    147445817,  # alex
    164228786,  # oleg
    48531466,   # nick
    218439424,  # monty
]
API_ORIGIN = 'http://37.228.118.11:8080'
PORT = 8088
PHOTOS_URL_ORIGIN = 'http://uiguy.ru'  # 37.139.30.202
PHOTOS_URL_PATH = '/oil-stone-urban-hackaton/photos'
PHOTOS_LOCAL_DIR = '/var/www/uiguy.ru'

STAGES = {
    'initial': 'initial',
    'geolocation': 'geolocation',
    'shop_select': 'shop_select',
    'photos_upload': 'photos_upload',
}


count = 0
users = {}  # todo
# users = {147445817: {
#     'id': 147445817, 'priority': 1, 'stage': 'photos_upload', 'stage_data': None, 'photos': [], 'shop_id': 27}
# }


class handler(BaseHTTPRequestHandler):

    def do_PATCH(self):
        try:
            self.log_request()
            query = urlparse.parse_qs(urlparse.splitquery(self.path)[1])
            if self.path.startswith('/bot/task'):
                printf('<< server', self.path, 'method', self.command, query)
                [user_id, task_id] = [
                    int(query['user_id'][0]), query['task_id'][0]]
                json = json_parse(self.rfile.read(
                    int(self.headers['Content-Length'])))
                printf('json', json, 'user', users[user_id]['photos'])

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json_dump({'ok': True}).encode())

                (task, i) = [(x, i) for i, x in enumerate(
                    users[user_id]['photos']) if x['task_id'] == task_id][0]

                printf('photo', task, i, json['status'])

                human_status = {
                    'processed': 'успешно обработано, баллы начислены! ❤️',
                    'error': 'какое-то не такое. ¯\_(ツ)_/¯\n😞 Попробуем ещё разок?',
                    'processing': 'ещё обрабатывается',
                }[json['status']]

                if len(users[user_id]['photos']) > 1:
                    bot.sendMessage(user_id, 'Фото №%d %s' % (i + 1, human_status))
                else:
                    bot.sendMessage(user_id, 'Фото %s' % human_status)
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                message = cow.Cowacter().milk('Hello from OilStone chatBot!1111111')
                self.wfile.write(message.encode())
        except Exception as e:
            printf(e)

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json_dump({'error': str(e)}).encode())

    def do_GET(self):
        message = cow.Cowacter().milk('Hello from OilStone chatBot!1111111')
        self.wfile.write(message.encode())


def initial_user(data):
    user = {
        'id': None,
        'priority': (1 if is_super_user(data['id']) else 2),
        'stage': STAGES['initial'],
        'stage_data': None,
        'photos': [],
        'shop_id': None,
    }
    user.update(data)
    return user


def getFileLInk(file):
    file_ = bot.getFile(file)
    return 'https://api.telegram.org/file/bot%s/%s' % (TOKEN, file_['file_path'])


def save_photo(source_photo_path, photo_path):
    os.system('curl "%s" > %s' % (source_photo_path, photo_path))


def add_user_photo(task):
    users[task['user_id']]['photos'].append(
        {'photo_path': task['photo_path'], 'task_id': task['task_id']})


def start_processing(user, file_id, photo_path):
    task = {}
    task.update(user)
    task.update({
        'user_id': user['id'],
        'task_id': gen_task_id(user, file_id),
        'photo_path': photo_path,
    })

    add_user_photo(task)

    # http -vj POST 'http://37.228.118.11:8080/task?task_id=42&priority=2&photo_path=https://invntrm.ru/path/to/img.jpg&user_id=147445817&shop_id=423'

    query = {key: task[key] for key in [
        'task_id',
        'priority',
        'photo_path',
        'user_id',
        'shop_id',
    ]}

    printf('\n\nstart_processing...\n', 'task', task, 'query', query)

    r = requests.post('%s/task' % API_ORIGIN, query)
    printf('task inited')
    printf(r, r.json(), r.status_code)
    return r


def gen_task_id(user, file_id):
    return '%d-%s-%d' % (user['id'], file_id, randint(0, 1e6))


def onMessage(msg, chat_id, content_type):
    global users, count

    def send(text, reply_markup=None):
        return bot.sendMessage(chat_id, text, reply_markup=reply_markup)

    stage = users[chat_id]['stage']

    def set_stage(stage, data=None):
        users[chat_id]['stage'] = stage
        users[chat_id]['stage_data'] = data

    printf("stage: %s" % stage)

    if stage == 'initial':
        if content_type == 'text' and msg['text'].startswith('/start'):
            set_stage('geolocation')
            send('📍 Здравствуйте, %s! Хотите заработать на походах в магазин?\nОтправьте геолокацию, чтобы определить магазин.\n\n💡 Tip: кнопка слева от текстового поля' %
                 msg['from']['first_name'])

    elif stage == 'geolocation':
        if content_type == 'location':
            send('🙏 Спасибо! Сейчас уточним магазин...')
            location = msg['location']
            try:
                url = '%s/geo?latitude=%f&longitude=%f' % (
                    API_ORIGIN, location['latitude'], location['longitude'])
                printf('url', url)
                r = requests.get(url)
                printf(r, r.json(), r.status_code)
                if r.status_code == 200 or r.status_code == 201:
                    # shops = [ {'shop_id': 42, 'name': 'Пятёра'}, ]
                    shops = r.json()
                    set_stage('shop_select', data={'shops': shops})

                    keyboard = ReplyKeyboardMarkup(
                        keyboard=[[shop_button(shop, shops) for shop in shops]])

                    send('Выберите магазин в котором вы находитесь',
                         reply_markup=keyboard)
                    # todo: if count == 1 then auto_select
                else:
                    send('😰 Упс! %s.\n\nПопробуем ещё раз через минутку?' %
                         r.json()['error'])
            except RequestException as e:
                printf('RequestException')
                printf(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
            except Exception as e:
                printf(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
        else:
            send('Okay... но нужна геолокация, без неё не получится определить магазин, в которов вы находитесь')

    elif stage == 'shop_select':
        if content_type == 'text':
            shops = users[chat_id]['stage_data']['shops']
            printf('shops', shops)
            matches = [x for x in shops if x['name'] == msg['text']]
            printf('matches', matches)
            if len(matches) != 1:
                send(
                    '😬 Нужно название мазазина из найденных вариантов,\nесли не нашёлся нужный — Сорян :(')
            else:
                id = matches[0]['shop_id']
                users[chat_id]['shop_id'] = id
                set_stage('photos_upload')
                send(
                    '🤳 Отлично! Выбран мазазан «%s».\nТеперь сделайте одну или несколько фотографий стеллажей с майонезами «Слобода»\n\n💡 Tip: упаковки должны быть хорошо видны' % msg[
                        'text'],
                    reply_markup=ReplyKeyboardRemove())

    elif stage == 'photos_upload':
        if content_type == 'photo' or (content_type == 'document' and msg['document']['mime_type'].startswith('image/')):
            photo = msg['photo'][-1] if content_type == 'photo' else msg['document']
            try:
                source_photo_path = getFileLInk(photo['file_id'])
                printf('source_photo_path:')
                printf(source_photo_path)
                photo_path = '%s/%s.jpg' % (PHOTOS_URL_PATH, photo['file_id'])
                save_photo(source_photo_path, '%s%s' %
                           (PHOTOS_LOCAL_DIR, photo_path))
                r = start_processing(users[chat_id], photo['file_id'], '%s%s' % (
                    PHOTOS_URL_ORIGIN, photo_path))

                if r.status_code == 200 or r.status_code == 201:
                    send('🌈 Класс! Обрабатываем.\n📸 Сделайте ещё одну/несколько фотографий\nили подождите секундочку')

                else:
                    send('😰 Упс! %s.\n\nПопробуем ещё раз через минутку?' %
                         r.json()['error'])

            except RequestException as e:
                printf('RequestException')
                printf(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
            except Exception as e:
                printf(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
        else:
            send('Okay... но нужна фотография витрины с майонезами «Слобода»')

    else:
        count += 1
        send((msg['text'] + " #%d") % count)


def shop_button(shop, shops):
    printf(shop)
    matches = [x for x in shops if x['name'] == shop['name']]
    if len(matches) != 1:
        name = '%s (%s)' % (shop['name'], shop['shop_address'])
    else:
        name = shop['name']

    kb = KeyboardButton(text=name)
    printf(kb)
    return kb


def handle(msg):
    global count, users
    content_type, chat_type, chat_id = telepot.glance(msg)
    printf(content_type, chat_type, chat_id)
    printf(msg)

    if not users.get(chat_id):
        users[chat_id] = initial_user({'id': chat_id})

    onMessage(msg, chat_id, content_type)


def is_super_user(id):
    return id in SUPER_USERS


printf('start tg polling')

bot = telepot.Bot(TOKEN)
MessageLoop(bot, handle).run_as_thread()


printf('start localhost:%s' % PORT)
serv = HTTPServer(("localhost", PORT), handler)
serv.serve_forever()
