"""Intentionally vulnerable demo app. Used only to test the DevSecOps agent. Never deploy."""
import sqlite3
import subprocess
from flask import Flask, request

app = Flask(__name__)
API_KEY = "x9Kd82hf3LqPz71vBn40sWqE5tYu6iOaR2mC"  # fake key for scanner testing


@app.route("/")
def index():
    return '<a href="/hello?n=a">hello</a> <a href="/user?name=a">user</a> <a href="/ping?host=localhost">ping</a>'


@app.route("/user")
def user():
    name = request.args.get("name", "")
    db = sqlite3.connect("app.db")
    return str(db.execute("SELECT * FROM users WHERE name = '%s'" % name).fetchall())  # SQLi


@app.route("/ping")
def ping():
    return subprocess.check_output("ping -c1 " + request.args.get("host", ""), shell=True)  # cmd injection


@app.route("/hello")
def hello():
    return "<h1>Hello " + request.args.get("n", "") + "</h1>"  # reflected XSS


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
