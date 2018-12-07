# from telegram.ext import Updater, CommandHandler

from http.server import BaseHTTPRequestHandler
from cowpy import cow


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        message = cow.Cowacter().milk('Hello from Python on Now Lambda!1111111')
        self.wfile.write(message.encode())
        return

# REQUEST_KWARGS = {
#     'proxy_url': 'socks5://37.139.30.202:5656',
#     # Optional, if you need authentication:
#     'urllib3_proxy_kwargs': {
#         'username': 'proxyuser',
#         'password': 'n9jXHGHE00Arj42eqn',
#       }
# }

# def hello(bot, update):
#     update.message.reply_text(
#         'Hello {}'.format(update.message.from_user.first_name))

# def start(bot, update):
#     update.message.reply_text(
#         'Hi, hi: {}'.format(update.message.from_user.first_name))

# print('wtf')

# updater = Updater('778814536:AAGZp7325xBl2fb73PgAI7bQTYfV9Ao44sk',
#                   request_kwargs=REQUEST_KWARGS)

# print('setup')

# updater.dispatcher.add_handler(CommandHandler('hello', hello))
# updater.dispatcher.add_handler(CommandHandler('start', start))

# print('get_me')
# print(updater.bot.get_me())

# print('start_polling')

# updater.start_polling()
# updater.idle()
