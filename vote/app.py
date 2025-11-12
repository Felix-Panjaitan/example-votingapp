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

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "vote", "message": "%(message)s", "hostname": "'
    + hostname
    + '"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# gunicorn_error_logger = logging.getLogger("gunicorn.error")
# app.logger.handlers.extend(gunicorn_error_logger.handlers)
# app.logger.setLevel(logging.INFO)

# vote_counter = None

vote_counter = metrics.counter(
    "vote_count_total",
    "Number of votes submitted",
    labels={"option": lambda: request.form.get("vote", "")},
)


def get_redis():
    if not hasattr(g, "redis"):
        try:
            g.redis = Redis(host="redis", db=0, socket_timeout=5)
            app.logger.info(
                f'{{"action": "redis_connection", "status": "success", "host": "redis"}}'
            )
        except Exception as e:
            app.logger.error(
                f'{{"action": "redis_connection", "status": "error", "error": "{str(e)}"}}'
            )
            raise
    return g.redis


@app.route("/", methods=["POST", "GET"])
@vote_counter
def hello():
    voter_id = request.cookies.get("voter_id")
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]
        app.logger.info(f'{{"action": "new_voter", "voter_id": "{voter_id}"}}')

    vote = None

    if request.method == "POST":
        try:
            redis = get_redis()
            vote = request.form["vote"]
            # app.logger.info("Received vote for %s", vote)
            app.logger.info(
                f'{{"action": "vote_received", "vote": "{vote}", "voter_id": "{voter_id}"}}'
            )
            data = json.dumps({"voter_id": voter_id, "vote": vote})
            # data = json.dumps(
            #     {"voter_id": request.cookies.get("voter_id"), "vote": request.form["vote"]}
            # )
            redis.rpush("votes", data)
            app.logger.info(
                f'{{"action": "vote_stored", "vote": "{vote}", "voter_id": "{voter_id}", "status": "success"}}'
            )
            # app.logger.info("Recorded vote for %s", request.form["vote"])
            # return redirect(url_for("index"))
            # vote_counter.inc()
        except Exception as e:
            app.logger.error(
                f'{{"action": "vote_processing", "status": "error", "error": "{str(e)}", "voter_id": "{voter_id}"}}'
            )

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
