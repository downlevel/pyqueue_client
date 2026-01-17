from pyqueue_client import PyQueue

notifier = PyQueue(queue_type="remote", server_url="http://localhost:8000", api_key="test_api_key", queue_name="test_queue")

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