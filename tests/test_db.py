import unittest
from unittest.mock import MagicMock, patch
from DB import PharmacyDB


class TestPharmacyDB(unittest.TestCase):
    @patch('DB.MongoClient')
    def setUp(self, mock_client):
        # Set up a mock MongoDB client for testing
        self.mock_client = mock_client.return_value
        self.mock_db = self.mock_client.__getitem__.return_value
        self.mock_collection = self.mock_db.__getitem__.return_value

        # Create PharmacyDB instance with mock connection string
        self.pharmacy_db = PharmacyDB("mock_connection_string")

    def test_save_medication_data(self):
        # Prepare test data
        chat_id = 563127228
        medication_data = {
            "chat_id": chat_id,
            "name": "Aspirin",
            "expiration_date": "2025-12-31",
            "quantity": 30,
            "usage": "Pain relief",
            "limit": 5
        }

        # Call the method
        self.pharmacy_db.save_medication_data(chat_id, medication_data)

        # Assert that insert_one was called with correct data
        self.mock_collection.insert_one.assert_called_once_with(medication_data)

    def test_get_medication_quantity(self):
        # Prepare mock data
        chat_id = 563127228
        medication_name = "Aspirin"
        mock_medication = {"chat_id": chat_id, "name": medication_name, "quantity": 25}

        # Configure mock to return our test data
        self.mock_collection.find_one.return_value = mock_medication

        # Call the method
        result = self.pharmacy_db.get_medication_quantity(chat_id, medication_name)

        # Assert the correct query was made
        self.mock_collection.find_one.assert_called_once_with({"chat_id": chat_id, "name": medication_name})

        # Assert the correct result was returned
        self.assertEqual(result, "залишилося 25")

    def test_get_medication_quantity_not_found(self):
        # Configure mock to return None (medication not found)
        self.mock_collection.find_one.return_value = None

        # Call the method
        result = self.pharmacy_db.get_medication_quantity(563127228, "NonExistentMed")

        # Assert the correct result was returned
        self.assertEqual(result, "Препарат не знайдено")