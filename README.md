# PyQueue Client

A Python library for managing message queues with **full AWS SQS-style features** for both local JSON files and remote PyQueue servers. Features include visibility timeouts, receipt handles, message tracking, and flexible consumption patterns.

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Features

### Core Features
- **Dual Mode Operation**: Seamless switch between local (file-based) and remote (HTTP API) queues
- **SQS-Style API**: Familiar AWS SQS-like interface with visibility timeouts and receipt handles
- **Full Feature Parity**: Both local and remote modes support the complete feature set
- **Visibility Timeout**: Messages become temporarily invisible after receive to prevent duplicate processing
- **Receipt Handles**: Unique tokens for safe message deletion (prevents accidental deletion)
- **Message Tracking**: Track receive count and first received timestamp for each message
- **Flexible Consumption**: Filter messages by "new only", auto-delete, or manual acknowledgment
- **Backward Compatible**: Automatically upgrades old messages to new format

### Local Queue Features
- **File-Based Storage**: Simple JSON file storage for development and testing
- **No External Dependencies**: Works offline without any server infrastructure
- **Automatic Cleanup**: Expired visibility timeouts are automatically cleaned up
- **Thread-Safe Design**: Safe concurrent access with proper file handling

### Remote Queue Features
- **HTTP REST API**: Connect to remote PyQueue servers
- **API Key Authentication**: Secure access with X-API-Key header
- **Connection Pooling**: Persistent HTTP sessions for better performance
- **Health Monitoring**: Built-in health check endpoint
- **Configurable Timeouts**: Control request timeout behavior

## Installation

```bash
pip install pyqueue-client
```

## Quick Start

### Local Queue (Development & Testing)

```python
from pyqueue_client import PyQueue

# Initialize local queue
queue = PyQueue(queue_type="local", queue_file="queue.json")

# Add a message
queue.add_message({"task": "send_email", "to": "user@example.com"})

# Receive messages with visibility timeout
messages = queue.receive_messages(max_messages=5, visibility_timeout=30)

# Process and delete
for msg in messages:
    print(f"Processing: {msg['message_body']}")
    queue.delete_message(msg['ReceiptHandle'])
```

### Remote Queue (Production)

```python
from pyqueue_client import PyQueue

# Initialize remote queue with authentication
queue = PyQueue(
    queue_type="remote",
    server_url="https://api.pyqueue.com",
    queue_name="production-tasks",
    api_key="your-api-key-here",
    timeout=30
)

# Same API as local queue!
queue.add_message({"task": "process_order", "order_id": 12345})
messages = queue.receive_messages(max_messages=10, visibility_timeout=60)
```

## Detailed Usage

### Adding Messages

```python
# Add message with auto-generated ID
queue.add_message({
    "task": "process_payment",
    "amount": 99.99,
    "currency": "USD"
})

# Add message with custom ID
queue.add_message({
    "task": "send_notification",
    "user_id": 12345
}, item_id="notification-user-12345")
```

### Receiving Messages (SQS-Style)

The `receive_messages()` method supports multiple modes:

```python
# Standard receive with visibility timeout
messages = queue.receive_messages(
    max_messages=10,           # Maximum messages to receive
    visibility_timeout=30,      # Seconds until message becomes visible again
    delete_after_receive=False, # Auto-delete after receive?
    only_new=False             # Only messages never received before?
)

# Each message has this structure:
# {
#     "Id": "message-uuid",
#     "ReceiptHandle": "receipt_xyz...",  # Use this to delete
#     "message_body": { ... },            # Your data
#     "timestamp": "2026-01-22T12:00:00",
#     "receive_count": 1,                 # How many times received
#     "first_received_at": "2026-01-22T12:00:00"
# }
```

#### Visibility Timeout Behavior

When you receive a message, it becomes **invisible** to other consumers for the specified timeout period:

```python
# Consumer 1 receives a message
messages = queue.receive_messages(visibility_timeout=60)

# Consumer 2 won't see this message for 60 seconds
# (unless Consumer 1 deletes it with delete_message())

# If Consumer 1 fails to process, message automatically
# becomes visible again after 60 seconds
```

#### Only New Messages

Filter messages that have never been received before:

```python
# Get only messages that are being received for the first time
messages = queue.receive_messages(only_new=True)

# Useful for ensuring first-time processing
# Messages with receive_count > 0 are filtered out
```

#### Auto-Delete on Receive

Automatically delete messages after receiving (no manual acknowledgment needed):

```python
messages = queue.receive_messages(
    max_messages=5,
    delete_after_receive=True
)

# Messages are immediately deleted from queue
# No need to call delete_message()
```

### Deleting Messages

```python
# Using receipt handle (recommended - SQS-style)
messages = queue.receive_messages(max_messages=1)
queue.delete_message(messages[0]['ReceiptHandle'])

# Using message ID directly (alternative)
queue.remove_message("message-uuid")
```

### Updating Messages

```python
queue.update_message("message-uuid", {
    "task": "send_email",
    "status": "updated",
    "priority": "high"
})
```

### Getting Messages (Without Visibility Changes)

```python
# Get all messages (doesn't affect visibility)
all_messages = queue.get_messages()

# Get limited number of messages
first_10 = queue.get_messages(max_messages=10)
```

### Checking Message Existence

```python
# Check single message
if queue.has_message("message-uuid"):
    print("Message exists")

# Batch check multiple messages (optimized)
existing_ids = queue.check_existence([
    "msg-1", "msg-2", "msg-3", "msg-4"
])
print(f"Found: {existing_ids}")
```

### Queue Information & Statistics

```python
info = queue.get_queue_info()
print(info)

# Local queue returns:
# {
#     "queue_type": "local",
#     "queue_file": "queue.json",
#     "message_count": 15,
#     "visible_messages": 10,      # Currently visible
#     "invisible_messages": 5,      # Hidden by visibility timeout
#     "never_received": 8,          # Messages never received
#     "total_receives": 22,         # Sum of all receive_counts
#     "file_size": 4096
# }
```

### Queue Maintenance

```python
# Clear all messages
queue.clear_queue()

# Manual cleanup of expired visibility timeouts (local only)
# Note: This happens automatically on every read operation
queue.cleanup_expired_messages()

# Health check
if queue.health_check():
    print("Queue is accessible and healthy")
```

## Consumer Pattern Example

Here's a production-ready consumer pattern:

```python
import time
import logging
from pyqueue_client import PyQueue

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize queue
queue = PyQueue(
    queue_type="remote",
    server_url="https://api.pyqueue.com",
    queue_name="tasks",
    api_key="your-api-key",
    timeout=30
)

def process_message(message_body):
    """Your business logic here"""
    print(f"Processing: {message_body}")
    # Simulate work
    time.sleep(2)
    return True

# Main consumer loop
while True:
    try:
        # Receive up to 5 messages with 60-second visibility timeout
        messages = queue.receive_messages(
            max_messages=5,
            visibility_timeout=60,
            only_new=False
        )

        if not messages:
            # No messages available, wait before polling again
            time.sleep(5)
            continue

        for msg in messages:
            try:
                # Process the message
                success = process_message(msg['message_body'])

                if success:
                    # Delete message after successful processing
                    queue.delete_message(msg['ReceiptHandle'])
                    print(f"✅ Processed message {msg['Id']}")
                else:
                    print(f"⚠️ Failed to process {msg['Id']}")
                    # Message will become visible again after timeout

            except Exception as e:
                print(f"❌ Error processing {msg['Id']}: {e}")
                # Message will become visible again for retry

    except KeyboardInterrupt:
        print("Shutting down consumer...")
        break
    except Exception as e:
        print(f"Consumer error: {e}")
        time.sleep(10)  # Wait before retrying
```

## Message Structure

### Internal Message Format (in queue)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-22T12:00:00.000000",
  "message_body": {
    "task": "send_email",
    "user_id": 12345,
    "custom_field": "any value"
  },
  "receive_count": 3,
  "first_received_at": "2026-01-22T11:00:00.000000",
  "invisible_until": "2026-01-22T12:01:00.000000",
  "current_receipt_handle": "receipt_abc123..."
}
```

### Received Message Format (after receive_messages)

```json
{
  "Id": "550e8400-e29b-41d4-a716-446655440000",
  "ReceiptHandle": "receipt_abc123...",
  "message_body": {
    "task": "send_email",
    "user_id": 12345,
    "custom_field": "any value"
  },
  "timestamp": "2026-01-22T12:00:00.000000",
  "receive_count": 3,
  "first_received_at": "2026-01-22T11:00:00.000000"
}
```

## API Reference

### Initialization

```python
PyQueue(
    queue_type="local",           # "local" or "remote"
    queue_file="queue.json",      # Local only: file path
    server_url=None,              # Remote only: server URL
    queue_name="default",         # Remote only: queue name
    api_key=None,                 # Remote only: authentication
    timeout=30                    # Remote only: request timeout
)
```

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `add_message(message, item_id=None)` | `message` (dict), `item_id` (str, optional) | `str` (message ID) | Add message to queue |
| `get_messages(max_messages=None)` | `max_messages` (int, optional) | `List[dict]` | Get messages without affecting visibility |
| `get_message(item_id)` | `item_id` (str) | `dict` or `None` | Get specific message by ID |
| `has_message(item_id)` | `item_id` (str) | `bool` | Check if message exists |
| `check_existence(item_ids)` | `item_ids` (List[str]) | `List[str]` | Batch check message existence |
| `receive_messages(...)` | See below | `List[dict]` | Receive messages SQS-style |
| `delete_message(receipt_handle)` | `receipt_handle` (str) | `bool` | Delete message via receipt handle |
| `remove_message(item_id)` | `item_id` (str) | `bool` | Delete message via ID |
| `update_message(item_id, new_message)` | `item_id` (str), `new_message` (dict) | `bool` | Update message content |
| `clear_queue()` | None | `bool` | Remove all messages |
| `get_queue_info()` | None | `dict` | Get queue statistics |
| `health_check()` | None | `bool` | Check queue accessibility |
| `cleanup_expired_messages()` | None | `bool` | Manual cleanup (local only) |

### receive_messages() Parameters

```python
receive_messages(
    max_messages=10,           # Maximum messages to receive (1-10)
    visibility_timeout=30,      # Seconds until message visible again
    delete_after_receive=False, # Auto-delete after receive?
    only_new=False             # Only never-received messages?
)
```

## Feature Comparison: Local vs Remote

| Feature | Local Queue | Remote Queue |
|---------|-------------|--------------|
| Visibility Timeout | ✅ Full support | ✅ Full support |
| Receipt Handles | ✅ Full support | ✅ Full support |
| Only New Filter | ✅ Full support | ✅ Full support |
| Receive Tracking | ✅ Full support | ✅ Full support |
| Auto-delete on Receive | ✅ Full support | ✅ Full support |
| Message Updates | ✅ Full support | ✅ Full support |
| Batch Operations | ✅ Full support | ✅ Optimized |
| API Authentication | N/A | ✅ API Key |
| Connection Pooling | N/A | ✅ Yes |
| Health Checks | ✅ File access | ✅ HTTP endpoint |
| Concurrent Access | ⚠️ File-based | ✅ Server-side |
| Performance | Fast (local I/O) | Network-dependent |
| Use Case | Dev/Testing | Production |

## Logging

PyQueue Client uses Python's standard logging module:

```python
import logging

# Basic logging
logging.basicConfig(level=logging.INFO)

# Debug mode (shows all HTTP requests, file operations, etc.)
logging.getLogger("pyqueue_client").setLevel(logging.DEBUG)

# Example output:
# INFO:pyqueue_client.queue_manager:✅ Message added: abc-123
# INFO:pyqueue_client.queue_manager:🗑 Message deleted via receipt handle: receipt_xyz
# DEBUG:pyqueue_client.remote_queue:🔗 POST http://localhost:8000/api/v1/queues/tasks/messages
```

## Configuration

### Environment Variables

- `QUEUE_FILE_PATH`: Default path for local queue file (default: `"queue.json"`)

```bash
export QUEUE_FILE_PATH="/var/data/myqueue.json"
```

```python
from pyqueue_client import PyQueue

# Will use /var/data/myqueue.json by default
queue = PyQueue(queue_type="local")
```

## Migration Guide

### Upgrading from v1.1.x to v1.2.x

Version 1.2.x adds full SQS-style features to local queues. **Your existing code will continue to work** - backward compatibility is guaranteed.

**What's New:**
- Visibility timeout support for local queues
- Receipt handles for safe message deletion
- Message tracking (receive_count, first_received_at)
- Enhanced queue statistics

**Breaking Changes:**
- None! Old messages are automatically upgraded when read.

**Recommended Changes:**

```python
# Old way (still works)
messages = queue.receive_messages(max_messages=5, delete_after_receive=True)
for msg in messages:
    process(msg)

# New way (recommended)
messages = queue.receive_messages(max_messages=5, visibility_timeout=60)
for msg in messages:
    try:
        process(msg['message_body'])
        queue.delete_message(msg['ReceiptHandle'])  # Use receipt handle
    except Exception:
        pass  # Message will retry after timeout
```

## Development & Testing

### Running Tests

```bash
# Basic local queue test
python test_local.py

# Advanced feature tests
python test_local_advanced.py

# Remote queue tests (requires server)
python test_remote.py
```

### Test Coverage

The library includes comprehensive tests:
- Basic CRUD operations
- Visibility timeout behavior
- Receipt handle validation
- Only new message filtering
- Receive count tracking
- Auto-delete functionality
- Queue statistics
- Backward compatibility

## Requirements

- Python >= 3.6
- requests >= 2.31.0
- urllib3 >= 2.0.0

## Use Cases

### Development & Testing
Use **local queues** for:
- Unit tests
- Local development
- Offline development
- Simple task queues
- Prototyping

### Production
Use **remote queues** for:
- Distributed systems
- Microservices communication
- Background job processing
- Event-driven architectures
- Scalable task processing

## Best Practices

1. **Use visibility timeouts**: Set visibility_timeout based on your processing time
2. **Always delete processed messages**: Use receipt handles for safe deletion
3. **Handle failures gracefully**: Messages auto-retry when visibility timeout expires
4. **Monitor queue statistics**: Use `get_queue_info()` for observability
5. **Use only_new for deduplication**: Ensure first-time processing when needed
6. **Enable logging in production**: Debug issues with structured logs
7. **Set appropriate timeouts**: Configure HTTP timeouts for remote queues

## Troubleshooting

### Message not being deleted
- Ensure you're using the correct `ReceiptHandle` from `receive_messages()`
- Receipt handles expire when visibility timeout expires
- Use `delete_message()` not `remove_message()` for SQS-style deletion

### Messages not becoming visible
- Check if visibility timeout has expired
- Use `get_queue_info()` to see invisible message count
- Call `cleanup_expired_messages()` for manual cleanup (local only)

### Remote connection errors
- Verify server URL is correct and accessible
- Check API key is valid
- Increase timeout parameter if network is slow
- Use `health_check()` to verify server status

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

Made with ❤️ for developers who need simple, reliable message queues
