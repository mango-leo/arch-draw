# Order processing architecture

When a checkout is confirmed, the Order API writes the order to Orders DB.

The API also publishes an OrderPlaced event to the Event Queue.
