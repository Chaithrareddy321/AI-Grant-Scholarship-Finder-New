import unittest
from datetime import date

import pandas as pd

from app import app
from nlp_engine import deadline_details, df, field_groups, profile_is_eligible


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.profile = {
            "age": "18",
            "income": "25000",
            "education": "UG",
            "field": "Computer Science and Engineering",
            "gender": "Male",
            "category": "SC",
            "state": "Andhra Pradesh",
            "marks": "8.9 CGPA",
        }

    def test_profile_search_returns_relevant_sc_award(self):
        response = self.client.post(
            "/recommend",
            json={"query": "CSE student", "profile": self.profile},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        names = [item["name"] for item in response.get_json()["recommendations"]]
        self.assertIn("Central Sector Scholarship of Top Class Education for SC Students", names)
        self.assertNotIn("Women Techmakers Scholarship", names)
        self.assertNotIn("Kotak Kanya Scholarship", names)
        self.assertFalse(any("ICAR" in name for name in names))
        self.assertFalse(any("Postgraduate Scholarships" in name for name in names))

    def test_special_award_requires_matching_status(self):
        worker_award = df[df["id"] == 17].iloc[0]
        self.assertFalse(profile_is_eligible(worker_award, self.profile))
        self.assertTrue(
            profile_is_eligible(
                worker_award,
                {
                    **self.profile,
                    "special_status": "Child of a covered worker (beedi/cine/mines)",
                },
            )
        )

    def test_reserved_category_and_region_mismatches_are_filtered(self):
        obc_award = df[df["id"] == 10].iloc[0]
        north_east_award = df[df["id"] == 9].iloc[0]
        self.assertFalse(profile_is_eligible(obc_award, self.profile))
        self.assertFalse(profile_is_eligible(north_east_award, self.profile))

    def test_income_limit_includes_exactly_250000_but_rejects_more(self):
        post_matric_sc = df[df["id"] == 49].iloc[0]
        at_limit = {**self.profile, "income": "250000"}
        over_limit = {**self.profile, "income": "250001"}

        self.assertTrue(profile_is_eligible(post_matric_sc, at_limit))
        self.assertFalse(profile_is_eligible(post_matric_sc, over_limit))

    def test_new_schemes_have_official_application_and_guideline_links(self):
        for scholarship_id in (49, 50):
            scholarship = df[df["id"] == scholarship_id].iloc[0]
            self.assertEqual(scholarship["max_income"], "250000")
            self.assertIn("scholarships.gov.in", scholarship["application_url"])
            self.assertTrue(scholarship["guidelines_url"].startswith("https://"))

    def test_emerging_technology_branches_are_recognized(self):
        self.assertIn("computing", field_groups("Cloud Computing"))
        self.assertIn("computing", field_groups("Quantum Computing"))
        technology_award = df[df["id"] == 38].iloc[0]
        technology_profile = {
            **self.profile,
            "gender": "Female",
            "field": "Cloud Computing",
        }
        self.assertTrue(profile_is_eligible(technology_award, technology_profile))

    def test_legacy_query_only_request_is_still_supported(self):
        response = self.client.post(
            "/recommend",
            json={"query": "computer science scholarship"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["recommendations"])

    def test_dashboard_returns_deadline_tracking_summary(self):
        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total_scholarships"], len(df))
        self.assertIn("closing_soon", payload["deadline_counts"])
        self.assertLessEqual(len(payload["upcoming_deadlines"]), 5)
        self.assertIn("Engineering and Technology", payload["filter_options"]["fields"])
        self.assertIn("UG", payload["filter_options"]["levels"])
        websites = payload["scholarship_websites"]
        self.assertEqual(len(websites), 4)
        self.assertTrue(all(site["name"] and site["url"].startswith("https://") for site in websites))
        if payload["upcoming_deadlines"]:
            first_deadline = payload["upcoming_deadlines"][0]
            scholarship = df[df["id"] == first_deadline["id"]].iloc[0]
            expected_application_url = "" if pd.isna(scholarship["application_url"]) else scholarship["application_url"]
            expected_guidelines_url = "" if pd.isna(scholarship["guidelines_url"]) else scholarship["guidelines_url"]
            self.assertEqual(first_deadline["application_url"], expected_application_url)
            self.assertEqual(first_deadline["guidelines_url"], expected_guidelines_url)

    def test_deadline_statuses_are_calculated_for_known_dates(self):
        today = date(2026, 10, 25)

        self.assertEqual(
            deadline_details("2026-10-31", today)["deadline_status"],
            "Closing soon",
        )
        self.assertEqual(
            deadline_details("2026-11-20", today)["deadline_status"],
            "Open",
        )
        self.assertEqual(
            deadline_details("2026-10-20", today)["deadline_status"],
            "Closed",
        )
        self.assertEqual(
            deadline_details("2026-11-20", today, "2026-11-01")["deadline_status"],
            "Opens soon",
        )

    def test_advanced_provider_filter_is_applied(self):
        response = self.client.post(
            "/recommend",
            json={
                "filters": {"provider_type": "Government"},
                "top_n": 10,
            },
        )

        self.assertEqual(response.status_code, 200)
        recommendations = response.get_json()["recommendations"]
        self.assertTrue(recommendations)
        self.assertTrue(all(item["provider_type"].startswith("Government") for item in recommendations))

    def test_advanced_field_and_level_filters_are_applied(self):
        response = self.client.post(
            "/recommend",
            json={
                "filters": {
                    "field": "Agriculture",
                    "level": "PG",
                },
                "top_n": 10,
            },
        )

        self.assertEqual(response.status_code, 200)
        recommendations = response.get_json()["recommendations"]
        self.assertTrue(recommendations)
        self.assertTrue(all("Agriculture" in item["field"] for item in recommendations))
        self.assertTrue(all("PG" in item["level"] for item in recommendations))

    def test_invalid_result_limit_is_rejected(self):
        response = self.client.post(
            "/recommend",
            json={"query": "computer science", "top_n": 1000},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
