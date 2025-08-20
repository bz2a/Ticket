from pymongo import MongoClient


class Database:
    def __init__(self, uri):
        try:
            
            self.client = MongoClient(uri)
            
            self.db = self.client["TicketBotDB"]
            
            self.tickets = self.db["tickets"]
            print("Successfully connected to MongoDB!")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None
            self.tickets = None

db_instance = None

def setup_database(uri):
    global db_instance
    db_instance = Database(uri)