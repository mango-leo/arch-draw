from sqlite3 import connect

def save_order():
    with connect("orders.db") as db:
        db.execute("INSERT INTO orders DEFAULT VALUES")
