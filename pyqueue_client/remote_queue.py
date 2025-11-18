import json
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Optional


class RemoteQueueClient:
    """Client for interacting with remote PyQueue server"""

    def __init__(self, server_url: str, queue_name: str = "default", api_key: str = None, timeout: int = 30):
        """
        Initialize remote queue client
        
        Args:
            server_url: Base URL of the PyQueue server (e.g., 'http://localhost:8000')
            queue_name: Name of the queue to interact with
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip('/')
        self.queue_name = queue_name
        self.timeout = timeout
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to the server"""
        url = f"{self.server_url}/api/v1/queues/{self.queue_name}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=self.timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            response.raise_for_status()
            
            print(f"🔗 {method} {url} - Status: {response.status_code}")
            print(f"📥 Response: {response.text}")
            print(f"📤 Data: {data}")

            return response.json() if response.content else {}
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to PyQueue server: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from server: {e}")
    
    def add_message(self, message: Dict, item_id: Optional[str] = None) -> str:
        """Add a message to the remote queue"""
        if item_id is None:
            item_id = message.get("id", str(uuid.uuid4()))
            
        payload = {
            "id": item_id,
            "message_body": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = self._make_request("POST", "/messages", payload)
        print(f"✅ Message added to remote queue: {item_id}")
        return response.get("id", item_id)
    
    def get_messages(self, max_messages: int = 10) -> List[Dict]:
        """Get messages from the remote queue"""
        endpoint = f"/messages?max_messages={max_messages}"
        response = self._make_request("GET", endpoint)
        return response.get("messages", [])
    
    def receive_messages(self, max_messages: int = 10, visibility_timeout: int = 30) -> List[Dict]:
        """
        Receive messages from the queue (like SQS ReceiveMessage)
        Messages become invisible for the specified timeout period
        """
        endpoint = f"/messages/receive?max_messages={max_messages}&visibility_timeout={visibility_timeout}"
        response = self._make_request("POST", endpoint)
        return response.get("messages", [])
    
    def delete_message(self, receipt_handle: str) -> bool:
        """Delete a message using its receipt handle"""
        endpoint = f"/messages/{receipt_handle}"
        self._make_request("DELETE", endpoint)
        print(f"🗑 Message deleted from remote queue: {receipt_handle}")
        return True
    
    def remove_message(self, item_id: str) -> bool:
        """Remove a message by its ID (for compatibility with local queue)"""
        endpoint = f"/messages/by-id/{item_id}"
        self._make_request("DELETE", endpoint)
        print(f"🗑 Message removed from remote queue: {item_id}")
        return True
    
    def update_message(self, item_id: str, new_message: Dict) -> bool:
        """Update a message in the remote queue"""
        payload = {
            "message_body": new_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        endpoint = f"/messages/by-id/{item_id}"
        self._make_request("PUT", endpoint, payload)
        print(f"🔄 Message updated in remote queue: {item_id}")
        return True
    
    def clear_queue(self) -> bool:
        """Clear all messages from the remote queue"""
        self._make_request("DELETE", "/messages")
        print("🚀 Remote queue cleared!")
        return True
    
    def get_queue_info(self) -> Dict:
        """Get information about the queue"""
        response = self._make_request("GET", "/info")
        return response
    
    def health_check(self) -> bool:
        """Check if the remote server is healthy"""
        try:
            response = self._make_request("GET", "/health")
            return response.get("status") == "healthy"
        except:
            return False
