from pyqueue_client import PyQueue
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
HOST = os.getenv("HOST", "localhost")
PORT = os.getenv("PORT", "8000")
BASE_URL = f"http://{HOST}:{PORT}"
QUEUE_NAME = os.getenv("QUEUE_NAME_TEST", "test_queue")  # Development queue name
API_KEY = os.getenv("API_KEY_TEST", "pk_dev_12345")  # Development API key

notifier = PyQueue(queue_type="remote", server_url=BASE_URL, api_key=API_KEY, queue_name=QUEUE_NAME)

notifier.add_message(message={
        "message_field_1": "Message Field Value 1",
        "message_field_2": "Message Field Value 2",
})

messages = notifier.get_messages()
print(messages)

#test get message by id
message_id = messages[0]['id']
message = notifier.get_message(item_id=message_id)
print(message)

all_ids = ["5d74f678523b964d5b9f8898f96e75c0","8a319434dbc60580e8f50559c5d6801c"]
existing_ids = notifier.check_existence(all_ids)
print(existing_ids)