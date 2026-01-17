import json
import logging
import os
import uuid
from datetime import datetime
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

        # Read existing queue with error handling
        try:
            with open(self.queue_file, "r") as f:
                content = f.read().strip()
                if not content:  # Handle empty file
                    queue = []
                else:
                    queue = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            queue = []  # Initialize empty queue on error

        # Check if message already exists
        item_id = item_queue["id"]
        if any(item["id"] == item_id for item in queue):
            return

        item_queue["message_body"] = message  
        queue.append(item_queue)  # Add new message

        # Write back to queue
        with open(self.queue_file, "w") as f:
            json.dump(queue, f, indent=4)

        self.logger.info(f"✅ Message added: {item_queue['id']}")

    def get_messages(self):
        """Returns all messages from the queue"""
        if self.queue_type == "remote":
            return self.remote_client.get_messages()
            
        # Local queue implementation
        with open(self.queue_file, "r") as f:
            return json.load(f)

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
    
    def receive_messages(self, max_messages=10, visibility_timeout=30, delete_after_receive=False, only_new=False):
        """
        Receive messages from the queue (SQS-style)
        For remote queues, messages become temporarily invisible or are deleted immediately.
        For local queues, optionally delete the messages after reading.
        The only_new flag is only supported for remote queues.
        """
        if self.queue_type == "remote":
            return self.remote_client.receive_messages(max_messages, visibility_timeout, delete_after_receive, only_new)
            
        # Local queue implementation
        if only_new:
            self.logger.warning("only_new flag is not supported for local queues; returning all messages.")
        messages = self.get_messages()
        selected_messages = messages[:max_messages]

        if delete_after_receive and selected_messages:
            remaining_messages = messages[max_messages:]
            with open(self.queue_file, "w") as f:
                json.dump(remaining_messages, f, indent=4)
            self.logger.info(f"🗑 Deleted {len(selected_messages)} message(s) after receive")

        return selected_messages

    def clear_queue(self):
        """Clears the queue"""
        if self.queue_type == "remote":
            return self.remote_client.clear_queue()
            
        # Local queue implementation
        with open(self.queue_file, "w") as f:
            json.dump([], f)
        self.logger.info("🚀 Queue cleared!")

    def remove_message(self, item_id):
        """Removes a message from the queue"""
        if self.queue_type == "remote":
            return self.remote_client.remove_message(item_id)
            
        # Local queue implementation
        with open(self.queue_file, "r") as f:
            queue = json.load(f)

        new_queue = [item for item in queue if item["id"] != item_id]

        with open(self.queue_file, "w") as f:
            json.dump(new_queue, f, indent=4)
        self.logger.info(f"🗑 Message removed: {item_id}")

    def update_message(self, item_id, new_message):
        """Updates a message in the queue"""
        if self.queue_type == "remote":
            return self.remote_client.update_message(item_id, new_message)
            
        # Local queue implementation
        with open(self.queue_file, "r") as f:
            queue = json.load(f)

        for item in queue:
            if item["id"] == item_id:
                item["timestamp"] = datetime.utcnow().isoformat()  # Add timestamp
                item["message_body"] = new_message
                break

        with open(self.queue_file, "w") as f:
            json.dump(queue, f, indent=4)
        self.logger.info(f"🔄 Message updated: {new_message}")
    
    def delete_message(self, receipt_handle: str):
        """
        Delete a message using receipt handle (SQS-style)
        For local queues, receipt_handle is treated as item_id
        """
        if self.queue_type == "remote":
            return self.remote_client.delete_message(receipt_handle)
            
        # Local queue implementation - treat receipt_handle as item_id
        return self.remove_message(receipt_handle)
    
    def get_queue_info(self):
        """Get information about the queue"""
        if self.queue_type == "remote":
            return self.remote_client.get_queue_info()
            
        # Local queue implementation
        try:
            messages = self.get_messages()
            return {
                "queue_type": "local",
                "queue_file": self.queue_file,
                "message_count": len(messages),
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
