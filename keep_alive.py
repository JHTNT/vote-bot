from flask import Flask
from threading import Thread
import os

app = Flask('')

# print(os.environ["REPLIT_DB_URL"])

@app.route('/')
def main():
	return 'Bot is aLive!'

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()