from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["github_events"]
collection = db["events"]

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        event = {
            "request_id": data["head_commit"]["id"],
            "author": data["pusher"]["name"],
            "action": "PUSH",
            "from_branch": "",
            "to_branch": data["ref"].split("/")[-1],
            "timestamp": datetime.utcnow()
        }

    elif event_type == "pull_request":
        pr = data["pull_request"]
        action_type = "MERGE" if pr["merged"] else "PULL_REQUEST"

        event = {
            "request_id": str(pr["id"]),
            "author": pr["user"]["login"],
            "action": action_type,
            "from_branch": pr["head"]["ref"],
            "to_branch": pr["base"]["ref"],
            "timestamp": datetime.utcnow()
        }

    else:
        return jsonify({"message": "ignored"}), 200

    if not collection.find_one({"request_id": event["request_id"]}):
        collection.insert_one(event)

    return jsonify({"message": "stored"}), 200


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/events")
def events():
    data = collection.find().sort("timestamp", -1)
    result = []

    for e in data:
        time_str = e["timestamp"].strftime("%d %B %Y - %I:%M %p UTC")

        if e["action"] == "PUSH":
            msg = f'{e["author"]} pushed to {e["to_branch"]} on {time_str}'

        elif e["action"] == "PULL_REQUEST":
            msg = f'{e["author"]} submitted a pull request from {e["from_branch"]} to {e["to_branch"]} on {time_str}'

        elif e["action"] == "MERGE":
            msg = f'{e["author"]} merged branch {e["from_branch"]} to {e["to_branch"]} on {time_str}'

        result.append(msg)

    return jsonify(result)


if __name__ == "__main__":
    app.run()
