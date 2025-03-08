from pymongo import MongoClient

class PharmacyDB:
    def __init__(self, uri):
        self.client = MongoClient(uri)
        self.db = self.client["Medicaments"]
        self.collection = self.db["PharmacyDB"]
        self.ping_db()


    def save_medication_data(self, chat_id, medication_data):
        self.collection.insert_one(medication_data)

    def get_medication_quantity(self, chat_id, medication_name):
        # Find the medication in the database
        medication = self.collection.find_one({"chat_id": chat_id, "name": medication_name})
        if medication:
            quantity = medication.get("quantity", 0)
            return f"залишилося {quantity}"
        else:
            return "Препарат не знайдено"

    #Ping database
    def ping_db(self):
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)