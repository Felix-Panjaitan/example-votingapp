import json
import logging
import os
import random
import socket

from flask import Flask, g, make_response, redirect, render_template, request, url_for
from prometheus_flask_exporter import PrometheusMetrics
from redis import Redis

option_a = os.getenv("OPTION_A", "Cats")
option_b = os.getenv("OPTION_B", "Dogs")
hostname = socket.gethostname()

app = Flask(__name__)
metrics = PrometheusMetrics(app)

gunicorn_error_logger = logging.getLogger("gunicorn.error")
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

# vote_counter = None

vote_counter = metrics.counter(
    "vote_count_total",
    "Number of votes submitted",
    labels={"option": lambda: request.form.get("vote", "")},
)


def get_redis():
    if not hasattr(g, "redis"):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    return g.redis


@app.route("/", methods=["POST", "GET"])
@vote_counter
def hello():
    voter_id = request.cookies.get("voter_id")
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]

    vote = None

    if request.method == "POST":
        redis = get_redis()
        vote = request.form["vote"]
        app.logger.info("Received vote for %s", vote)
        data = json.dumps({"voter_id": voter_id, "vote": vote})
        # data = json.dumps(
        #     {"voter_id": request.cookies.get("voter_id"), "vote": request.form["vote"]}
        # )
        redis.rpush("votes", data)
        # app.logger.info("Recorded vote for %s", request.form["vote"])
        # return redirect(url_for("index"))
        # vote_counter.inc()

    resp = make_response(
        render_template(
            "index.html",
            option_a=option_a,
            option_b=option_b,
            hostname=hostname,
            vote=vote,
        )
    )
    resp.set_cookie("voter_id", voter_id)
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
