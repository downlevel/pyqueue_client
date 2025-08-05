import os

# Default queue file path (can be overridden with an environment variable)
QUEUE_FILE_PATH = os.getenv("QUEUE_FILE_PATH", "queue.json")
