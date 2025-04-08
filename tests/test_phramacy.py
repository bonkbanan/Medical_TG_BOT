import unittest
from unittest.mock import MagicMock, patch
import datetime
from PharmacyBot import PharmacyBot


class TestPharmacyBot(unittest.TestCase):
    @patch('PharmacyBot.telebot.TeleBot')
    @patch('PharmacyBot.PharmacyDB')
    def setUp(self, mock_db_class, mock_telebot_class):
        # Set up mock objects
        self.mock_bot = mock_telebot_class.return_value
        self.mock_db = mock_db_class.return_value

        # Create PharmacyBot instance with mock token and URI
        self.pharmacy_bot = PharmacyBot("mock_token", "mock_uri")

        # Create a mock message
        self.mock_message = MagicMock()
        self.mock_message.chat.id = 563127228
        self.mock_message.text = "Test message"

    def test_send_welcome(self):
        # Call the method
        self.pharmacy_bot.send_welcome(self.mock_message)

        # Assert the bot sent the correct reply
        self.mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            "Привіт, як справи? Виберіть, що ви хочете зробити:",
            reply_markup=self.pharmacy_bot.markup
        )

        # Assert user state was set correctly
        self.assertEqual(
            self.pharmacy_bot.user_data[self.mock_message.chat.id]["state"],
            self.pharmacy_bot.states["NOTHING"]
        )

    def test_add_medication(self):
        # Call the method
        self.pharmacy_bot.add_medication(self.mock_message)

        # Assert user state was set correctly
        self.assertEqual(
            self.pharmacy_bot.user_data[self.mock_message.chat.id]["state"],
            self.pharmacy_bot.states["MEDICATION_NAME"]
        )

        # Assert the bot sent the correct message
        self.mock_bot.send_message.assert_called_once_with(
            self.mock_message.chat.id,
            "Введіть назву препарату:"
        )

    def test_medication_details(self):
        # Create a mock callback query
        mock_call = MagicMock()
        mock_call.message.chat.id = 563127228
        mock_call.data = "details_Aspirin"

        # Configure mock database response
        mock_medication = {
            "_id": "mock_id",
            "chat_id": 563127228,
            "name": "Aspirin",
            "expiration_date": "2025-06-30",
            "quantity": 25,
            "usage": "Pain relief",
            "limit": 5
        }
        self.mock_db.collection.find_one.return_value = mock_medication

        # Call the method
        self.pharmacy_bot.medication_details(mock_call)

        # Assert database was queried correctly
        self.mock_db.collection.find_one.assert_called_once_with(
            {"chat_id": 563127228, "name": "Aspirin"}
        )

        # Assert the correct message was sent
        expected_message = "Назва: Aspirin\nТермін придатності: 2025-06-30\nКількість: 25\nВід чого: Pain relief\nліміт: 5\n"
        self.mock_bot.send_message.assert_called_once_with(563127228, expected_message)