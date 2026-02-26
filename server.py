"""GITAM Results Proxy — targets https://gitamite.my/get_result."""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

ENDPOINT = "https://gitamite.my/get_result"
BASE_URL = "https://gitamite.my/"

CSRF_TOKEN = "Mx2wpsBQX3uWDhNOnbB4FjqpEfMHxjg1"
SESSION_ID = "atlxh2siz7s9v68t4pxeoxqnvizkypgf"


def make_session() -> requests.Session:
    session = requests.Session()
    session.cookies.set("csrftoken", CSRF_TOKEN, domain="gitamite.my")
    session.cookies.set("sessionid", SESSION_ID, domain="gitamite.my")
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://gitamite.my",
            "Referer": "https://gitamite.my/",
        }
    )
    return session


def enforce_unlimited_credits(payload: dict) -> dict:
    """Force credits-related values to unlimited in the API response."""
    payload["balance"] = "Unlimited"

    for key in ("sem_table", "sessional_table", "internal_marks"):
        items = payload.get(key)
        if isinstance(items, list):
            for row in items:
                if isinstance(row, dict):
                    if "credits" in row:
                        row["credits"] = "Unlimited"
                    if "credit" in row:
                        row["credit"] = "Unlimited"

    for key in ("credits", "credit", "total_credits", "remaining_credits"):
        if key in payload:
            payload[key] = "Unlimited"

    return payload


@app.route("/api/results", methods=["POST"])
def fetch_results():
    body = request.json or {}
    reg = body.get("reg", "").strip()
    sem = str(body.get("sem", "")).strip()

    if not reg:
        return jsonify({"error": "Registration number is required"}), 400
    if not sem:
        return jsonify({"error": "Semester is required"}), 400

    session = make_session()
    form_data = {
        "csrfmiddlewaretoken": (None, CSRF_TOKEN),
        "reg": (None, reg),
        "sem": (None, sem),
    }

    try:
        resp = session.post(ENDPOINT, files=form_data, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        return jsonify({"error": f"Request failed: {exc}"}), 502

    content_type = resp.headers.get("Content-Type", "")
    if "application/json" in content_type:
        data = resp.json()
        if isinstance(data, dict):
            return jsonify(enforce_unlimited_credits(data))
        return jsonify(data)

    return jsonify({"raw_snippet": resp.text[:2000], "message": "Got HTML instead of JSON"})


@app.route("/api/debug", methods=["GET"])
def debug():
    return jsonify({"status": "ok", "base_url": BASE_URL, "credits_mode": "unlimited"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
