import json
import logging
import os
import random
import socket
import time

from flask import (
    Flask,
    Response,
    g,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from redis import Redis

option_a = os.getenv("OPTION_A", "Cats")
option_b = os.getenv("OPTION_B", "Dogs")
hostname = socket.gethostname()

app = Flask(__name__)

# Separate counters for cats and dogs
votes_cats_counter = Counter("votes_cats_total", "Total number of votes for cats")
votes_dogs_counter = Counter("votes_dogs_total", "Total number of votes for dogs")
votes_total_counter = Counter("votes_total", "Total number of votes cast")


def get_redis():
    if not hasattr(g, "redis"):
        try:
            g.redis = Redis(host="redis", db=0, socket_timeout=5)
            g.redis.ping()
        except Exception as e:
            app.logger.error(f"Redis connection failed: {str(e)}")
            raise
    return g.redis


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/", methods=["GET", "POST"])
def index():
    voter_id = request.cookies.get("voter_id")
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]

    vote = None

    if request.method == "POST":
        try:
            redis = get_redis()
            vote = request.form["vote"]

            # Increment specific counters based on vote
            if vote == "a":  # Cats
                votes_cats_counter.inc()
                app.logger.info(f"Vote for {option_a} recorded")
            elif vote == "b":  # Dogs
                votes_dogs_counter.inc()
                app.logger.info(f"Vote for {option_b} recorded")

            # Always increment total counter
            votes_total_counter.inc()

            # Store in Redis
            data = json.dumps(
                {"voter_id": voter_id, "vote": vote, "timestamp": time.time()}
            )
            redis.rpush("votes", data)

        except Exception as e:
            app.logger.error(f"Error processing vote: {str(e)}")

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
