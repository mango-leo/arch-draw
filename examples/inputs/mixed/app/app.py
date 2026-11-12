from flask import Flask
from store import save_order

app = Flask(__name__)

@app.post("/orders")
def checkout():
    save_order()
    return "", 201

if __name__ == "__main__":
    app.run(port=8080)
