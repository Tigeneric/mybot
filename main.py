from telegram import Update, InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, Location, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    ContextTypes,
    ConversationHandler,
)
import requests
import openai
import itertools
import math

RADIUS = "500"
API_KEY = ""

TOKEN = ""

openai.api_key = ""

step = 0

# Определим различные состояния диалога
COMMAND_START, LOCATION, CAFE_LIST, ANSWER = range(4)


def near_cafe(latitude, longitude) -> int:
    # URL-запрос
    URL = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude},{longitude}&radius={RADIUS}&type=cafe&key={API_KEY}"

    # Выполнение запроса
    response = requests.get(URL)
    data = response.json()

    # Предполагая, что data - это результат вашего запроса в формате JSON
    places = data.get('results', [])
    global name_to_id
    name_to_id = {place['name']: place['place_id'] for place in places}


def next_cafe(modificator) -> int:
    start_list = 0 + modificator * 4
    end_list = 4 + modificator * 4
    return list(name_to_id.keys())[start_list:end_list]


def review_cafe(user_choice) -> None:
    URL = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={user_choice}&fields=review,name,rating&key={API_KEY}"

    # Выполнение запроса
    response = requests.get(URL)
    data = response.json()
    reviews = [review['text'] for review in data.get('result', {}).get('reviews', [])]

    response_msg = (
        reviews
    )
    return response_msg


async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton("Отправить местоположение", request_location=True)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text('Пожалуйста, отправьте свое местоположение:', reply_markup=reply_markup)
    return LOCATION


async def handle_button_press(update: Update, context: CallbackContext):
    # Получение текста нажатой кнопки
    global step
    button_text = update.message.text
    if button_text == 'Назад' and step == 0:
        start
        return LOCATION
    elif button_text == 'Назад':
        step -= 1
        await buttons(update, context, step)
    elif button_text == 'Вперед':
        # Если нажата 'Кнопка 2', делайте что-то другое
        step += 1
        await buttons(update, context, step)
    else:
        await answer(update, context)


async def answer(update: Update, context: CallbackContext) -> None:
    user_choice = name_to_id[update.message.text]
    review = review_cafe(user_choice)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a pirat."},
            {"role": "user",
             "content": "What do you think about this establishment? Write in Russian. Here are the reviews:" + str(
                 review)}
        ]
    )
    await update.message.reply_text(completion.choices[0].message['content'])


async def buttons(update: Update, context: CallbackContext, step) -> None:
    labels = next_cafe(step)
    iter_labels = itertools.zip_longest(*[iter(labels)] * 2)
    keyboard = [[KeyboardButton(label) for label in pair if label] for pair in iter_labels]
    if step == 0:
        keyboard.append([KeyboardButton('Вперед')])
    elif step == math.ceil(len(name_to_id) // 4):
        keyboard.append([KeyboardButton('Назад')])
    else:
        keyboard.append([KeyboardButton('Назад'), KeyboardButton('Вперед')])
    await update.message.reply_text('тут?',
                                    reply_markup=ReplyKeyboardMarkup(keyboard,
                                                                     resize_keyboard=True,
                                                                     one_time_keyboard=True, input_field_placeholder=""
                                                                     ), )


async def location_callback(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    location = update.message.location

    response_msg = (
        f"Местоположение пользователя {user.first_name}: latitude = {location.latitude}, longitude = {location.longitude}\n\n"
    )
    global lat, lon
    lat, lon = location.latitude, location.longitude
    near_cafe(lat, lon)
    await buttons(update, context, 0)
    await update.message.reply_text(response_msg)
    return ANSWER


'''
async def cafe_list(update: Update, context: CallbackContext) -> None:
    #user = update.message.from_user
    keyboard = [[KeyboardButton(label)] for label in near_cafe(lat, lon)]
    await update.message.reply_text('Выберите одну из опций:',)
'''


def main() -> None:
    application = Application.builder().token(TOKEN).build()
    dp = application

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOCATION: [MessageHandler(filters.LOCATION, location_callback)],
            ANSWER: [MessageHandler(filters.TEXT, handle_button_press)],
            # Добавьте другие состояния и ассоциированные с ними обработчики.
        },
        # dp.add_handler(MessageHandler(filters.LOCATION, location_callback))
        # dp.add_handler(CommandHandler("cafe", cafe_list))
        # dp.add_handler(MessageHandler(filters.TEXT, answer))
        fallbacks=[],  # Здесь можно добавить обработчики для непредвиденных сообщений или команд.
    )
    application.add_handler(conversation_handler)

    # Run the bot until the user presses Ctrl-C
    dp.run_polling(allowed_updates=Update.ALL_TYPES)
    # application.idle()


if __name__ == '__main__':
    main()