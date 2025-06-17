import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.new_dashboard_subscriber import EnhancedDashboardSubscriber

def get_config():
    # load dotenv in ../.env and read the configuration
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    config = {
        'mongo': {
            'uri': os.getenv('MONGO_URI'),
            'database': os.getenv('MONGO_DATABASE', 'event_db'),
            'username': os.getenv('MONGO_USER'),
            'password': os.getenv('MONGO_PASSWORD'),
            'ttl': int(os.getenv('TTL_SECONDS', 24 * 60 * 60)) # Default to 24 hours
        }
    }
    return config


def get_event_db():
    """
    Get the MongoDB client and database for event storage.
    """
    config = get_config()

    try:
        client = MongoClient(
            config['mongo']['uri'],
            username=config['mongo']['username'],
            password=config['mongo']['password'],
            authSource=config['mongo']['database'],
            serverSelectionTimeoutMS=5000  # Timeout for server selection
        )
        # Test the connection
        client.admin.command('ping')
        db = client[config['mongo']['database']]
        return db
    except ConnectionFailure as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    except OperationFailure as e:
        raise RuntimeError(f"MongoDB operation failed: {e}")
    except Exception as e:
        raise RuntimeError(f"An unknown error occurred while connecting to MongoDB: {e}")

if __name__ == "__main__":
    try:
        db = get_event_db()
        print("Successfully connected to the event database.")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

    subscriber = EnhancedDashboardSubscriber()
    subscriber.start()