import os
from datetime import date
from pathlib import Path

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

from nlp_engine import deadline_details, df, recommend_scholarships


app = Flask(__name__)
CORS(app)
WEBSITE_DIRECTORY_PATH = Path(__file__).with_name("scholarship_websites.csv")


@app.route("/")
def home():
    return jsonify({
        "message": "AI Grant & Scholarship Finder API is running"
    })


@app.route("/dashboard", methods=["GET"])
def dashboard():
    website_directory = pd.read_csv(WEBSITE_DIRECTORY_PATH).fillna("").to_dict(orient="records")
    today = date.today()
    upcoming = []
    deadline_counts = {
        "open": 0,
        "closing_soon": 0,
        "upcoming": 0,
        "closed": 0,
        "not_listed": 0,
    }

    for _, scholarship in df.iterrows():
        details = deadline_details(
            scholarship.get("application_deadline"),
            today,
            scholarship.get("application_start"),
        )
        status = details["deadline_status"]
        if status == "Open":
            deadline_counts["open"] += 1
        elif status == "Closing soon":
            deadline_counts["closing_soon"] += 1
        elif status == "Closed":
            deadline_counts["closed"] += 1
        elif status == "Opens soon":
            deadline_counts["upcoming"] += 1
        else:
            deadline_counts["not_listed"] += 1

        if details["days_remaining"] is not None and details["days_remaining"] >= 0:
            upcoming.append({
                "id": int(scholarship["id"]),
                "name": str(scholarship["name"]),
                "provider": str(scholarship["provider"]),
                "application_deadline": str(scholarship["application_deadline"]),
                "application_url": (
                    "" if pd.isna(scholarship.get("application_url"))
                    else str(scholarship["application_url"])
                ),
                "guidelines_url": (
                    "" if pd.isna(scholarship.get("guidelines_url"))
                    else str(scholarship["guidelines_url"])
                ),
                **details,
            })

    upcoming.sort(key=lambda item: item["days_remaining"])
    return jsonify({
        "success": True,
        "total_scholarships": len(df),
        "scholarship_websites": website_directory,
        "deadline_counts": deadline_counts,
        "upcoming_deadlines": upcoming[:5],
        "filter_options": {
            "fields": sorted({
                str(value).strip()
                for value in df["field"]
                if str(value).strip() and str(value).strip().casefold() != "any"
            }),
            "levels": sorted({
                str(value).strip()
                for value in df["level"]
                if str(value).strip() and str(value).strip().casefold() != "any"
            }),
        },
    })


@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "Send a JSON profile or query"
            }), 400

        profile = data.get("profile", {})
        if not isinstance(profile, dict):
            return jsonify({
                "error": "Profile must be a JSON object"
            }), 400

        filters = data.get("filters", {})
        if not isinstance(filters, dict):
            return jsonify({
                "error": "Filters must be a JSON object"
            }), 400
        if any(not isinstance(value, str) for value in filters.values()):
            return jsonify({
                "error": "Filter values must be strings"
            }), 400

        top_n = data.get("top_n", 5)
        if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 50:
            return jsonify({
                "error": "top_n must be an integer between 1 and 50"
            }), 400

        user_query = data.get("query", "")
        if not isinstance(user_query, str):
            return jsonify({
                "error": "Query must be a string"
            }), 400

        if not user_query.strip():
            user_query = ", ".join(
                f"{key}: {value}"
                for key, value in profile.items()
                if str(value).strip()
            )

        advanced_query = filters.get("search_text", "").strip()
        if advanced_query:
            user_query = f"{user_query}, {advanced_query}".strip(", ")

        if not user_query.strip():
            if any(value.strip() and value != "relevance" for value in filters.values()):
                user_query = "scholarship grant"
            else:
                return jsonify({
                    "error": "Profile cannot be empty"
                }), 400

        recommendations = recommend_scholarships(
            user_query,
            top_n=top_n,
            profile=profile,
            filters=filters,
        )

        return jsonify({
            "success": True,
            "recommendations": recommendations
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        port=int(os.environ.get("PORT", "5000")),
    )
