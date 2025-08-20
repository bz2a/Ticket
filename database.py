from pymongo import MongoClient

# This class will manage the database connection.
class Database:
    def __init__(self, uri):
        try:
            # Establish a connection to the MongoDB server
            self.client = MongoClient(uri)
            # Select your database (e.g., "TicketBotDB")
            self.db = self.client["TicketBotDB"]
            # Select your collection for tickets (e.g., "tickets")
            self.tickets = self.db["tickets"]
            print("Successfully connected to MongoDB!")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None
            self.tickets = None

# We can create a single instance of the database to be imported by other files.
# The actual URI will be passed from the main bot file.
db_instance = None

def setup_database(uri):
    global db_instance
    db_instance = Database(uri)