import datetime
import telebot
import os
from telebot import types
from DB import PharmacyDB
from datetime import datetime

class PharmacyBot:
    def __init__(self, token, uri):
        self.tb = telebot.TeleBot(token)
        self.db = PharmacyDB(uri)
        self.user_data = {}
        self.refill = False
        self.states = {
            "MEDICATION_NAME": "medication_name",
            "EXPIRATION_DATE": "expiration_date",
            "QUANTITY": "quantity",
            "USAGE": "usage",
            "NOTHING": "nothing",
            "USING": "using",
            "REFILL": "refill",
            "SEARCHING": "searching",
            "LIMIT": "limit"
        }
        self.array = [self.states["MEDICATION_NAME"], self.states["EXPIRATION_DATE"], self.states["QUANTITY"],
                      self.states["USAGE"], self.states["LIMIT"], self.states["NOTHING"]]
        self.markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        itembtnAdd = types.KeyboardButton('Додати нові ліки')
        itembtnUse = types.KeyboardButton('Використати ліки')
        itembtnFind = types.KeyboardButton('Пошук в аптечці')
        itembtnRefill = types.KeyboardButton('Поповнити аптечку')
        itembtnUseless = types.KeyboardButton('Просрочка або недостача')
        self.markup.row(itembtnAdd, itembtnUse, itembtnFind)
        self.markup.row(itembtnRefill, itembtnUseless)
        self.start_bot()

    def send_welcome(self, message):
        self.tb.reply_to(message, "Привіт, як справи? Виберіть, що ви хочете зробити:", reply_markup=self.markup)
        self.user_data[message.chat.id] = {"state": self.states["NOTHING"]} #reply on start

    def send_help(self, message):
        self.tb.reply_to(message, "Привіт, я твій телеграм бот з обліку медикаментів.\n"
                                  "Внизу є кнопки якими ти можеж користуватися, те що пише на кнопці - "
                                  "це воно й означає. Попробуй - тут все інтуїтивно просто", reply_markup=self.markup)
        self.user_data[message.chat.id] = {"state": self.states["NOTHING"]} #reply on start

    def add_medication(self, message):
        self.user_data[message.chat.id] = {"state": self.states["MEDICATION_NAME"]}
        self.tb.send_message(message.chat.id, "Введіть назву препарату:")       #Asking for new medicament name

    def adding_new_medicament(self, message):               #asking all info about medicaments
        chat_id = message.chat.id
        state = self.user_data.get(chat_id, {}).get("state")
        if state == self.states["MEDICATION_NAME"]:
            self.user_data[chat_id]["medication"] = message.text
            self.user_data[chat_id]["state"] = self.states["EXPIRATION_DATE"]
            self.tb.send_message(chat_id,
                                 f"Введіть коли вичерпується термін придатності {message.text} (Рік-Місяць-День):")
        elif state == self.states["EXPIRATION_DATE"]:
            # Split the text into parts using hyphen as separator
            parts = message.text.split('-')
            valid_day = 0
            min_date = datetime(2020, 1, 1)

            if len(parts) == 3:
                # Check if each part is composed of digits
                if all(part.isdigit() for part in parts):
                    # Check the format of the date
                    year, month, day = map(int, parts)
                    if len(parts[0]) == 4 and 1 <= int(parts[1]) <= 12 and 1 <= int(parts[2]) <= 31:
                        # Check if the number of days is valid for the month
                        if month in [1, 3, 5, 7, 8, 10, 12]:
                            valid_day = 31
                        elif month in [4, 6, 9, 11]:
                            valid_day = 30
                        elif month == 2:
                            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                                valid_day = 29
                            else:
                                valid_day = 28
                        # Check if the day is within the valid range
                        if day <= valid_day:
                            # Check if the entered date is later than January 1, 2020
                            entered_date = datetime(year, month, day)
                            if entered_date > min_date:
                                self.user_data[chat_id]["expiration_date"] = message.text
                                self.user_data[chat_id]["state"] = self.states["QUANTITY"]
                                if self.refill:
                                    self.tb.send_message(chat_id,
                                                         f"У вас його {self.db.get_medication_quantity(chat_id, self.user_data[chat_id]['medication'])}. Введіть скільки таблеток  {self.user_data[chat_id]['medication']} ви хочете добавити до того що вже є:")
                                else:
                                    self.tb.send_message(chat_id,
                                                         f"Введіть кількість {self.user_data[chat_id]['medication']}:")
                            else:
                                self.tb.send_message(chat_id, "Введена дата повинна бути пізніше 2020-01-01")
                        else:
                            self.tb.send_message(chat_id, "Неправильний день місяця, повторіть:")
                    else:
                        self.tb.send_message(chat_id, "Будь ласка, введіть правильну дату (Рік-Місяць-День):")
                else:
                    self.tb.send_message(chat_id, "Використовуйте, будь ласка, цифри (Рік-Місяць-День):")
            else:
                self.tb.send_message(chat_id, "Дата повинна бути у форматі (Рік-Місяць-День)")
        elif state == self.states["QUANTITY"]:
            if message.text.isdigit():
                self.user_data[chat_id]["quantity"] = int(message.text)
                self.user_data[chat_id]["state"] = self.states["USAGE"]
                if not self.refill:
                    self.tb.send_message(chat_id,
                                         f"Від чого цей препарат {self.user_data[chat_id]['medication']}:")
                else:

                    medication = self.db.collection.find_one({"chat_id": chat_id,"name": self.user_data[chat_id][
                             "medication"]})  # Use previously selected medication_name
                    self.db.collection.update_one({"_id": medication["_id"]}, {
                        "$set": {"expiration_date": self.user_data[chat_id]["expiration_date"],
                                 "quantity": self.user_data[chat_id]["quantity"] + medication["quantity"]}})
                    self.refill = False
                    self.tb.send_message(chat_id, "Данні про препарат оновлено!", reply_markup=self.markup)
                    self.user_data[chat_id]["state"] = self.states["NOTHING"]
            else:
                self.tb.send_message(chat_id, "Введіть будь-ласку правильну quantity (integer):")
        elif state == self.states["USAGE"]:
            self.user_data[chat_id]["usage"] = message.text
            if not self.refill:
                self.user_data[chat_id]["state"] = self.states["LIMIT"]
                self.tb.send_message(chat_id, "Введіть мінімальну кількості таблеток, "
                                              "це для нагадування при закінченні препарату:")

        elif state == self.states["LIMIT"]:
            self.user_data[chat_id]["limit"] = int(message.text)
            self.user_data[chat_id]["state"] = self.states["NOTHING"]
            self.db.save_medication_data(chat_id, {
                "chat_id": chat_id,
                "name": self.user_data[chat_id]["medication"],
                "expiration_date": self.user_data[chat_id]["expiration_date"],
                "quantity": self.user_data[chat_id]["quantity"],
                "usage": self.user_data[chat_id]["usage"],
                "limit": self.user_data[chat_id]["limit"]
            })
            self.tb.send_message(chat_id, "Данні про препарат збережено!", reply_markup=self.markup)

        elif state == self.states["NOTHING"]:
            self.tb.send_message(chat_id, "Вибачте, виберіть що ви хочете зробити з клавіатури")

    def search_use_medications(self, message):
        chat_id = message.chat.id           #write all usages
        if message.text == "Пошук в аптечці":
            self.user_data[message.chat.id] = {"state": self.states["SEARCHING"]}
        elif message.text == "Використати ліки":
            self.user_data[message.chat.id] = {"state": self.states["USING"]}
        elif message.text == "Поповнити аптечку":
            self.user_data[message.chat.id] = {"state": self.states["REFILL"]}
        query = {"chat_id": chat_id}
        sort_query = {"usages": -1}  # 1 for ascending, -1 for descending
        usages = list(set([med["usage"] for med in self.db.collection.find(query).sort(sort_query)]))
        if usages:
            buttons = None
            keyboard = types.InlineKeyboardMarkup()
            if self.user_data.get(chat_id, {}).get("state") == self.states["SEARCHING"]:
                buttons = [types.InlineKeyboardButton(text=usage, callback_data=f"search_{usage}") for usage in usages]
            elif self.user_data.get(chat_id, {}).get("state") == self.states["USING"]:
                buttons = [types.InlineKeyboardButton(text=usage, callback_data=f"use_{usage}") for usage in usages]
            elif self.user_data.get(chat_id, {}).get("state") == self.states["REFILL"]:
                buttons = [types.InlineKeyboardButton(text=usage, callback_data=f"refill_{usage}") for usage in usages]

            keyboard.add(*buttons)
            self.tb.send_message(chat_id, "Оберіть категорію:", reply_markup=keyboard)
        else:
            self.tb.send_message(chat_id, "Ваша аптечка пуста")

    def start_polling(self):
        self.tb.infinity_polling(none_stop=True)

    def handle_usage_choice(self, call):
        chat_id = call.message.chat.id          #after chosing the usage - write all medicaments with this usages
        usage = call.data.split('_')[1]
        if usage:
            query = {"chat_id": chat_id, "usage": usage}
        else:
            query = {"chat_id": chat_id}

        sort_query = {"name": -1}  # 1 for ascending, -1 for descending
        medications = list(self.db.collection.find(query).sort(sort_query))

        if len(medications) > 0:
            buttons = None
            if self.user_data.get(chat_id, {}).get("state") == self.states["SEARCHING"]:
                buttons = [types.InlineKeyboardButton(text=med["name"], callback_data="details_" + med["name"]) for med
                           in medications]
            elif self.user_data.get(chat_id, {}).get("state") == self.states["REFILL"]:
                buttons = [types.InlineKeyboardButton(text=med["name"], callback_data="refillAdd_" + med["name"]) for
                           med in medications]
            elif self.user_data.get(chat_id, {}).get("state") == self.states["USING"]:
                buttons = [types.InlineKeyboardButton(text=med["name"], callback_data="changeAmount_" + med["name"]) for
                           med in medications]
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(*buttons)
            self.tb.send_message(chat_id, f"Всі ваші препарати по категорії: {usage}", reply_markup=keyboard)
        else:
            message = f"Не знайдено препаратів для категорії '{usage}'" if usage else "В вашій аптечці ще немає препаратів."
            self.tb.send_message(chat_id, message)

    def medication_details(self, call):
        chat_id = call.message.chat.id              #wrote info about this medicament
        medication_name = call.data.split('_')[1]
        changing = {"name": "Назва", "expiration_date": "Термін придатності", "quantity": "Кількість",
                    "usage": "Від чого", "limit": "ліміт"}
        medication = self.db.collection.find_one({"chat_id": chat_id, "name": medication_name})

        if medication:
            message = ""
            for key, value in medication.items():
                if key != '_id' and key != 'chat_id':
                    message += changing[key] + f": {value}\n"
            self.tb.send_message(chat_id, message)
        else:
            self.tb.send_message(chat_id, "Препарат не найдено")

    def medication_change_amount(self, call):
        chat_id = call.message.chat.id                  #function after using "using medicamnt" where asking how many you use
        medication_name = call.data.split('_')[1]  # Extract medication name from callback data

        # Call the method from PharmacyDB class
        medication = self.db.collection.find_one({"chat_id": chat_id, "name": medication_name})
        if medication:
            message = f"Ви вибрали {medication_name}. Його лишилося {medication['quantity']}. Введіть скільки ви використали:"
            self.tb.send_message(chat_id, message)

            self.user_data[chat_id]["medication"] = medication_name
        else:
            self.tb.send_message(chat_id, "Препарат не знайдено")

    def updatating_date(self, call):
        chat_id = call.message.chat.id              #asking for new expiration date
        medication_name = call.data.split('_')[1]
        self.user_data[chat_id]["state"] = self.states["EXPIRATION_DATE"]
        self.user_data[chat_id]["medication"] = call.data.split('_')[1]
        self.refill = True

        self.tb.send_message(chat_id,
                             "Ви вибрали " + medication_name + "\n Введіть коли вичерпується термін придатності (Рік-Місяць-День):")

    def update_medication_quantity(self, message):
        chat_id = message.chat.id
        used_amount = int(message.text)             #asking for new quantity and update in db
        medication = self.db.collection.find_one(
            {"chat_id": chat_id, "name": self.user_data[chat_id]["medication"]})
        if medication:
            text = ""
            if medication['quantity'] != 0:
                new_quantity = medication['quantity'] - used_amount
                if new_quantity < 0:
                    text = ("Ви використали більше чим мали в аптечці, можливо вам хтось ще додав"
                            ", тому у вас не лишилося цих таблеток\n")
                    new_quantity = 0
                self.user_data[chat_id] = {"state": self.states["NOTHING"]}
                self.db.collection.update_one({"_id": medication["_id"]}, {"$set": {"quantity": new_quantity}})
                self.tb.send_message(chat_id, text + "Данні про препарат оновлено. Тепер його " + str(new_quantity),
                                     reply_markup=self.markup)

                if new_quantity <= medication['limit']:
                    self.tb.send_message(chat_id,
                    "Зверніть увагу, кількість цього препарату перейшла мінімальну межу, бажано докупити його ")

    def handle_useless_items(self, message):
        chat_id = message.chat.id
                                        #write about bad medicament
        # Find expired medications (expiration date in the past)
        today = datetime.now()  # Import datetime for current date comparison
        expired_medications = list(self.db.collection.find({
            "chat_id": chat_id,
            "$expr": {"$lte": [{"$dateFromString": {"dateString": "$expiration_date", "format": "%Y-%m-%d"}}, today]}
        }))

        # Find medications with quantity below the limit
        low_quantity_medications = list(self.db.collection.find({
            "chat_id": chat_id,
            "$expr": {"$lte": ["$quantity", "$limit"]}
        }))

        # Prepare messages and inline buttons
        expired_message = ""
        if len(expired_medications) > 0:
            expired_buttons = [types.InlineKeyboardButton(text=med["name"], callback_data="details_" + med["name"]) for
                               med in expired_medications]
            expired_keyboard = types.InlineKeyboardMarkup()
            expired_keyboard.add(*expired_buttons)
            expired_message = "Прострочені препарати:\n"
            self.tb.send_message(chat_id, expired_message, reply_markup=expired_keyboard)

        low_quantity_message = ""
        if len(low_quantity_medications) > 0:
            low_quantity_buttons = [types.InlineKeyboardButton(text=med["name"], callback_data="details_" + med["name"])
                                    for med in low_quantity_medications]
            low_quantity_keyboard = types.InlineKeyboardMarkup()
            low_quantity_keyboard.add(*low_quantity_buttons)
            low_quantity_message = "Препарати з недостатньою кількістю (нижче встановленого мінімуму):\n"
            self.tb.send_message(chat_id, low_quantity_message, reply_markup=low_quantity_keyboard)

        if expired_message == "" and low_quantity_message == "":
            self.tb.send_message(chat_id, "В аптечці немає прострочених або препаратів з недостатньою кількістю.")

    #handler for all messages
    def start_bot(self):
        self.tb.message_handler(commands=['start'])(self.send_welcome)
        self.tb.message_handler(commands=['help'])(self.send_help)
        self.tb.message_handler(func=lambda message: message.text == 'Додати нові ліки')(self.add_medication)

        self.tb.message_handler(func=lambda message: message.text == 'Пошук в аптечці'
            or message.text == 'Використати ліки' or message.text == 'Поповнити аптечку')(self.search_use_medications)

        self.tb.message_handler(func=lambda message: message.text == 'Просрочка або недостача')(
            self.handle_useless_items)

        self.tb.message_handler(
            func=lambda message: True and (self.user_data.get(message.chat.id, {}).get("state") in self.array))(
            self.adding_new_medicament)

        self.tb.callback_query_handler(func=lambda call: (call.data.startswith('search_')
                or call.data.startswith('refill_') or call.data.startswith('use_')))(self.handle_usage_choice)

        self.tb.callback_query_handler(func=lambda call: call.data.startswith('details_'))(self.medication_details)

        self.tb.callback_query_handler(func=lambda call: call.data.startswith('refillAdd_'))(self.updatating_date)

        self.tb.message_handler(
            func=lambda message: message.content_type == 'text' and (self.user_data.get(message.chat.id, {}).get(
                "state") == self.states["EXPIRATION_DATE"] or self.user_data.get(message.chat.id, {}).get(
                "state") == self.states["USING"]))(self.update_medication_quantity)

        self.tb.callback_query_handler(func=lambda call: call.data.startswith('changeAmount_'))(
            self.medication_change_amount)


if __name__ == "__main__":
    token = os.environ.get('TELEGRAM_TOKEN')
    uri = os.environ.get('BD_TOKEN')
    bot = PharmacyBot(token, uri)
    bot.start_polling()
