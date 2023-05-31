import telebot
import logging
import time
import random
from telebot import types
import pymorphy2
import json
from threading import Thread
import re

print ("Let's go! Поехали!")

API_TOKEN = 'insert_API_token_here' #can be taken at BotFather
bot = telebot.TeleBot(API_TOKEN)
morph = pymorphy2.MorphAnalyzer()
MarkdownV2 = "MarkdownV2"

class player:
  """Класс для игрока"""
  def __init__(self, chat_id, user_id, name, words, result_points, result_words, result_unique, result_full):
    self.chat_id = chat_id
    self.user_id = user_id
    self.name = name
    self.words = words
    self.result_points = result_points
    self.result_words = result_words
    self.result_unique = result_unique

class game:
  """Класс для игры"""
  def __init__(self, code, word, duration, admin_id, players, current):
    self.code = code
    self.word = word
    self.duration = duration
    self.admin_id = admin_id
    self.players = players
    self.current = current

class user:
  """Класс для юзера"""
  def __init__(self, chat_id, user_id, name, gender, current, game, prev_game):
    self.chat_id = chat_id
    self.user_id = user_id
    self.name = name
    self.gender = gender
    self.current = current
    self.game = game
    self.prev_game = prev_game


def default_player(chat_id, user_id):
  default = player(chat_id = chat_id, user_id = user_id, name = users[chat_id].name, words = [], result_points = 0, result_words = 0, result_unique = 0, result_full = "")
  return default



def default_game(code, admin_id):
  default = game(code = code, word = "", duration = 10, admin_id = admin_id, players = [default_player(admin_id, users[admin_id].user_id)], current = "awaits")
  return default

games = {}
users = {}

def make_user(chat_id, user_id):
  user1 = user(chat_id = chat_id, user_id = user_id, name = "", gender = "", current = "reading", game = "", prev_game = "")
  users[chat_id] = user1
  bot.send_message(chat_id, "Привет!")
  time.sleep(2)
  bot.send_message(chat_id, "С тех пор, как вы последний раз пользовались этим ботом, он был перезагружен (или вы им ещё не пользовались).")
  time.sleep(3)
  bot.send_message(chat_id, "Поэтому мне нужно вас авторизовать. Как вас называть?\n"
    "(Придумайте себе никнейм не длиннее 15 символов)")
  user1.current = "get_name"

def check_username(username):
  for i in username:
    if i not in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя abcdefghijklmnopqrstuvwxyz':
      return False
  return True

def make_user_got_name(id, name):
  if len(name) > 15:
    bot.send_message(id, "Никнейм не может быть длиннее 15 символов. Пожалуйста, придумайте покороче.")
    users[id].current = "get_name"
  elif not check_username(name):
    bot.send_message(id, "Никнейм может содержать только русские и английские буквы. Пожалуйста, придумайте покороче.")
    users[id].current = "get_name"
  elif name in users:
    bot.send_message(id, "Этот никнейм уже занят. Придумайте другой.")
    users[id].current = "get_name"
  else:
    users[id].name = name
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text = 'в форме м.р., напр. "выиграл"', callback_data = 'male'))
    keyboard.add(types.InlineKeyboardButton(text = 'в форме ж.р., напр. "выиграла"', callback_data = 'female'))
    bot.send_message(id, "Хорошо, " + name + ".")
    bot.send_message(id, "В какой форме про вас говорить?\n", reply_markup = keyboard)
    users[id].current = "get_gender"

def make_user_got_gender(id, gender):
  users[id].gender = gender
  bot.send_message(id, "Спасибо! Теперь можно начать работу со мной.\n"
                       "Чтобы присоединиться к игре, нажмите /join_game.\n"
                       "Чтобы создать игру, нажмите /new_game.")

def send_to_all(code, text):
  if code not in games:
    return
  for player in games[code].players:
    bot.send_message(player.chat_id, text)

def bold(text):
  return "*" + text + "*"

def italic(text):
  return "_" + text + "_"

def crossed(text):
  return "~" + text + "~"

def monospaced(text):
  return "```" + text + "```"


def agree(word, number):
  return morph.parse(word)[0].make_agree_with_number(number).word

def linked_name(id):
  return "[" + users[id].name + "](tg://user?id=" + str(users[id].user_id) + ")"


def to_case(arr, case):
    ans = []
    for i in arr:
        word = morph.parse(i)[0]
        ans.append(word.inflect({case}).word)
    return ans

def write_time(time1):
  result = ""
  if time1 // 60 > 0:
    result += str(time1 // 60) + " " + agree("минута", time1 // 60)
  if time1 // 60 > 0 and time1 % 60 > 0:
    result += " "
  if time1 % 60 > 0:
    result += str(time1 % 60) + " " + agree("секунда", time1 % 60)
  return result

def random_syllable():
  consonants = 'БВГДЖЗКЛМНПРСТФХЦЧШЩ'
  vowels = 'АОУЫЭЯЁЮИЕ'
  syll = ''
  while syll == '' or (syll[0] in 'ЖЦЧШЩ' and syll[1] in 'ЫЭЯЁЮ'):
    cons = random.randint(0, 19)
    vow = random.randint(0, 9)
    syll = consonants[cons] + vowels[vow]
  return syll

def generate_code_letters():
  code = ''
  while (code == '' or code in games):
    code = random_syllable() + random_syllable() + random_syllable()
  return code

def generate_code_numbers():
  code = ''
  while (code == '' or code in games):
    code = random.randint(100, 999)
  return str(code)

def in_word(word1, word2):
  #word1 – слово, предположительно составленное из word2
  word1 = ''.join(sorted(word1))
  word2 = ''.join(sorted(word2))
  i = 0
  k = 0
  while i < len(word1):
    while k + 1 < len(word2) and word1[i] != word2[k]:
      k += 1
    if word1[i] != word2[k]:
      return False
    if k + 1 == len(word2) and i + 1 < len(word1):
      return False
    i += 1
    k += 1
  return True

def noun_and_normal_form(word):
  p = morph.parse(word)
  for i in range(len(p)):
    if 'NOUN' in p[i].tag:
      if p[i].word == p[i].normal_form:
        return True
  return False

def get_name(message):
  if message.from_user.last_name == None:
    return message.from_user.first_name
  else:
    return message.from_user.first_name + ' ' + message.from_user.last_name

def not_now(id):
  cur = users[id].current
  if cur == "word_for_game":
    bot.send_message(id, "Не надо начинать что-то новое – ответьте на вопрос: из какого слова будут составляться другие слова?")
  elif cur == 'game_duration_own':
    bot.send_message(id, "Не надо начинать что-то новое – ответьте на вопрос: сколько будет длиться игра?")
  elif cur == "join_game":
    bot.send_message(id, "Не надо начинать что-то новое – пришлите мне код игры, к которой хотите присоединиться.")
  elif cur == "game" or cur == "game_admin":
    bot.send_message(id, "Не надо начинать что-то новое во время игры – лучше пишите слова.")
  elif cur == "get_name":
    bot.send_message(id, "Вы не ответили на мой вопрос: как вас называть?")
  elif cur == "new_nickname":
    bot.send_message(id, "Вы не ответили на мой вопрос: каким будет ваш новый никнейм?")
  elif cur == "awaits_game_admin":
    bot.send_message(id, "Не надо начинать что-то новое, вы уже создали игру.")
  elif cur == "awaits_game":
    bot.send_message(id, "Не надо начинать что-то новое, вы уже присоединились к игре.")
  elif cur == "game_duration":
    bot.send_message(id, "Не надо начинать что-то новое, выберите из вариантов длительность игры.")
  elif cur == "ready_to_start":
    bot.send_message(id, "Не надо начинать что-то новое, ответьте, хотите ли вы начать игру.")
  elif cur in ["get_gender", "change_gender", "leave_game_awaits", "leave_game", "cancel_game", "see_results"]:
    bot.send_message(id, "Пожалуйста, выберите нужный вариант из предложенных.")
  elif cur == "start_game_go":
    bot.send_message(id, "Подождите, игра сейчас начнётся.")
  elif cur == "leave_game":
    bot.send_message(id, "Нельзя выйти из игры, не войдя в неё (/join_game).")
  else:
    bot.send_message(id, "Не надо начинать новое дело, пока не закончили предыдущее.")

@bot.message_handler(commands=['rules'])
def send_rules(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in [""]:
    not_now(id)
    return
  bot.send_document(id, open(r'Правила игры в Слова из слов.pdf', 'rb'))

@bot.message_handler(commands=['help'])
def send_help(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in [""]:
    not_now(id)
    return
  bot.send_message(id, 'С моей помощью можно сыграть в "Слова из слов" (в Наборщика).\n'
                                      "Для создания новой игры нажмите /new_game.\n"
                                      "Чтобы присоединиться к уже созданной игре, нажмите /join_game.\n"
                                      "Игра закончится по истечении заданного времени,\n"
                                      "или если её создатель вызовет /end_game.\n")


@bot.message_handler(commands=['start'])
def start_bot(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in [""]:
    not_now(id)
    return
  bot.send_message(id, "Привет, " + users[message.chat.id].name + '!')
  bot.send_sticker(id, 'CAACAgIAAxkBAALwrF7k_QnoF-kAAQEKhLSJlu0CUWUdgQACNQEAAjDUnRG0uDX9ZqC2fBoE')
  bot.send_message(id, 'Я бот для игры в "Слова из слов" (в Наборщика). Для подробной информации нажмите /help.')

@bot.message_handler(commands=['change_nickname'])
def change_nickname(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in [""]:
    not_now(id)
    return
  bot.send_message(id, "Хорошо, каким будет ваш новый никнейм (напоминаю, не больше 15 символов)?")
  users[id].current = "new_nickname"

def got_nickname(id, name):
  if len(name) > 15:
    bot.send_message(id, "Никнейм не может быть длиннее 15 символов. Пожалуйста, придумайте покороче.")
    users[id].current = "get_name"
  elif name in users:
    bot.send_message(id, "Этот никнейм уже занят. Придумайте другой.")
    users[id].current = "get_name"
  else:
    users[id].name = name
    bot.send_message(id, "Хорошо, теперь вы " + name + ".")

@bot.message_handler(commands=['change_gender'])
def change_gender(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in [""]:
    not_now(id)
    return
  users[id].current = "change_gender"
  keyboard = types.InlineKeyboardMarkup()
  keyboard.add(types.InlineKeyboardButton(text = 'в форме м.р., напр. "выиграл"', callback_data = 'male'))
  keyboard.add(types.InlineKeyboardButton(text = 'в форме ж.р., напр. "выиграла"', callback_data = 'female'))
  bot.send_message(id, "В какой форме про вас говорить?\n", reply_markup = keyboard)

def got_gender(id, gender):
  users[id].gender = gender
  if gender == "male":
    bot.send_message(id, "Хорошо, теперь я буду писать про вас в мужском роде.")
  else:
    bot.send_message(id, "Хорошо, теперь я буду писать про вас в женском роде.")

@bot.message_handler(commands=['new_game'])
def new_game(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current != "":
    not_now(id)
    return
  users[id].current = "awaits_game_admin"
  code = str(generate_code_numbers())
  users[id].game = code
  games[code] = default_game(code, id)
  bot.send_message(id, "Объявляю набор в игру! Код – " + code + '.\n'
                                    'Дайте его всем, с кем хотите сыграть, и попросите их вызвать у себя /join_game.\n'
                                    'Когда будете готовы начать игру, отправьте /start_game.')

@bot.message_handler(commands=['cancel_game'])
def cancel_game(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in ["awaits_game_admin", ""]:
    not_now(id)
    return
  if users[id].current == "awaits_game_admin":
    users[id].current = "cancel_game"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text = "Да, отменить", callback_data = "yes"))
    keyboard.add(types.InlineKeyboardButton(text = "Не отменять", callback_data = "no"))
    bot.send_message(id, "Вы уверены, что хотите отменить игру?", reply_markup = keyboard)
  elif users[id].current == "awaits_game":
    bot.send_message(id, "Если вы хотите выйти из игры, нажмите /leave_game.")
  elif users[id].current == "game_admin":
    bot.send_message(id, "Если вы хотите завершить игру для всех, нажмите /end_game.")
  elif users[id].current == "game":
    bot.send_message(id, "Если вы хотите выйти из игры, нажмите /leave_game.")
  else:
    bot.send_message(id, "Вы не создавали игру, вам нечего отменять.")

def cancel_game_continue(id):
  id = message.chat.id
  code = users[id].game
  for player in games[code].players:
    if player.chat_id != id:
      if users[id].gender == "male":
        bot.send_message(player.chat_id, "К сожалению, создатель игры, " + linked_name(id) + ", отменил её.\n" +
                                  "Вы можете присоединиться к другой игре, нажав /join_game, или создать свою с помощью /new_game.", parse_mode = "MarkdownV2")
      else:
        bot.send_message(player.chat_id, "К сожалению, создательница игры, " + linked_name(id) + ", отменила её.\n" +
                                  "Вы можете присоединиться к другой игре, нажав /join_game, или создать свою с помощью /new_game.", parse_mode = "MarkdownV2")
  games.pop(code)

@bot.message_handler(commands=['start_game'])
def start_game(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in ["awaits_game_admin", "awaits_game", ""]:
    not_now(id)
    return
  if users[id].game == "":
    bot.send_message(id, "Чтобы начать игру, её нужно сначала создать командой /new_game.")
  elif users[id].current == "awaits_game":
    bot.send_message(id, "Начать игру может только её создатель.")
  else:
    ask_word_for_game(id)

def ask_word_for_game(id):
  bot.send_message(id, "Из какого слова будут составляться другие слова?")
  users[id].current = 'word_for_game'

def get_word_for_game(id, text):
  code = users[id].game
  if noun_and_normal_form(text.lower()):
    games[code].word = text.lower()
    bot.send_message(id, "Хорошо, слово '" + games[code].word.upper() + "'.")
    ask_game_duration(id)
  else:
    bot.send_message(id, "Такого слова я не знаю. Попробуйте ещё раз.")
    users[id].current = "word_for_game"


def ask_game_duration(id):
  keyboard = types.InlineKeyboardMarkup()
  keyboard.add(types.InlineKeyboardButton(text = '5 минут', callback_data = '5'))
  keyboard.add(types.InlineKeyboardButton(text = '10 минут', callback_data = '10'))
  keyboard.add(types.InlineKeyboardButton(text = '15 минут', callback_data = '15'))
  keyboard.add(types.InlineKeyboardButton(text = 'свой вариант', callback_data = 'own'))
  keyboard.add(types.InlineKeyboardButton(text = 'поменять слово', callback_data = 'change_word'))

  bot.send_message(id, "Сколько будет длиться игра?", reply_markup=keyboard)
  users[id].current = "game_duration"

def get_game_duration(id, text):
  if not text.isdigit():
      bot.send_message(id, "Отправьте мне, пожалуйста, только целое число – длительность игры в минутах.")
      users[id].current = "game_duration_own"
  elif int(text) <= 0:
      bot.send_message(id, "Тогда игра уже закончилась :)\n"
                           "Отправьте мне, пожалуйста, **положительное число** – длительность игры в минутах.")
      users[id].current = "game_duration_own"
  elif int(text) > 20:
      bot.send_message(id, "Это слишком долго. Пожалуйста, отправьте мне длительность игры в минутах (не больше 20).")
      users[id].current = "game_duration_own"
  else:
      games[users[id].game].duration = int(text)
      if int(text) == 1:
        bot.send_message(id, "Хорошо, игра продлится " + text + " минуту.")
      elif int(text) < 5:
        bot.send_message(id, "Хорошо, игра продлится " + text + " минуты.")
      else:
        bot.send_message(id, "Хорошо, игра продлится " + text + " минут.")
      ready_to_start(id)

def ready_to_start(id):
  keyboard = types.InlineKeyboardMarkup()
  keyboard.add(types.InlineKeyboardButton(text = 'начать!', callback_data = 'start'))
  keyboard.add(types.InlineKeyboardButton(text = 'поменять длительность игры', callback_data = 'change_duration'))
  bot.send_message(id, "Ура, мы готовы начать игру!", reply_markup = keyboard)
  users[id].current = "ready_to_start"

def start_game_go(id):
  code = users[id].game
  games[code].current = "in_progress"
  for player in games[code].players:
    users[player.chat_id].current = "start_game_go"
  minutes = "минут"
  if games[code].duration == 1:
    minutes = "минуту"
  elif games[code].duration < 5:
    minutes = "минуты"
  else:
    miutes = "минут"
  send_to_all(code, "Готовьтесь к началу игры! \n"
                                "Она продлится " + str(games[code].duration) + " " + minutes + ".\n")
  time.sleep(2)
  for text in ["На старт!\n", "Внимание!\n", "Поехали!\n"]:
    send_to_all(code, text)
    time.sleep(1)
  for player in games[code].players:
    bot.pin_chat_message(player.chat_id, bot.send_message(player.chat_id, games[code].word.upper()).message_id)

  for player in games[code].players:
    users[player.chat_id].current = 'game'
  users[id].current = "game_admin"

  time_left = games[code].duration * 60
  time_passed = 0
  while time_left > 0:
    if time_left == games[code].duration * 30 and time_left != 60:
      send_to_all(code, "Половина времени прошла! Осталось " + write_time(time_left) + ".")
    elif time_left == games[code].duration * 30 and time_left in [60, 90]:
      send_to_all(code, "Половина времени прошла! Осталась " + write_time(time_left) + ".")
    elif time_passed % 60 == 0 and time_passed > 0 and time_left > 60:
      send_to_all(code, "Осталось " + write_time(time_left) + ".")
    elif time_left == 60 and time_passed > 0:
      send_to_all(code, "Осталась 1 минута.")
    elif time_left == 10:
      send_to_all(code, "Осталось 10 секунд.")
    time.sleep(1)
    time_left -= 1
    time_passed += 1
  end_game(id)

def compare(player):
  return player.result_points

def end_game(id):
  code = users[id].game
  games[code].current = "finished"
  send_to_all(code, "Игра окончена!")
  for player1 in games[code].players:
    player1.result_full = ""
    for word in player1.words:
      player1.result_words += 1
      have_word = 0
      for player2 in games[code].players:
        if word in player2.words:
          have_word += 1
      if len(games[code].players) == have_word:
        player1.result_full += crossed(word) + "\n"
      else:
        if have_word == 1:
          player1.result_unique += 1
          player1.result_full += bold(word) + ": "
        else:
          player1.result_full += word + ": "
        player1.result_points += len(word) + len(games[code].players) - have_word
        player1.result_full += str(len(word) + len(games[code].players) - have_word) + "\n"
  games[code].players.sort(key = compare, reverse = True)
  count = 1
  results = "Результаты:\n" + "кол\. баллов, кол\. слов, кол\. уникальных\n"
  for player in games[code].players:
    if count == 1:
      results += "🥇 "
    elif count == 2:
      results += "🥈 "
    elif count == 3:
      results += "🥉 "
    else:
      results += "• "
    results += linked_name(player.chat_id) + ": " + str(player.result_points) + ", " + str(player.result_words) + ", " + str(player.result_unique) + "\n"
    count += 1

  results += "\n" + "С помощью кнопок ниже можно увидеть полные результаты каждого игрока " + "\n\(" + bold("жирным") + " выделены уникальные слова,\n" + crossed("зачёркнуты") + " слова, которые написали все\):"

  keyboard = types.InlineKeyboardMarkup()
  for player in games[code].players:
    keyboard.add(types.InlineKeyboardButton(text = player.name, callback_data = 'Результат ' + linked_name(player.chat_id) + ' в игре в слово "' + games[code].word + '":\n' + player.result_full))
  for player in games[code].players:
    bot.send_message(player.chat_id, results, reply_markup = keyboard, parse_mode = "MarkdownV2")
  for player in games[code].players:
    users[player.chat_id].game = ""
  games.pop(code)

@bot.message_handler(commands=['end_game'])
def ending_game(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in ["", "game_admin"]:
    not_now(id)
    return
  if "game" not in users[id].current or users[id].game == "":
    bot.send_message(id, "Чтобы начать и завершить игру, её нужно сначала создать командой /new_game или присоединиться к ней через /join_game.")
  elif users[id].current != "game_admin":
    bot.send_message(id, "Вы не можете завершить игру.")
  else:
    users[id].current = "end_game"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text = "Да, завершить игру", callback_data = "yes"))
    keyboard.add(types.InlineKeyboardButton(text = "Отменить", callback_data = "no"))
    bot.send_message(id, "Вы уверены, что хотите завершить игру?", reply_markup = keyboard)

@bot.message_handler(commands=['join_game'])
def join_game(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current != "":
    not_now(id)
    return
  users[id].current = "join_game"
  bot.send_message(id, "Отправьте мне код доступа игры.\n")

def join_game_continue(message):
  id = message.chat.id
  code = message.text
  if code in games and users[games[code].admin_id].current == "awaits_game_admin":
    users[id].current = "awaits_game"
    users[id].game = code
    games[code].players.append(default_player(id, message.from_user.id))
    bot.send_message(id, "Добро пожаловать в игру, созданную " + linked_name(games[code].admin_id) + ".")
    players_list = "Уже участвуют:\n"
    for player in games[code].players:
      players_list += "• " + player.name + "\n"

    players_list += "Всего " + str(len(games[code].players)) + " " + agree("человек", len(games[code].players)) + "."
    bot.send_message(id, players_list)

    for player in games[code].players:
      if (player.chat_id != id):
        if users[id].gender == "male":
          if len(games[code].players) % 10 in [2, 3, 4] and len(games[code].players) % 100 not in [12, 13, 14]:
            bot.send_message(player.chat_id, "К игре присоединился " + linked_name(id) + ".\n"
                                      "Всего уже " + str(len(games[code].players)) + " человека.", parse_mode = "MarkdownV2")
          else:
            bot.send_message(player.chat_id, "К игре присоединился " + linked_name(id) + ".\n"
                                      "Всего уже " + str(len(games[code].players)) + " человек.", parse_mode = "MarkdownV2")

        else:
          if len(games[code].players) % 10 in [2, 3, 4] and len(games[code].players) % 100 not in [12, 13, 14]:
            bot.send_message(player.chat_id, "К игре присоединилась " + linked_name(id) + ".\n"
                                      "Всего уже " + str(len(games[code].players)) + " человека.", parse_mode = "MarkdownV2")
          else:
            bot.send_message(player.chat_id, "К игре присоединилась " + linked_name(id) + ".\n"
                                      "Всего уже " + str(len(games[code].players)) + " человек.", parse_mode = "MarkdownV2")
  elif code in games and users[games[code].admin_id].current == "game_admin":
    users[id].current = "game"
    users[id].game = code
    games[code].players.append(default_player(id))
    bot.send_message(id, "Добро пожаловать в игру, созданную " + linked_name(games[code].admin_id) + ".\n"
                         "Сейчас я пришлю вам слово и вы можете начинать писать из него слова.", parse_mode = "MarkdownV2")
    time.sleep(1)
    bot.pin_chat_message(id, bot.send_message(id, games[code].word.upper()).message_id)

    for player in games[code].players:
      if (player.chat_id != id):
        if users[id].gender == "male":
          bot.send_message(player.chat_id, "К игре присоединился " + linked_name(id) + "!\n", parse_mode = "MarkdownV2")
        else:
          bot.send_message(player.chat_id, "К игре присоединилась " + linked_name(id) + "!\n", parse_mode = "MarkdownV2")
  else:
    bot.send_message(id, "Я не нашёл игры с таким кодом.\n Попробуйте ещё раз – нажмите /join_game.")

@bot.message_handler(commands=['leave_game'])
def leave_game(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if users[id].current not in ["awaits_game", "awaits_game_admin", "game_admin"]:
    not_now(id)
    return
  if users[id].current == "awaits_game":
    users[id].id = "leave_game_awaits"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text = "Да, выйти из игры", callback_data = "yes"))
    keyboard.add(types.InlineKeyboardButton(text = "Отменить", callback_data = "no"))
    bot.send_message(id, "Вы уверены, что хотите выйти?", reply_markup = keyboard)
  if users[id].current == "game":
    users[id].id = "leave_game"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text = "Да, выйти из игры", callback_data = "yes"))
    keyboard.add(types.InlineKeyboardButton(text = "Отменить", callback_data = "no"))
    bot.send_message(id, "Если вы выйдете, ваш результат обнулится. Вы уверены, что хотите выйти?", reply_markup = keyboard)
  elif users[id].current == "awaits_game_admin":
    bot.send_message(id, "Создатель игры не может выйти из неё. Если вы хотите отменить игру для всех, нажмите /cancel_game.")
  elif users[id].current == "game_admin":
    bot.send_message(id, "Создатель игры не может выйти из неё. Если вы хотите завершить игру для всех, нажмите /end_game.")
  else:
    bot.send_message(id, "Вы не в игре, вам неоткуда выходить.")

def leave_game_awaits_continue(id):
  code = users[id].game
  for player in games[code].players:
    if player.chat_id == id:
      games[code].players.remove(player)
      break
  if users[id].gender == "male":
    bot.send_message(player.chat_id, linked_name(id) + " вышел из игры.\n"
                                "Остаётся" + str(games[code].number_of_players) + " " + agree("человек", games[code].number_of_players) + ".", parse_mode = "MarkdownV2")
  else:
    bot.send_message(player.chat_id, linked_name(id) + " вышла из игры.\n"
                                "Остаётся" + str(games[code].number_of_players) + " " + agree("человек", games[code].number_of_players) + ".", parse_mode = "MarkdownV2")

def leave_game_continue(id):
  code = users[id].game
  for player in games[code].players:
    if player.chat_id == id:
      games[code].players.remove(player)
      break
  if users[id].gender == "male":
    bot.send_message(player.chat_id, linked_name(id) + " вышел из игры.\n", parse_mode = "MarkdownV2")
  else:
    bot.send_message(player.chat_id, linked_name(id) + " вышла из игры.\n", parse_mode = "MarkdownV2")

def check_words(message):
  words = re.findall(r"[\w']+", message.text)
  if len(words) == 0:
    bot.send_message(message.chat.id, "Не вижу в сообщении ни одного слова.")
  for word in words:
    check_word(message.chat.id, word.lower())
  users[message.chat.id].current = "game"

def check_word(id, word1):
  code = users[id].game
  word2 = games[users[id].game].word
  player_i = ''
  for i in range (len(games[code].players)):
    if games[code].players[i].chat_id == id:
      player_i = i
      break

  if not noun_and_normal_form(word1):
    bot.send_message(id, "'" + word1 + "': Такого слова нет. ❌")
  elif not in_word(word1, word2):
    bot.send_message(id, "'" + word1 + "': Слово не входит в '" + word2.upper() + "'. Отклонено. ❌")
  elif word1 in games[code].players[player_i].words:
    bot.send_message(id, "'" + word1 + "': Вы уже отправляли это слово. ❌")
  else:
    bot.send_message(id, "'" + word1 + "': Принято! ✅")
    games[code].players[player_i].words.append(word1)


@bot.message_handler(content_types=['text'])
def read_message(message):
  if message.chat.id not in users:
    make_user(message.chat.id, message.from_user.id)
    return
  id = message.chat.id
  if id not in users:
    make_user(id)
    return
  cur = users[id].current
  users[id].current = ""
  if cur == "word_for_game":
    get_word_for_game(id, message.text)
  elif cur == 'game_duration_own':
    get_game_duration(id, message.text)
  elif cur == "join_game":
    join_game_continue(message)
  elif cur == "game" or cur == "game_admin":
    check_words(message)
  elif cur == "get_name":
    make_user_got_name(id, message.text)
  elif cur == "new_nickname":
    got_nickname(id, message.text)
  elif cur == "awaits_game_admin":
    bot.send_message(id, "Чтобы начать игру, нажмите /start_game.")
    users[id].current = cur
  elif cur == "awaits_game":
    bot.send_message(id, "Игра начнётся, когда " + users[games[users[id].game].admin_id].name + " нажмёт /start_game.")
    users[id].current = cur
  elif cur in ["get_gender", "change_gender", "leave_game_awaits", "leave_game", "cancel_game", "see_results"]:
    bot.send_message(id, "Пожалуйста, выберите нужный вариант из предложенных.")
    users[id].current = cur
  elif cur == "reading":
    users[id].current = cur
  else:
    bot.send_message(id, "Если что-то непонятно, можно вызвать /help!")

@bot.callback_query_handler(func=lambda call: True)
def read_call(call):
  if call.message.chat.id not in users:
    return
  id = call.message.chat.id
  if id not in users:
    make_user(chat_id = call.message.chat.id)
  cur = users[id].current
  users[id].current = ""
  if cur == "game_duration":
    if call.data in ['5', '10', '15']:
      get_game_duration(id, call.data)
    elif call.data == 'own':
      users[id].current = 'game_duration_own'
      bot.send_message(id, "Oтправьте мне длительность игры в минутах.")
    elif call.data == 'change_word':
      ask_word_for_game(id)
  elif cur == "ready_to_start":
    if call.data == 'start':
      start_game_go(id)
    elif call.data == "change_duration":
      ask_game_duration(id)
  elif cur == "get_gender":
    make_user_got_gender(id, call.data)
  elif cur == "change_gender":
    got_gender(id, call.data)
  elif cur == "leave_game_awaits":
    if call.data == "yes":
      leave_game_awaits_continue(id)
    else:
      bot.send_message(id, "Выход из игры отменён.")
      users[id].current = "awaits_game"
  elif cur == "leave_game":
    if call.data == "yes":
      leave_game_continue(id)
    else:
      bot.send_message(id, "Выход из игры отменён. Можно продолжать писать слова.")
      users[id].current = "game"
  elif cur == "cancel_game":
    if call.data == "yes":
      cancel_game_continue(id)
    else:
      bot.send_message(id, "Игра не отменена. Чтобы начать её, нажмите /start_game.")
      users[id].current = "awaits_game_admin"
  elif cur == "see_results":
    if call.data in users and users[call.data].game in games:
      for player_x in games[users[call.data].game].players:
        if player_x.id == call.data:
          player = player_x
          break
      bot.send_message(id, "Результат " + player.name + ":\n" +
                           str(player.result_points) + " " + agree("балл", player.result_points) + ";\n" +
                           str(player.result_words) + " " + agree("слово", player.result_words) + ";\n из них" +
                           str(player.result_unique) + " " + agree("уникальный", player.result_unique) + ".\n" +
                           "\n" +
                           player.result_full, parse_mode = "MarkdownV2")
  elif cur == "reading":
    users[id].current = "reading"
  elif "Результат" in call.data:
    bot.send_message(id, call.data)
  else:
    users[id].current = cur

while True:
    try:
        bot.polling(none_stop=True)

    except Exception as e:
        print(e)
        time.sleep(10)