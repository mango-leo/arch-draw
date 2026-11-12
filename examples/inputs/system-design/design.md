# Warehouse system architecture

The warehouse operator sends pick requests to the Fulfillment API.
The API queues each request for the Picking Worker.
The worker updates inventory in the Stock Ledger.
The Proposed Simulator would read the Stock Ledger in a future design.
