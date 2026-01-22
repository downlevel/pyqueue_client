"""
Demo: Understanding "In-Flight" Messages in PyQueue

In message queue systems (like AWS SQS), "in-flight" messages are messages that:
1. Have been received by a consumer (via receive_messages)
2. Are temporarily invisible to other consumers
3. Haven't been deleted yet

This prevents duplicate processing by multiple consumers.
"""
import time
import logging
from pyqueue_client import PyQueue

# Setup logging
logging.basicConfig(level=logging.INFO)

def demo_in_flight_messages():
    """Demonstrate how in-flight messages work"""

    print("\n" + "="*70)
    print("IN-FLIGHT MESSAGES DEMO")
    print("="*70)

    # Create a clean queue
    queue = PyQueue(queue_type="local", queue_file="demo_queue.json")
    queue.clear_queue()

    # Add some test messages
    print("\n📦 Adding 5 messages to the queue...")
    for i in range(1, 6):
        queue.add_message({"task": f"task_{i}", "data": f"value_{i}"}, item_id=f"msg-{i}")

    # Check initial state
    info = queue.get_queue_info()
    print(f"\n📊 Initial Queue State:")
    print(f"   Total messages: {info['message_count']}")
    print(f"   Visible messages: {info['visible_messages']}")
    print(f"   In-flight messages: {info['invisible_messages']}")
    print(f"   Never received: {info['never_received']}")

    # STEP 1: Consumer A receives 3 messages
    print("\n" + "="*70)
    print("STEP 1: Consumer A receives 3 messages (30 second visibility timeout)")
    print("="*70)

    consumer_a_messages = queue.receive_messages(
        max_messages=3,
        visibility_timeout=30  # Messages invisible for 30 seconds
    )

    print(f"\n✅ Consumer A received {len(consumer_a_messages)} messages:")
    for msg in consumer_a_messages:
        print(f"   - {msg['Id']}: {msg['message_body']}")
        print(f"     Receipt Handle: {msg['ReceiptHandle']}")
        print(f"     Receive Count: {msg['receive_count']}")

    # Check state after receive
    info = queue.get_queue_info()
    print(f"\n📊 Queue State After Consumer A Receive:")
    print(f"   Total messages: {info['message_count']}")
    print(f"   Visible messages: {info['visible_messages']}")
    print(f"   IN-FLIGHT messages: {info['invisible_messages']} ⚠️")
    print(f"   Never received: {info['never_received']}")

    print("\n💡 The 3 messages are now 'in-flight':")
    print("   - They are INVISIBLE to other consumers")
    print("   - They will become visible again in 30 seconds")
    print("   - Consumer A can delete them using receipt handles")

    # STEP 2: Consumer B tries to receive immediately
    print("\n" + "="*70)
    print("STEP 2: Consumer B tries to receive messages IMMEDIATELY")
    print("="*70)

    consumer_b_messages = queue.receive_messages(max_messages=10)

    print(f"\n✅ Consumer B received {len(consumer_b_messages)} messages:")
    if consumer_b_messages:
        for msg in consumer_b_messages:
            print(f"   - {msg['Id']}: {msg['message_body']}")
    else:
        print("   (only the 2 visible messages, NOT the 3 in-flight ones)")

    # STEP 3: Consumer A successfully processes and deletes one message
    print("\n" + "="*70)
    print("STEP 3: Consumer A processes and deletes message 1")
    print("="*70)

    # Simulate processing
    msg_to_delete = consumer_a_messages[0]
    print(f"\n🔨 Consumer A processing: {msg_to_delete['Id']}")
    time.sleep(1)  # Simulate work

    # Delete using receipt handle
    success = queue.delete_message(msg_to_delete['ReceiptHandle'])
    if success:
        print(f"✅ Message {msg_to_delete['Id']} deleted successfully")

    info = queue.get_queue_info()
    print(f"\n📊 Queue State After Deletion:")
    print(f"   Total messages: {info['message_count']} (was 5, now 4)")
    print(f"   Visible messages: {info['visible_messages']}")
    print(f"   IN-FLIGHT messages: {info['invisible_messages']} (2 still in-flight)")

    # STEP 4: Consumer A fails to process another message (doesn't delete it)
    print("\n" + "="*70)
    print("STEP 4: Consumer A FAILS to process message 2 (doesn't delete it)")
    print("="*70)

    failed_msg = consumer_a_messages[1]
    print(f"\n❌ Consumer A failed to process: {failed_msg['Id']}")
    print("   (Receipt handle NOT used - message will retry)")
    print("   The message will become visible again after 30 seconds")

    # STEP 5: Wait for visibility timeout to expire
    print("\n" + "="*70)
    print("STEP 5: Waiting for visibility timeout to expire...")
    print("="*70)
    print("\n⏰ In a real scenario, you would wait 30 seconds.")
    print("   For this demo, we'll manually cleanup expired messages.")

    # Manually expire the visibility timeout by manipulating the queue
    # (In production, this happens automatically after the timeout)
    queue.cleanup_expired_messages()

    # Force expire by reading the raw queue and modifying timestamps
    import json
    with open("demo_queue.json", "r") as f:
        raw_queue = json.load(f)

    # Set all invisible_until to None (simulate timeout expiry)
    for msg in raw_queue:
        if msg.get("invisible_until"):
            msg["invisible_until"] = None

    with open("demo_queue.json", "w") as f:
        json.dump(raw_queue, f, indent=4)

    info = queue.get_queue_info()
    print(f"\n📊 Queue State After Timeout Expiry:")
    print(f"   Total messages: {info['message_count']}")
    print(f"   Visible messages: {info['visible_messages']} (messages are visible again!)")
    print(f"   IN-FLIGHT messages: {info['invisible_messages']}")

    print("\n💡 The failed message is now VISIBLE again and can be retried!")

    # STEP 6: Consumer B can now receive the previously failed message
    print("\n" + "="*70)
    print("STEP 6: Consumer B receives messages (including the retry)")
    print("="*70)

    consumer_b_retry = queue.receive_messages(max_messages=10, visibility_timeout=30)
    print(f"\n✅ Consumer B received {len(consumer_b_retry)} messages:")
    for msg in consumer_b_retry:
        print(f"   - {msg['Id']}: {msg['message_body']}")
        print(f"     Receive Count: {msg['receive_count']} (notice the retry count!)")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY: What is 'In-Flight'?")
    print("="*70)
    print("""
IN-FLIGHT MESSAGES are messages in a TEMPORARY STATE:

✅ What happens when you receive a message:
   1. Message becomes INVISIBLE (in-flight) for visibility_timeout seconds
   2. Receipt handle is generated for safe deletion
   3. receive_count is incremented
   4. first_received_at timestamp is set (if first time)

🔄 Two possible outcomes:

   SUCCESS: Consumer deletes the message
   ----------------------------------------
   - Consumer calls delete_message(receipt_handle)
   - Message is PERMANENTLY removed from queue
   - Other consumers never see it again

   FAILURE: Consumer doesn't delete the message
   ----------------------------------------
   - Visibility timeout expires (e.g., 30 seconds)
   - Message becomes VISIBLE again automatically
   - Another consumer can receive and retry it
   - receive_count increases with each retry

💡 Why is this useful?

   - Prevents duplicate processing by multiple consumers
   - Automatic retry on failure (just don't delete the message)
   - Safe processing: if consumer crashes, message returns to queue
   - Visibility timeout should be > your processing time

🔧 Implementation Details in PyQueue:

   Local Queue:
   - Uses "invisible_until" field (timestamp)
   - Automatic cleanup on every read operation
   - Receipt handles for safe deletion

   Remote Queue:
   - Server manages visibility state
   - Same API and behavior as local
    """)

    # Final state
    final_info = queue.get_queue_info()
    print("\n📊 Final Queue Statistics:")
    print(f"   Total messages: {final_info['message_count']}")
    print(f"   Visible: {final_info['visible_messages']}")
    print(f"   In-flight: {final_info['invisible_messages']}")
    print(f"   Total receives (across all messages): {final_info['total_receives']}")

    print("\n" + "="*70)
    print("Demo completed!")
    print("="*70)


if __name__ == "__main__":
    demo_in_flight_messages()
