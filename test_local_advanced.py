"""
Advanced test suite for local queue with SQS-style features
Tests visibility timeout, receipt handles, only_new flag, and receive tracking
"""
import time
import logging
from pyqueue_client import PyQueue

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_basic_operations():
    """Test basic add and get operations"""
    print("\n=== TEST 1: Basic Operations ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Add messages
    queue.add_message({"task": "task1", "data": "value1"}, item_id="msg1")
    queue.add_message({"task": "task2", "data": "value2"}, item_id="msg2")
    queue.add_message({"task": "task3", "data": "value3"}, item_id="msg3")

    # Get all messages
    messages = queue.get_messages()
    print(f"✅ Added {len(messages)} messages")
    assert len(messages) == 3, "Should have 3 messages"
    print("✅ Basic operations test passed!")


def test_visibility_timeout():
    """Test that messages become invisible after receive and reappear after timeout"""
    print("\n=== TEST 2: Visibility Timeout ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Add test messages
    queue.add_message({"task": "timeout_test"}, item_id="timeout1")
    queue.add_message({"task": "timeout_test"}, item_id="timeout2")

    # Receive with 3 second visibility timeout
    print("Receiving messages with 3 second visibility timeout...")
    received = queue.receive_messages(max_messages=2, visibility_timeout=3)
    print(f"✅ Received {len(received)} messages")
    assert len(received) == 2, "Should receive 2 messages"

    # Try to receive again immediately - should get nothing (messages are invisible)
    print("Trying to receive again immediately...")
    received_again = queue.receive_messages(max_messages=10)
    print(f"✅ Received {len(received_again)} messages (should be 0 - messages are invisible)")
    assert len(received_again) == 0, "Should not receive any messages (still invisible)"

    # Wait for visibility timeout to expire
    print("Waiting 4 seconds for visibility timeout to expire...")
    time.sleep(4)

    # Now should be able to receive again
    print("Trying to receive after timeout expired...")
    received_after_timeout = queue.receive_messages(max_messages=10)
    print(f"✅ Received {len(received_after_timeout)} messages (should be 2 - messages are visible again)")
    assert len(received_after_timeout) == 2, "Should receive 2 messages again"

    print("✅ Visibility timeout test passed!")


def test_receipt_handles():
    """Test that receipt handles work correctly for deletion"""
    print("\n=== TEST 3: Receipt Handles ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Add test messages
    queue.add_message({"task": "receipt_test"}, item_id="receipt1")
    queue.add_message({"task": "receipt_test"}, item_id="receipt2")

    # Receive messages
    print("Receiving messages...")
    received = queue.receive_messages(max_messages=2, visibility_timeout=30)
    print(f"✅ Received {len(received)} messages with receipt handles")

    # Verify receipt handles are present
    assert all("ReceiptHandle" in msg for msg in received), "All messages should have receipt handles"
    print(f"✅ Receipt handle example: {received[0]['ReceiptHandle']}")

    # Delete using receipt handle
    receipt_to_delete = received[0]["ReceiptHandle"]
    print(f"Deleting message with receipt handle: {receipt_to_delete}")
    success = queue.delete_message(receipt_to_delete)
    assert success, "Delete should succeed"

    # Verify only 1 message remains (need to wait for visibility timeout)
    time.sleep(31)  # Wait for visibility timeout to expire
    remaining = queue.get_messages()
    print(f"✅ {len(remaining)} message(s) remaining after deletion")
    assert len(remaining) == 1, "Should have 1 message left"

    # Try to delete with invalid receipt handle
    print("Trying to delete with invalid receipt handle...")
    invalid_delete = queue.delete_message("invalid_receipt_handle")
    print(f"✅ Delete with invalid handle returned: {invalid_delete} (should be False)")

    print("✅ Receipt handles test passed!")


def test_only_new_flag():
    """Test that only_new flag filters out previously received messages"""
    print("\n=== TEST 4: Only New Flag ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Add test messages
    queue.add_message({"task": "new_test"}, item_id="new1")
    queue.add_message({"task": "new_test"}, item_id="new2")
    queue.add_message({"task": "new_test"}, item_id="new3")

    # Receive 2 messages (they become "not new")
    print("Receiving 2 messages (marking them as 'not new')...")
    first_receive = queue.receive_messages(max_messages=2, visibility_timeout=1, delete_after_receive=False)
    print(f"✅ Received {len(first_receive)} messages")

    # Wait for visibility timeout
    time.sleep(2)

    # Receive with only_new=True - should get only the 3rd message
    print("Receiving with only_new=True (should get only 1 message)...")
    only_new_receive = queue.receive_messages(max_messages=10, only_new=True, visibility_timeout=1)
    print(f"✅ Received {len(only_new_receive)} message(s) with only_new=True")
    assert len(only_new_receive) == 1, "Should receive only 1 new message"

    # Receive without only_new - should get all 3 messages
    time.sleep(2)
    print("Receiving without only_new flag (should get all 3)...")
    all_receive = queue.receive_messages(max_messages=10, only_new=False, visibility_timeout=1)
    print(f"✅ Received {len(all_receive)} messages without only_new flag")
    assert len(all_receive) == 3, "Should receive all 3 messages"

    print("✅ Only new flag test passed!")


def test_receive_count_tracking():
    """Test that receive_count is tracked correctly"""
    print("\n=== TEST 5: Receive Count Tracking ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Add test message
    queue.add_message({"task": "count_test"}, item_id="count1")

    # Receive multiple times
    for i in range(3):
        print(f"Receive attempt {i+1}...")
        received = queue.receive_messages(max_messages=1, visibility_timeout=1)
        print(f"  Receive count: {received[0]['receive_count']}")
        assert received[0]['receive_count'] == i + 1, f"Receive count should be {i+1}"
        time.sleep(2)  # Wait for visibility timeout

    print("✅ Receive count tracking test passed!")


def test_delete_after_receive():
    """Test immediate deletion after receive"""
    print("\n=== TEST 6: Delete After Receive ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Add test messages
    queue.add_message({"task": "delete_test"}, item_id="del1")
    queue.add_message({"task": "delete_test"}, item_id="del2")

    # Receive with delete_after_receive=True
    print("Receiving with delete_after_receive=True...")
    received = queue.receive_messages(max_messages=2, delete_after_receive=True)
    print(f"✅ Received and deleted {len(received)} messages")

    # Check queue is empty
    remaining = queue.get_messages()
    print(f"✅ {len(remaining)} messages remaining (should be 0)")
    assert len(remaining) == 0, "Queue should be empty"

    print("✅ Delete after receive test passed!")


def test_queue_info():
    """Test get_queue_info with visibility statistics"""
    print("\n=== TEST 7: Queue Info ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Add messages
    queue.add_message({"task": "info_test"}, item_id="info1")
    queue.add_message({"task": "info_test"}, item_id="info2")
    queue.add_message({"task": "info_test"}, item_id="info3")

    # Get info before receiving
    info = queue.get_queue_info()
    print(f"Queue info before receive:")
    print(f"  Total messages: {info['message_count']}")
    print(f"  Visible: {info['visible_messages']}")
    print(f"  Invisible: {info['invisible_messages']}")
    print(f"  Never received: {info['never_received']}")
    assert info['visible_messages'] == 3, "All should be visible"
    assert info['never_received'] == 3, "All should be never received"

    # Receive some messages
    queue.receive_messages(max_messages=2, visibility_timeout=10)

    # Get info after receiving
    info = queue.get_queue_info()
    print(f"\nQueue info after receive:")
    print(f"  Total messages: {info['message_count']}")
    print(f"  Visible: {info['visible_messages']}")
    print(f"  Invisible: {info['invisible_messages']}")
    print(f"  Never received: {info['never_received']}")
    assert info['invisible_messages'] == 2, "2 should be invisible"
    assert info['never_received'] == 1, "1 should be never received"

    print("✅ Queue info test passed!")


def test_backward_compatibility():
    """Test that old messages without new fields still work"""
    print("\n=== TEST 8: Backward Compatibility ===")
    queue = PyQueue(queue_file="test_queue.json", queue_type="local")
    queue.clear_queue()

    # Manually add an old-style message (without tracking fields)
    import json
    old_message = {
        "id": "old1",
        "timestamp": "2025-01-01T00:00:00.000000",
        "message_body": {"task": "old_task"}
    }
    with open("test_queue.json", "w") as f:
        json.dump([old_message], f)

    # Try to receive it
    print("Receiving old-style message...")
    received = queue.receive_messages(max_messages=1, visibility_timeout=5)
    print(f"✅ Received {len(received)} old-style message")
    assert len(received) == 1, "Should receive the old message"
    assert received[0]['receive_count'] == 1, "Should have receive_count=1 after first receive"

    print("✅ Backward compatibility test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("PyQueue Local - Advanced Feature Tests")
    print("Testing: Visibility Timeout, Receipt Handles, Only New, etc.")
    print("=" * 60)

    try:
        test_basic_operations()
        test_visibility_timeout()
        test_receipt_handles()
        test_only_new_flag()
        test_receive_count_tracking()
        test_delete_after_receive()
        test_queue_info()
        test_backward_compatibility()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
