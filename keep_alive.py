from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def main():
	return os.environ["REPLIT_DB_URL"]

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()