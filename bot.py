from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import DatabaseManager, hide_img
import schedule
import threading
import time
from config import API_TOKEN, DATABASE

bot = TeleBot(API_TOKEN)
manager = DatabaseManager(DATABASE)

# Стоимость выкупа одной картинки в бонусах
BONUS_COST = 15

def gen_markup(prize_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Получить!", callback_data=f"claim_{prize_id}"))
    return markup

def gen_shop_markup(lost_prizes):
    markup = InlineKeyboardMarkup()
    for prize_id, img_name in lost_prizes[:5]: # Показываем максимум 5 последних упущеных
        markup.add(InlineKeyboardButton(f"Купить картинку #{prize_id} за {BONUS_COST} 🪙", callback_data=f"buy_{prize_id}"))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    data = call.data

    #получение картинки на скорость
    if data.startswith("claim_"):
        prize_id = data.split("_")[1]
        
        if manager.get_winners_count(prize_id) < 3:
            res = manager.add_winner(user_id, prize_id)
            if res:
                img = manager.get_prize_img(prize_id)
                with open(f'img/{img}', 'rb') as photo:
                    bot.send_photo(user_id, photo, caption="Поздравляем! Ты успел и получил картинку! +5 бонусов! 🎉")
            else:
                bot.send_message(user_id, 'Ты уже получил эту картинку!')
        else:
            bot.send_message(user_id, "К сожалению, 3 человека уже забрали приз! Но ты можешь выкупить её в `/shop` 😉")

    #Покупка упущенной картинки за бонусы
    elif data.startswith("buy_"):
        prize_id = data.split("_")[1]
        current_points = manager.get_user_points(user_id)

        if current_points >= BONUS_COST:
            #проверка на покупку и получение
            res = manager.add_winner(user_id, prize_id)
            if res:
                manager.change_user_points(user_id, -BONUS_COST) # Списываем бонусы
                img = manager.get_prize_img(prize_id)
                with open(f'img/{img}', 'rb') as photo:
                    bot.send_photo(user_id, photo, caption=f"Успешно куплено! Списано {BONUS_COST} бонусов. Твой баланс: {current_points - BONUS_COST} 🪙")
            else:
                bot.send_message(user_id, "Эта картинка уже есть в твоей коллекции!")
        else:
            bot.send_message(user_id, f"Недостаточно бонусов! Требуется: {BONUS_COST} 🪙, у тебя: {current_points} 🪙")

def send_message():
    prize_id, img = manager.get_random_prize()[:2]
    if prize_id is None:
        return # Если картинки кончились
    
    manager.mark_prize_used(prize_id)
    hide_img(img)
    for user in manager.get_users():
        try:
            with open(f'hidden_img/{img}', 'rb') as photo:
                bot.send_photo(user, photo, reply_markup=gen_markup(prize_id))
        except Exception as e:
            print(f"Ошибка отправки пользователю {user}: {e}")
        

def schedule_thread():
    schedule.every().minute.do(send_message) 
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! 
Тебя успешно зарегистрировали! На твой счет начислено 10 приветственных бонусов 🪙.

Каждый час приходят новые заблюренные картинки. Первые 3 кликнувших получают их бесплатно.
Если не успел — не беда! Команда /shop позволит выкупить упущенное за бонусы!""")

@bot.message_handler(commands=['me'])
def handle_me(message):
    points = manager.get_user_points(message.chat.id)
    bot.reply_to(message, f"Твой баланс: {points} 🪙 бонусов.\nЗа каждую быструю победу ты получаешь +5 бонусов.")

@bot.message_handler(commands=['shop'])
def handle_shop(message):
    user_id = message.chat.id
    lost_prizes = manager.get_lost_prizes(user_id)
    
    if not lost_prizes:
        bot.send_message(user_id, "У тебя нет упущенных картинок. Ты либо всё собрал, либо новые игры ещё не проводились.")
        return
        
    points = manager.get_user_points(user_id)
    bot.send_message(
        user_id, 
        f"Твой баланс: {points} 🪙\nВыбери картинку из списка упущенных, которую хочешь открыть за {BONUS_COST} бонусов:", 
        reply_markup=gen_shop_markup(lost_prizes)
    )

@bot.message_handler(commands=['rating'])
def handle_rating(message):
    res = manager.get_rating() 
    if not res:
        bot.send_message(message.chat.id, "Рейтинг пока пуст.")
        return
    res_str = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res_str = '\n'.join(res_str)
    res_str = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res_str
    bot.send_message(message.chat.id, res_str)

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    manager.create_tables()

    t_polling = threading.Thread(target=polling_thread)
    t_schedule = threading.Thread(target=schedule_thread)

    t_polling.start()
    t_schedule.start()
