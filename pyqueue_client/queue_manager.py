import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from .remote_queue import RemoteQueueClient

# Default queue file path
QUEUE_FILE = os.getenv("QUEUE_FILE_PATH", "queue.json")

class PyQueue:
    def __init__(self, queue_file=QUEUE_FILE, queue_type="local", server_url=None, api_key=None, queue_name="default", timeout=30):
        """
        Initialize PyQueue client
        
        Args:
            queue_file: Path to local queue file (used when queue_type="local")
            queue_type: "local" for file-based queue, "remote" for server-based queue
            server_url: URL of remote PyQueue server (required when queue_type="remote")
            queue_name: Name of the remote queue (used when queue_type="remote")
            timeout: Request timeout for remote operations
        """
        self.queue_type = queue_type.lower()
        self.logger = logging.getLogger(__name__)
        
        if self.queue_type == "local":
            self.queue_file = queue_file
            # Ensure queue file exists
            if not os.path.exists(self.queue_file):
                with open(self.queue_file, "w") as f:
                    json.dump([], f)
                    
        elif self.queue_type == "remote":
            if not server_url:
                raise ValueError("server_url is required when queue_type='remote'")
            self.remote_client = RemoteQueueClient(server_url, queue_name, api_key, timeout)
            
        else:
            raise ValueError("queue_type must be 'local' or 'remote'")

    # Helper methods for local queue management
    def _generate_receipt_handle(self) -> str:
        """Generate a unique receipt handle"""
        return f"receipt_{uuid.uuid4()}"

    def _is_message_visible(self, message: Dict) -> bool:
        """Check if a message is currently visible (not hidden by visibility timeout)"""
        if "invisible_until" not in message or message["invisible_until"] is None:
            return True

        invisible_until = datetime.fromisoformat(message["invisible_until"])
        return datetime.utcnow() >= invisible_until

    def _cleanup_expired_visibility(self, queue: List[Dict]) -> List[Dict]:
        """Reset visibility for messages whose timeout has expired"""
        now = datetime.utcnow()
        for message in queue:
            if "invisible_until" in message and message["invisible_until"]:
                invisible_until = datetime.fromisoformat(message["invisible_until"])
                if now >= invisible_until:
                    message["invisible_until"] = None
        return queue

    def _read_queue(self) -> List[Dict]:
        """Read queue from file with error handling and visibility cleanup"""
        try:
            with open(self.queue_file, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                queue = json.loads(content)
                # Cleanup expired visibility timeouts
                return self._cleanup_expired_visibility(queue)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_queue(self, queue: List[Dict]):
        """Write queue to file"""
        with open(self.queue_file, "w") as f:
            json.dump(queue, f, indent=4)

    def _ensure_message_fields(self, message: Dict) -> Dict:
        """Ensure message has all required tracking fields for local queue"""
        if "receive_count" not in message:
            message["receive_count"] = 0
        if "first_received_at" not in message:
            message["first_received_at"] = None
        if "invisible_until" not in message:
            message["invisible_until"] = None
        return message

    def add_message(self, message, item_id=None):
        """Adds a message to the queue"""
        if self.queue_type == "remote":
            return self.remote_client.add_message(message, item_id)

        # Local queue implementation
        item_queue = {}  # Initialize message queue
        if item_id is None:
            item_queue["id"] = message.get("id", str(uuid.uuid4()))  # Unique id
        else:
            item_queue["id"] = item_id

        item_queue["timestamp"] = datetime.utcnow().isoformat()  # Add timestamp
        item_queue["message_body"] = message

        # Add tracking fields for SQS-style behavior
        item_queue["receive_count"] = 0
        item_queue["first_received_at"] = None
        item_queue["invisible_until"] = None

        # Read existing queue
        queue = self._read_queue()

        # Check if message already exists
        if any(item["id"] == item_queue["id"] for item in queue):
            return

        queue.append(item_queue)  # Add new message

        # Write back to queue
        self._write_queue(queue)

        self.logger.info(f"✅ Message added: {item_queue['id']}")

    def get_messages(self, max_messages: int = None):
        """
        Returns messages from the queue

        Args:
            max_messages: Maximum number of messages to return (None = all messages)
        """
        if self.queue_type == "remote":
            # Remote client expects max_messages parameter
            if max_messages is not None:
                return self.remote_client.get_messages(max_messages)
            else:
                return self.remote_client.get_messages(10)  # Default for remote

        # Local queue implementation - return all messages (including invisible ones)
        queue = self._read_queue()

        # Ensure backward compatibility with old messages
        for message in queue:
            self._ensure_message_fields(message)

        # Apply max_messages limit if specified
        if max_messages is not None:
            return queue[:max_messages]

        return queue

    def get_message(self, item_id):
        """Returns a specific message by ID if it exists, otherwise None"""
        # Get all messages (works for both local and remote)
        messages = self.get_messages()
        
        # Find the specific message
        for item in messages:
            if item.get("id") == item_id:
                return item
        return None

    def has_message(self, item_id):
        """Checks if a message exists in the queue"""
        return self.get_message(item_id) is not None
    
    def check_existence(self, item_ids: List[str]) -> List[str]:
        """Check which messages from the list exist in the queue"""
        if self.queue_type == "remote":
            return self.remote_client.check_existence(item_ids)
        
        # Local queue implementation
        existing_ids = []
        messages = self.get_messages()
        message_ids_set = {item["id"] for item in messages}
        
        for item_id in item_ids:
            if item_id in message_ids_set:
                existing_ids.append(item_id)
        
        return existing_ids
    
    def receive_messages(self, max_messages=10, visibility_timeout=30, delete_after_receive=False, only_new=False):
        """
        Receive messages from the queue (SQS-style)
        For remote queues, messages become temporarily invisible or are deleted immediately.
        For local queues, implements full SQS-style behavior with visibility timeout and receipt handles.
        """
        if self.queue_type == "remote":
            return self.remote_client.receive_messages(max_messages, visibility_timeout, delete_after_receive, only_new)

        # Local queue implementation with full SQS-style behavior
        queue = self._read_queue()
        now = datetime.utcnow()

        # Filter visible messages
        visible_messages = []
        for message in queue:
            self._ensure_message_fields(message)
            if self._is_message_visible(message):
                # Apply only_new filter if requested
                if only_new and message["first_received_at"] is not None:
                    continue
                visible_messages.append(message)

        # Select messages up to max_messages
        selected_messages = visible_messages[:max_messages]

        # Process selected messages
        received_messages = []
        messages_to_delete = []

        for message in selected_messages:
            # Update tracking fields
            message["receive_count"] += 1
            if message["first_received_at"] is None:
                message["first_received_at"] = now.isoformat()

            # Generate receipt handle
            receipt_handle = self._generate_receipt_handle()
            message["current_receipt_handle"] = receipt_handle

            if delete_after_receive:
                # Mark for deletion
                messages_to_delete.append(message["id"])
            else:
                # Set visibility timeout
                message["invisible_until"] = (now + timedelta(seconds=visibility_timeout)).isoformat()

            # Prepare response message (SQS-style format)
            response_message = {
                "Id": message["id"],
                "ReceiptHandle": receipt_handle,
                "message_body": message["message_body"],
                "timestamp": message["timestamp"],
                "receive_count": message["receive_count"],
                "first_received_at": message["first_received_at"]
            }
            received_messages.append(response_message)

        # Delete messages if requested
        if delete_after_receive and messages_to_delete:
            queue = [msg for msg in queue if msg["id"] not in messages_to_delete]
            self.logger.info(f"🗑 Deleted {len(messages_to_delete)} message(s) after receive")

        # Save updated queue
        self._write_queue(queue)

        return received_messages

    def clear_queue(self):
        """Clears the queue"""
        if self.queue_type == "remote":
            return self.remote_client.clear_queue()

        # Local queue implementation
        self._write_queue([])
        self.logger.info("🚀 Queue cleared!")
        return True

    def remove_message(self, item_id):
        """Removes a message from the queue by ID"""
        if self.queue_type == "remote":
            return self.remote_client.remove_message(item_id)

        # Local queue implementation
        queue = self._read_queue()
        original_count = len(queue)
        new_queue = [item for item in queue if item["id"] != item_id]

        if len(new_queue) == original_count:
            self.logger.warning(f"⚠️ Message not found: {item_id}")
            return False

        self._write_queue(new_queue)
        self.logger.info(f"🗑 Message removed: {item_id}")
        return True

    def update_message(self, item_id, new_message):
        """Updates a message in the queue"""
        if self.queue_type == "remote":
            return self.remote_client.update_message(item_id, new_message)

        # Local queue implementation
        queue = self._read_queue()
        message_found = False

        for item in queue:
            if item["id"] == item_id:
                item["timestamp"] = datetime.utcnow().isoformat()
                item["message_body"] = new_message
                message_found = True
                break

        if not message_found:
            self.logger.warning(f"⚠️ Message not found for update: {item_id}")
            return False

        self._write_queue(queue)
        self.logger.info(f"🔄 Message updated: {item_id}")
        return True
    
    def delete_message(self, receipt_handle: str):
        """
        Delete a message using receipt handle (SQS-style)
        For local queues, validates the receipt handle before deleting
        """
        if self.queue_type == "remote":
            return self.remote_client.delete_message(receipt_handle)

        # Local queue implementation - find message by receipt handle
        queue = self._read_queue()
        message_to_delete = None

        for message in queue:
            if message.get("current_receipt_handle") == receipt_handle:
                message_to_delete = message
                break

        if message_to_delete is None:
            self.logger.warning(f"⚠️ Receipt handle not found or expired: {receipt_handle}")
            return False

        # Remove the message
        queue = [msg for msg in queue if msg["id"] != message_to_delete["id"]]
        self._write_queue(queue)
        self.logger.info(f"🗑 Message deleted via receipt handle: {message_to_delete['id']}")
        return True
    
    def get_queue_info(self):
        """Get information about the queue"""
        if self.queue_type == "remote":
            return self.remote_client.get_queue_info()

        # Local queue implementation
        try:
            messages = self.get_messages()
            visible_count = sum(1 for msg in messages if self._is_message_visible(msg))
            invisible_count = len(messages) - visible_count

            # Calculate statistics
            total_receives = sum(msg.get("receive_count", 0) for msg in messages)
            never_received = sum(1 for msg in messages if msg.get("receive_count", 0) == 0)

            return {
                "queue_type": "local",
                "queue_file": self.queue_file,
                "message_count": len(messages),
                "visible_messages": visible_count,
                "invisible_messages": invisible_count,
                "never_received": never_received,
                "total_receives": total_receives,
                "file_size": os.path.getsize(self.queue_file) if os.path.exists(self.queue_file) else 0
            }
        except Exception as e:
            return {
                "queue_type": "local",
                "queue_file": self.queue_file,
                "error": str(e)
            }
    
    def health_check(self):
        """Check if the queue is accessible"""
        if self.queue_type == "remote":
            return self.remote_client.health_check()

        # Local queue implementation - check if file is accessible
        try:
            with open(self.queue_file, "r") as f:
                json.load(f)
            return True
        except:
            return False

    def cleanup_expired_messages(self):
        """
        Manually trigger cleanup of expired visibility timeouts.
        This is called automatically on every read operation, but can be called manually if needed.
        Only applicable to local queues.
        """
        if self.queue_type == "remote":
            self.logger.warning("cleanup_expired_messages is not applicable to remote queues")
            return False

        # Read queue (which automatically cleans up expired visibility)
        queue = self._read_queue()
        self._write_queue(queue)
        self.logger.info("🧹 Expired visibility timeouts cleaned up")
        return True
