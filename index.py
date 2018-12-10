#!/usr/bin/env python3

# todo: send Fake Typing Indicator as loading
# todo: /debug mode

import os
import sys
import re
import requests
from requests.exceptions import RequestException
import urllib.parse as urlparse
from json import dumps as json_dump
from json import loads as json_parse
from random import randint
import traceback
import io
import math

import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from http.server import BaseHTTPRequestHandler, HTTPServer
from cowpy import cow

with open('pid', 'w') as pid_file:
    pid_file.write('%d\n' % os.getpid())


def printf(*args):
    print(*args, flush=True)


def kb(buttons):
    return ReplyKeyboardMarkup(keyboard=buttons)


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

users = {}  # todo
# users = {147445817: {
#     'id': 147445817, 'priority': 1, 'stage': 'photos_upload', 'stage_data': None, 'photos': [], 'shop_id': 27}
# }


class server_handler(BaseHTTPRequestHandler):

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

                printf('photo', task, i, json['state'])

                human_state = {
                    'processed': 'принято и обработано, баллы начислены! ❤️',
                    'error': 'какое-то не такое. ¯\_(ツ)_/¯\nОтправьте ещё одно?',
                    'processing': 'ещё обрабатывается',
                }[json['state']]

                if len(users[user_id]['photos']) > 1:
                    bot.sendMessage(user_id, 'Фото №%d %s' % (i + 1, human_state), reply_markup=kb([[
                        KeyboardButton(text='Закончить')
                    ]]))
                else:
                    bot.sendMessage(user_id, 'Фото %s' % human_state, reply_markup=kb([[
                        KeyboardButton(text='Закончить')
                    ]]))
            elif self.path.startswith('/bot/debug'):
                printf('<< DEBUG', self.path, 'method', self.command, query)
                data = json_parse(self.rfile.read(int(self.headers['Content-Length'])))
                printf('<< DEBUG << DATA', data)
                for item in data:
                    if 'text' in item:
                        bot.sendMessage(int(query['user_id'][0]), item['text'])
                    if 'photo_path' in item:
                        bot.sendPhoto(int(query['user_id'][0]), io.BytesIO(requests.get(item['photo_path']).content))
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(json_dump({'ok': True}).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                message = cow.Cowacter().milk('Hello from OilStone chatBot!1111111')
                self.wfile.write(message.encode())
        except Exception as e:
            printf(traceback.format_exc())

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json_dump({'error': str(e)}).encode())

    def do_POST(self):
        self.wfile.write(b'')

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

def getFileLink(file):
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
    global users

    def send(text, reply_markup=ReplyKeyboardRemove()):
        return bot.sendMessage(chat_id, text, reply_markup=reply_markup)

    stage = users[chat_id]['stage']

    def set_stage(stage, data=None):
        users[chat_id]['stage'] = stage
        users[chat_id]['stage_data'] = data

    printf("stage: %s" % stage)

    try:

        if stage == 'initial' or (content_type == 'text' and msg['text'].startswith('/start')):
            set_stage('geolocation')
            reply_text = ('Отправьте геолокацию, чтобы определить магазин.\n\n(Кнопка геолокации — слева от текстового поля)')
            send(reply_text)

        elif stage == 'geolocation':
            if content_type == 'location' or (content_type == 'text' and msg['text'].startswith('/sample')):
                send('Уточните магазин.')
                if content_type == 'location':
                    location = msg['location']
                else:
                    location = {'latitude': 55.758524, 'longitude': 37.658760}
                    send('Пример данных — координаты 55.758524,37.658760 (метро Курская)')
                try:
                    url = '%s/geo?latitude=%f&longitude=%f' % (
                        API_ORIGIN, location['latitude'] / (180 / math.pi), location['longitude'] / (180 / math.pi))
                    printf('url', url)
                    r = requests.get(url)
                    printf(r, r.json(), r.status_code)
                    if r.status_code == 200 or r.status_code == 201:
                        # shops = [ {'shop_id': 42, 'name': 'Пятёра'}, ]
                        shops = r.json()
                        set_stage('shop_select', data={'shops': shops})

                        keyboard = kb([shop_button(i, shop, shops) for i, shop in enumerate(shops)] + [[
                            KeyboardButton(text='Отменить')
                        ]])

                        send('Выберите магазин, в котором вы находитесь',
                             reply_markup=keyboard)
                        # todo: if count == 1 then auto_select
                    else:
                        send('😰 Упс! %s.\n\nПопробуем ещё раз через минуту?' %
                             r.json()['error'])
                except RequestException as e:
                    printf('RequestException')
                    printf(traceback.format_exc())
                    send(
                        '😰 Упс! Что-то пошло не так.\n\nПопробуйте ещё раз через минуту?')
                except Exception as e:
                    printf(traceback.format_exc())
                    send(
                        '😰 Упс! Что-то пошло не так.\n\nПопробуйте ещё раз через минуту?')
            else:
                send('Пожалуйста, отправьте именно геолокацию. Без неё не получится точно определить магазин.')

        elif stage == 'shop_select':
            if content_type == 'text':
                shops = users[chat_id]['stage_data']['shops']
                printf('shops', shops)
                if msg['text'] == 'Отменить':
                    set_stage('initial')
                    send('Спасибо! Чтобы отправить ещё фотографии, напишите /start.')
                    return

                match = re.search('^\\d+', msg['text'])
                if not match:
                    send('Пожалуйста, обязательно выберите один из представленных вариантов.\nЕсли магазина нет в списке, значит, мы не сможем принять фото из него.')
                else:
                    shop = shops[int(match.group(0)) - 1]
                    id = shop['shop_id']
                    users[chat_id]['shop_id'] = id
                    set_stage('photos_upload')
                    reply_text = ('Выбран магазин «%s».\n'
                                  'Сделайте одну или несколько фотографий стеллажей с майонезами «Слобода».\n\n'
                                  'Внимание: фотографировать надо спереди. а не сбоку, и упаковки должны быть видны хорошо!')
                    send(reply_text % shop['name'], reply_markup=kb([[KeyboardButton(text='Закончить')]]))

        elif stage == 'photos_upload':
            if content_type == 'photo' or (content_type == 'document' and msg['document']['mime_type'].startswith('image/')) or \
                    (content_type == 'text' and msg['text'].startswith('/sample')):
                if content_type == 'photo':
                    photo = msg['photo'][-1]
                elif content_type == 'document':
                    photo = msg['document']
                else:
                    photo = None
                try:
                    if photo is not None:
                        source_photo_path = getFileLink(photo['file_id'])
                    else:
                        source_photo_path = 'http://lonthra.kalan.cc/photo_2018-12-09_20-29-35.jpg'
                        photo = {'file_id': 'AAAAAAAAAAAAAAAAAAAAAAAAAsample'}
                        bot.sendPhoto(chat_id, 'http://lonthra.kalan.cc/photo_2018-12-09_20-29-35.jpg', caption='Пример фотографии')
                    printf('source_photo_path:')
                    printf(source_photo_path)
                    photo_path = '%s/%s.jpg' % (PHOTOS_URL_PATH,
                                                photo['file_id'])
                    save_photo(source_photo_path, '%s%s' %
                               (PHOTOS_LOCAL_DIR, photo_path))
                    r = start_processing(users[chat_id], photo['file_id'], '%s%s' % (
                        PHOTOS_URL_ORIGIN, photo_path))

                    if r.status_code == 200 or r.status_code == 201:
                        send('Фотография поступила на обработку.\n\nЕсли необходимо, можете отправить ещё одну или несколько.')

                    else:
                        send('Ой! %s.\n\nПопробуйте ещё раз через минуту?' %
                             r.json()['error'])

                except RequestException as e:
                    printf('RequestException')
                    printf(traceback.format_exc())
                    send(
                        'Что-то пошло не так.\n\nПопробуйте ещё раз через минуту?')
                except Exception as e:
                    printf(traceback.format_exc())
                    send(
                        'Что-то пошло не так.\n\nПопробуйте ещё раз через минуту?')

            elif content_type == 'text' and msg['text'] == 'Закончить':
                set_stage('initial')
                send('Спасибо! Чтобы отправить ещё фотографии, напишите /start.')

            else:
                send('Пожалуйста, отправьте именно фотографию витрины с майонезами «Слобода».')

    except Exception as e:
        printf(traceback.format_exc())
        send('Ой! Что-то совсем пошло не так.\n\nПопробуйте ещё раз через минуту?')


def shop_button(i, shop, shops):
    human_i = i + 1
    printf(shop)
    matches = [x for x in shops if x['name'] == shop['name']]
    if len(matches) != 1:
        name = '%d. %s (%s)' % (human_i, shop['name'], shop['shop_address'])
    else:
        name = '%d. %s' % (human_i, shop['name'])

    kb = KeyboardButton(text=name)
    printf(kb)
    return [kb]


def handle(msg):
    global users
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
serv = HTTPServer(("localhost", PORT), server_handler)
serv.serve_forever()
