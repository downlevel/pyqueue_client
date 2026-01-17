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
message_id = messages['messages'][0]['id']
message = notifier.get_message_by_id(message_id=message_id)
print(message)