# PyQueue Client

A Python library for adding messages to PyQueue with support for both local JSON files and remote PyQueue servers. The client now provides structured logging and advanced receive options such as deleting messages on receipt and fetching only unseen items.

## Installation

```sh
pip install pyqueue-client
```

## Usage

### Local Queue (JSON File)

```python
from pyqueue_client import PyQueue

# Initialize local queue
notifier = PyQueue(queue_type="local", queue_file="queue.json")

# Add message with auto-generated ID
notifier.add_message({
    "message_field_1": "Message Field Value 1",
    "message_field_2": "Message Field Value 2",
})

# Add message with custom ID
notifier.add_message({
    "message_field_1": "Another Message",
    "message_field_2": "Another Value",
}, item_id="custom-message-id-123")

# Retrieve all messages
messages = notifier.get_messages()
print(messages)

# Update a message
notifier.update_message("custom-message-id-123", {
    "message_field_1": "Updated Message",
    "status": "processed"
})

# Remove a message
notifier.remove_message("custom-message-id-123")

# Clear all messages
notifier.clear_queue()
```

### Remote Queue (PyQueue Server)

```python
from pyqueue_client import PyQueue

# Initialize remote queue client (without authentication)
notifier = PyQueue(
    queue_type="remote",
    server_url="http://localhost:8000",
    queue_name="my-queue",
    timeout=30
)

# Initialize remote queue client with API key authentication
notifier = PyQueue(
    queue_type="remote",
    server_url="https://api.pyqueue.com",
    queue_name="my-queue",
    api_key="your-api-key-here",
    timeout=30
)

# Add message to remote queue
notifier.add_message({
    "user_id": 12345,
    "action": "send_email",
    "email": "user@example.com",
    "template": "welcome"
})

# Receive messages (SQS-style with visibility timeout)
messages = notifier.receive_messages(
    max_messages=10,
    visibility_timeout=30,
    delete_after_receive=False,
    only_new=False,
)
for message in messages:
    # Process message
    print(f"Processing message: {message['Id']}")
    
    # Delete message after processing (using receipt handle)
    notifier.delete_message(message['ReceiptHandle'])

# Get queue information
queue_info = notifier.get_queue_info()
print(f"Queue has {queue_info['message_count']} messages")

# Health check
if notifier.health_check():
    print("Remote server is healthy")
```

### Consumer Pattern

```python
import time
from pyqueue_client import PyQueue

# Consumer for processing messages (with API key)
consumer = PyQueue(
    queue_type="remote",
    server_url="https://api.pyqueue.com",
    queue_name="task-queue",
    api_key="your-api-key-here"
)

def process_message(message):
    """Process a single message"""
    print(f"Processing: {message['message_body']}")
    # Your processing logic here
    time.sleep(1)  # Simulate work
    return True

# Main consumer loop
while True:
    try:
        # Receive messages with visibility timeout
        messages = consumer.receive_messages(max_messages=5, visibility_timeout=60)
        
        for message in messages:
            try:
                # Process the message
                if process_message(message):
                    # Delete message after successful processing (explicit delete)
                    consumer.delete_message(message['ReceiptHandle'])
                    print(f"✅ Message {message['Id']} processed successfully")
                else:
                    print(f"❌ Failed to process message {message['Id']}")
                    
            except Exception as e:
                print(f"Error processing message {message['Id']}: {e}")
        
        if not messages:
            # No messages available, wait before polling again
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("Consumer stopped")
        break
    except Exception as e:
        print(f"Consumer error: {e}")
        time.sleep(10)  # Wait before retrying
    ```

    ```python
# Alternative: automatically delete messages as they are received
messages = consumer.receive_messages(
    max_messages=5,
    visibility_timeout=60,
    delete_after_receive=True,
    only_new=True,
)

    # Note: only_new applies to remote queues. For local queues the flag is ignored.
```

### Logging

The client uses the standard `logging` module. Enable the desired level in your application:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyqueue_client").setLevel(logging.DEBUG)
```
```

## ✨ Features

### 🔄 Queue Management
- **Local & Remote Queues** - Support for both JSON file storage and remote PyQueue servers
- **Add Messages** - Easily add structured messages to queues
- **Retrieve Messages** - Get messages from queues for processing
- **SQS-like API** - Familiar receive/delete pattern with visibility timeouts
- **Message Updates** - Update existing messages in the queue
- **Queue Operations** - Clear, remove, and manage queue contents

### 🌐 Remote Server Support
- **HTTP API** - RESTful API for remote queue operations
- **Connection Management** - Automatic session handling and error recovery
- **Health Checks** - Monitor server availability
- **Configurable Timeouts** - Control request timeouts for reliability
- **Multiple Queues** - Support for named queues on the same server
- **Receive Filters** - `delete_after_receive` and `only_new` controls for flexible consumption

### 🛠️ Developer Experience
- **Simple API** - Intuitive interface for quick integration
- **Unified Interface** - Same API for both local and remote queues
- **JSON Format** - Standard JSON structure for easy data handling
- **Flexible Schema** - Support for custom message fields and structures
- **Lightweight** - Minimal dependencies for fast installation and usage
- **Type Hints** - Full type annotation support for better IDE experience

### 📊 Data Structure
- **Unique IDs** - Each message gets a unique identifier for tracking
- **Timestamps** - Automatic timestamp generation for message ordering
- **Receipt Handles** - SQS-style receipt handles for message processing
- **Custom Fields** - Add any custom data fields to your message body
- **Type Safety** - Structured data format ensures consistency

## API Reference

### Initialization

```python
# Local queue
PyQueue(queue_type="local", queue_file="queue.json")

# Remote queue (without authentication)
PyQueue(
    queue_type="remote", 
    server_url="http://localhost:8000",
    queue_name="default",
    timeout=30
)

# Remote queue (with API key authentication)
PyQueue(
    queue_type="remote", 
    server_url="https://api.pyqueue.com",
    queue_name="default",
    api_key="your-api-key-here",
    timeout=30
)
```

### Methods

- `add_message(message, item_id=None)` - Add a message to the queue
- `get_messages()` - Get all messages from the queue
- `receive_messages(max_messages=10, visibility_timeout=30, delete_after_receive=False, only_new=False)` - Receive messages (SQS-style) with optional auto-delete and unseen filters
- `delete_message(receipt_handle)` - Delete a message using receipt handle
- `remove_message(item_id)` - Remove a message by ID
- `update_message(item_id, new_message)` - Update an existing message
- `clear_queue()` - Remove all messages from the queue
- `get_queue_info()` - Get queue statistics and information
- `health_check()` - Check if the queue is accessible

## Requirements

- Python >= 3.6
- requests >= 2.25.0
- urllib3 >= 1.26.0

## License

MIT License
