# todo: send Fake Typing Indicator as loading
# todo: /debug mode

import os
import sys
import requests
from requests.exceptions import RequestException

import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from http.server import BaseHTTPRequestHandler, HTTPServer
from cowpy import cow


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        message = cow.Cowacter().milk('Hello from OilStone chatBot!1111111')
        self.wfile.write(message.encode())
        return


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

print('setup')

count = 0
users = {}


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


def start_processing(user, file_id, photo_path):
    task = {}
    task.update(user)
    task.update({
        'user_id': user['id'],
        'task_id': gen_task_id(user, file_id),
        'photo_path': photo_path,
    })

    # todo: add_user_photo({photo_path, task_id}) # users[chat_id].photos.push({ photo_path, task_id })

    # http -vj POST 'http://37.228.118.11:8080/task?task_id=42&priority=2&photo_path=https://invntrm.ru/path/to/img.jpg&user_id=147445817&shop_id=423'

    query = {key: task[key] for key in [
        'task_id',
        'priority',
        'photo_path',
        'user_id',
        'shop_id',
    ]}

    print('\n\nstart_processing...\n', 'task', task, 'query', query)

    r = requests.post('%s/task' % API_ORIGIN, query)
    print('task inited')
    print(r, r.json(), r.status_code)


def gen_task_id(user, file_id):
    return '%d-%s' % (user['id'], file_id)


def onMessage(msg, chat_id, content_type):
    global users, count

    def send(text, reply_markup=None):
        return bot.sendMessage(chat_id, text, reply_markup=reply_markup)

    stage = users[chat_id]['stage']

    def set_stage(stage, data=None):
        users[chat_id]['stage'] = stage
        users[chat_id]['stage_data'] = data

    print("stage: %s" % stage)

    if stage == 'initial':
        if content_type == 'text' and msg['text'].endswith('/start'):
            set_stage('geolocation')
            send('📍 Здравствуйте, %s! Хотите заработать на походах в магазин?\nОтправьте геолокацию, чтобы определить магазин.\n\n💡 Tip: кнопка слева от текстового поля' %
                 msg['from']['first_name'])

    elif stage == 'geolocation':
        if content_type == 'location':
            send('🙏 Спасибо! Сейчас уточним магазин...')
            location = msg['location']
            try:
                url = '%s/geo?latitude=%f&longitude=%f' % (API_ORIGIN, location['latitude'], location['longitude'])
                print('url', url)
                r = requests.get(url)
                print(r, r.json(), r.status_code)
                if r.status_code == 200 or r.status_code == 201:
                    # shops = [ {'shop_id': 42, 'name': 'Пятёра'}, ]
                    shops = r.json()
                    set_stage('shop_select', data={'shops': shops})

                    keyboard = ReplyKeyboardMarkup(
                        keyboard=[[shop_button(shop) for shop in shops]])

                    send('Выберите магазин в котором вы находитесь',
                         reply_markup=keyboard)
                    # todo: if count == 1 then auto_select
                else:
                    send('😰 Упс! %s.\n\nПопробуем ещё раз через минутку?' %
                         r.json()['error'])
            except RequestException as e:
                print('RequestException')
                print(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
            except Exception as e:
                print(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
        else:
            send('Okay... но нужна геолокация, без неё не получится определить магазин, в которов вы находитесь')

    elif stage == 'shop_select':
        if content_type == 'text':
            shops = users[chat_id]['stage_data']['shops']
            print('shops', shops)
            matches = [x for x in shops if x['name'] == msg['text']]
            print('matches', matches)
            if len(matches) != 1:
                send(
                    '😬 Нужно название мазазина из найденных вариантов,\nесли не нашёлся нужный — Сорян :(')
            else:
                id = matches[0]['shop_id']
                users[chat_id]['shop_id'] = id
                set_stage('photos_upload')
                send(
                    '🤳 Отлично! Выбран %s\nТеперь сделайте одну или несколько фотографий стеллажей с майонезами «Слобода»\n\n💡 Tip: упаковки должны быть хорошо видны' % msg[
                        'text'],
                    reply_markup=ReplyKeyboardRemove())

    elif stage == 'photos_upload':
        if content_type == 'photo':
            photo = msg['photo'][-1]
            try:
                source_photo_path = getFileLInk(photo['file_id'])
                print('source_photo_path:')
                print(source_photo_path)
                photo_path = '%s/%s.jpg' % (PHOTOS_URL_PATH, photo['file_id'])
                save_photo(source_photo_path, '%s%s' %
                           (PHOTOS_LOCAL_DIR, photo_path))
                start_processing(users[chat_id], photo['file_id'], '%s%s' % (PHOTOS_URL_ORIGIN, photo_path))
                send(
                    '🌈 Класс! Уже обрабатываем фотку.\n📸 Сделайте ещё одну или несколько фотографий или ожидайте результат')
            except RequestException as e:
                print('RequestException')
                print(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
            except Exception as e:
                print(e)
                send('😰 Упс! Что-то пошло не так.\n\nПопробуем ещё раз через минутку?')
        else:
            send('Okay... но нужна фотография витрины с майонезами «Слобода»')

    else:
        count += 1
        send((msg['text'] + " #%d") % count)


def shop_button(shop):
    print(shop)
    kb = KeyboardButton(text=shop['name'])
    print(kb)
    return kb


def handle(msg):
    global count, users
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(content_type, chat_type, chat_id)
    print(msg)

    if not users.get(chat_id):
        users[chat_id] = initial_user({'id': chat_id})

    onMessage(msg, chat_id, content_type)


def is_super_user(id):
    return id in SUPER_USERS


print('start tg polling')

bot = telepot.Bot(TOKEN)
MessageLoop(bot, handle).run_as_thread()


print('start localhost:%s' % PORT)
serv = HTTPServer(("localhost", PORT), handler)
serv.serve_forever()
