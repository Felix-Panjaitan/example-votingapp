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
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from redis import Redis

# Environment variables
option_a = os.getenv("OPTION_A", "Cats")
option_b = os.getenv("OPTION_B", "Dogs")
hostname = socket.gethostname()

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Prometheus metrics
vote_counter_cats = Counter("votes_cats_total", "Total number of votes for cats")
vote_counter_dogs = Counter("votes_dogs_total", "Total number of votes for dogs")
vote_counter_total = Counter("votes_total", "Total number of votes cast")
request_count = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint"]
)
request_duration = Histogram("http_request_duration_seconds", "HTTP request duration")
redis_connection_errors = Counter(
    "redis_connection_errors_total", "Total Redis connection errors"
)
active_users = Gauge("active_users_current", "Current number of active users")

# Track unique voters for active users gauge
unique_voters = set()


def get_redis():
    """Get Redis connection with error handling"""
    if not hasattr(g, "redis"):
        try:
            g.redis = Redis(host="redis", db=0, socket_timeout=5)
            # Test the connection
            g.redis.ping()
            app.logger.info("Successfully connected to Redis")
        except Exception as e:
            app.logger.error(f"Redis connection failed: {str(e)}")
            redis_connection_errors.inc()
            raise
    return g.redis


@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


@app.route("/health")
def health():
    """Health check endpoint"""
    try:
        redis = get_redis()
        redis.ping()
        return {"status": "healthy", "redis": "connected"}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500


@app.route("/", methods=["GET", "POST"])
def index():
    """Main voting page"""
    start_time = time.time()

    # Track HTTP requests
    request_count.labels(method=request.method, endpoint="/").inc()

    # Get or create voter ID
    voter_id = request.cookies.get("voter_id")
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]
        app.logger.info(f"New voter created: {voter_id}")

    # Track unique voters for active users metric
    unique_voters.add(voter_id)
    active_users.set(len(unique_voters))

    vote = None

    if request.method == "POST":
        try:
            redis = get_redis()
            vote = request.form["vote"]

            app.logger.info(f"Received vote: {vote} from voter: {voter_id}")

            # Increment vote counters
            if vote == "a":  # Cats
                vote_counter_cats.inc()
                app.logger.info(f"Vote for {option_a} (cats) recorded")
            elif vote == "b":  # Dogs
                vote_counter_dogs.inc()
                app.logger.info(f"Vote for {option_b} (dogs) recorded")

            # Increment total vote counter
            vote_counter_total.inc()

            # Store vote in Redis
            data = json.dumps(
                {
                    "voter_id": voter_id,
                    "vote": vote,
                    "timestamp": time.time(),
                    "option": option_a if vote == "a" else option_b,
                }
            )
            redis.rpush("votes", data)

            app.logger.info(
                f"Vote stored successfully in Redis: {vote} from {voter_id}"
            )

        except Exception as e:
            app.logger.error(f"Error processing vote: {str(e)}")
            redis_connection_errors.inc()
            # Still render the page even if vote fails

    # Record request duration
    duration = time.time() - start_time
    request_duration.observe(duration)

    # Create response
    resp = make_response(
        render_template(
            "index.html",
            option_a=option_a,
            option_b=option_b,
            hostname=hostname,
            vote=vote,
        )
    )

    # Set voter ID cookie
    resp.set_cookie("voter_id", voter_id)

    return resp


@app.route("/stats")
def stats():
    """Show current voting stats"""
    try:
        # Get current vote counts from Prometheus metrics
        cats_count = vote_counter_cats._value._value
        dogs_count = vote_counter_dogs._value._value
        total_count = vote_counter_total._value._value

        stats_data = {
            "cats_votes": cats_count,
            "dogs_votes": dogs_count,
            "total_votes": total_count,
            "cats_percentage": round(
                (cats_count / total_count * 100) if total_count > 0 else 0, 1
            ),
            "dogs_percentage": round(
                (dogs_count / total_count * 100) if total_count > 0 else 0, 1
            ),
            "active_users": len(unique_voters),
            "leading": (
                option_a
                if cats_count > dogs_count
                else option_b if dogs_count > cats_count else "Tie"
            ),
        }

        return stats_data

    except Exception as e:
        app.logger.error(f"Error getting stats: {str(e)}")
        return {"error": str(e)}, 500


@app.before_request
def before_request():
    """Log all incoming requests"""
    app.logger.info(
        f"Request: {request.method} {request.path} from {request.remote_addr}"
    )


@app.after_request
def after_request(response):
    """Log response status"""
    app.logger.info(
        f"Response: {response.status_code} for {request.method} {request.path}"
    )
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all exceptions"""
    app.logger.error(f"Unhandled exception: {str(e)}")
    return (
        render_template(
            "index.html",
            option_a=option_a,
            option_b=option_b,
            hostname=hostname,
            error="An error occurred. Please try again.",
        ),
        500,
    )


if __name__ == "__main__":
    app.logger.info(f"Starting vote service on {hostname}")
    app.logger.info(f"Vote options: {option_a} vs {option_b}")
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
