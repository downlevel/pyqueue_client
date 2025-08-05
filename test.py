from pyqueue_client import PyQueue

notifier = PyQueue(queue_file="queue.json")

notifier.add_message(message={
        "message_field_1": "Message Field Value 1",
        "message_field_2": "Message Field Value 2",
})

messages = notifier.get_messages()
print(messages)