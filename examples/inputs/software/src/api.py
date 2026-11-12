from queue import SimpleQueue
from store import save_order

orders = SimpleQueue()

def checkout(order):
    save_order(order)
    orders.put(order)

def worker():
    return orders.get()
