import pandas as pd
import re
import nltk
from datetime import date
from pathlib import Path

# ============================================================
# 1. ENSURE NLTK RESOURCES ARE AVAILABLE
# ============================================================

def ensure_nltk_resources():
    resources = (
        ("corpora/stopwords", "stopwords"),
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/wordnet", "wordnet"),
        ("corpora/omw-1.4", "omw-1.4"),
    )
    for location, package in resources:
        try:
            nltk.data.find(location)
        except LookupError:
            if not nltk.download(package, quiet=True):
                raise RuntimeError(
                    f"Unable to download the NLTK resource '{package}'. "
                    "Check network access or install it with nltk.download()."
                )


ensure_nltk_resources()

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================
# 2. LOAD SCHOLARSHIP DATASET
# ============================================================

df = pd.read_csv(Path(__file__).with_name("scholarships.csv"))

print("\n================ ORIGINAL DATASET ================\n")
print(df.head())

# Replace missing values
df = df.fillna("")


# ============================================================
# 3. NLTK SETUP
# ============================================================

stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()


# ============================================================
# 4. TEXT PREPROCESSING FUNCTION
# ============================================================

def preprocess_text(text):

    # Convert everything to string
    text = str(text)

    # Convert to lowercase
    text = text.lower()

    # Remove special characters
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Tokenization
    tokens = word_tokenize(text)

    # Remove stopwords
    tokens = [
        word for word in tokens
        if word not in stop_words
    ]

    # Lemmatization
    tokens = [
        lemmatizer.lemmatize(word)
        for word in tokens
    ]

    # Convert list back to sentence
    return " ".join(tokens)


# ============================================================
# 5. CREATE TEXT FOR NLP / TF-IDF
# ============================================================

df["combined_text"] = (
    df["name"].astype(str) + " " +
    df["provider"].astype(str) + " " +
    df["provider_type"].astype(str) + " " +
    df["description"].astype(str) + " " +
    df["field"].astype(str) + " " +
    df["level"].astype(str) + " " +
    df["gender"].astype(str) + " " +
    df["state"].astype(str) + " " +
    df["category"].astype(str) + " " +
    df["max_income"].astype(str) + " " +
    df["min_percentage"].astype(str) + " " +
    df["age_requirement"].astype(str) + " " +
    df["application_start"].astype(str) + " " +
    df["application_deadline"].astype(str)
)


# ============================================================
# 6. PREPROCESS THE SCHOLARSHIP TEXT
# ============================================================

df["processed_text"] = df["combined_text"].apply(
    preprocess_text
)


# ============================================================
# 7. SAVE PREPROCESSED DATASET
# ============================================================

df.to_csv(
    Path(__file__).with_name("preprocessed_scholarships.csv"),
    index=False
)

print("\n================ PREPROCESSED DATASET ================\n")

print(
    df[
        [
            "id",
            "name",
            "field",
            "level",
            "gender",
            "state",
            "category",
            "processed_text"
        ]
    ].head()
)

print(
    "\nPreprocessed data saved successfully!"
)


# ============================================================
# 8. TF-IDF VECTOR REPRESENTATION
# ============================================================

vectorizer = TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 2)
)

tfidf_matrix = vectorizer.fit_transform(
    df["processed_text"]
)

print("\n================ TF-IDF INFORMATION ================\n")

print(
    "TF-IDF Matrix Shape:",
    tfidf_matrix.shape
)


# ============================================================
# 9. SCHOLARSHIP RECOMMENDATION FUNCTION
# ============================================================

def field_groups(value):
    text = str(value or "").lower()
    groups = set()
    patterns = {
        "computing": r"computer|information technology|information systems|data science|cyber|artificial intelligence|machine learning|software|cloud|blockchain|internet of things|\biot\b|embedded systems|vlsi|quantum computing|game development|bioinformatics|computational biology|fintech|human computer interaction|digital forensics|big data|computing",
        "engineering": r"engineering|technology|aerospace|automobile|robotics|nanotechnology|mechatronics|vlsi",
        "agriculture": r"agriculture|agricultural",
        "statistics": r"statistics|statistical|mathematics",
        "life sciences": r"life sciences|biotechnology|biomedical|biology|biological",
        "health": r"medicine|medical|health",
        "energy": r"energy|renewable",
        "business": r"commerce|management|business",
        "law": r"\blaw\b",
        "humanities": r"humanities|social sciences|literature|history",
    }
    for group, pattern in patterns.items():
        if re.search(pattern, text):
            groups.add(group)
    return groups


def profile_is_eligible(scholarship, profile):
    def profile_value(name):
        return str(profile.get(name, "")).strip()

    level = profile_value("education").lower()
    scholarship_level = str(scholarship.get("level", "")).lower()
    level_patterns = {
        "ug": r"\bug\b|undergraduate|bachelor",
        "diploma": r"diploma|post matric",
        "pg": r"\bpg\b|postgraduate|post graduate|master",
        "phd": r"\bph\.?d\b|doctoral",
    }
    pattern = level_patterns.get(level)
    listed_levels = [
        level_name
        for level_name, level_pattern in level_patterns.items()
        if re.search(level_pattern, scholarship_level)
    ]
    if pattern and listed_levels and not re.search(pattern, scholarship_level):
        return False

    student_field = profile_value("field")
    student_field_groups = field_groups(student_field)
    scholarship_field_groups = field_groups(scholarship.get("field", ""))
    if (
        student_field_groups
        and scholarship_field_groups
        and student_field_groups.isdisjoint(scholarship_field_groups)
    ):
        return False

    gender = profile_value("gender").lower()
    scholarship_gender = str(scholarship.get("gender", "")).strip().lower()
    if gender in {"female", "male"} and scholarship_gender in {"female", "male"}:
        if gender != scholarship_gender:
            return False

    category = profile_value("category").lower()
    special_status = profile_value("special_status").lower()
    scholarship_name = str(scholarship.get("name", "")).lower()
    scholarship_category = str(scholarship.get("category", "")).lower()

    special_requirements = [
        ("swanath" in scholarship_name, "aicte swanath eligible welfare category"),
        ("beedi/cine/iomc/lsdm" in scholarship_name, "child of a covered worker (beedi/cine/mines)"),
        ("central armed police forces" in scholarship_name, "ward of capf or assam rifles personnel"),
        ("police personnel martyred" in scholarship_name, "ward of police personnel martyred in an attack"),
        ("ministry of railways" in scholarship_name, "ward of railway personnel"),
    ]
    if any(required and special_status != status for required, status in special_requirements):
        return False

    category_patterns = {
        "sc": r"\bsc\b|scheduled caste",
        "st": r"\bst\b|scheduled tribe",
        "obc": r"\bobc\b|other backward",
        "ebc": r"\bebc\b",
        "dnt": r"\bdnt\b|denotified",
        "ews": r"\bews\b|economically weaker",
        "minority": r"minority",
        "persons with disabilities": r"persons with disabilities|disability|disabled",
    }
    required_categories = [
        category_name
        for category_name, category_pattern in category_patterns.items()
        if re.search(category_pattern, str(scholarship.get("category", "")).lower())
    ]
    if category and category != "other" and required_categories:
        selected_category = next(
            (
                category_name
                for category_name, category_pattern in category_patterns.items()
                if re.search(category_pattern, category)
            ),
            category,
        )
        pm_cares_match = (
            "pm cares" in scholarship_category
            and special_status == "pm cares children scheme beneficiary"
        )
        if selected_category not in required_categories and not pm_cares_match:
            return False

    if "pm cares" in scholarship_category:
        sc_or_obc_profile = category in {"sc", "obc"}
        pm_cares_profile = special_status == "pm cares children scheme beneficiary"
        if not sc_or_obc_profile and not pm_cares_profile:
            return False

    student_state = profile_value("state").lower()
    scholarship_state = str(scholarship.get("state", "")).strip().lower()
    north_eastern_states = {
        "arunachal pradesh", "assam", "manipur", "meghalaya", "mizoram",
        "nagaland", "sikkim", "tripura",
    }
    if scholarship_state == "north eastern region" and student_state not in north_eastern_states:
        return False

    income_text = profile_value("income").replace(",", "")
    income_match = re.search(r"\d+(?:\.\d+)?", income_text)
    maximum_income_match = re.search(
        r"\d[\d,]*(?:\.\d+)?", str(scholarship.get("max_income", ""))
    )
    if income_match and maximum_income_match:
        if float(income_match.group()) > float(maximum_income_match.group().replace(",", "")):
            return False

    student_age_match = re.search(r"\d+(?:\.\d+)?", profile_value("age"))
    age_requirement = str(scholarship.get("age_requirement", "")).lower()
    age_limits = re.findall(r"\d+(?:\.\d+)?", age_requirement)
    if student_age_match and age_limits:
        student_age = float(student_age_match.group())
        limits = [float(limit) for limit in age_limits]
        if len(limits) >= 2 and not min(limits) <= student_age <= max(limits):
            return False
        if len(limits) == 1:
            if re.search(r"under|below|maximum|up to|at most", age_requirement) and student_age > limits[0]:
                return False
            if re.search(r"over|above|minimum|at least", age_requirement) and student_age < limits[0]:
                return False

    marks_text = profile_value("marks").lower()
    minimum_marks_match = re.search(
        r"\d+(?:\.\d+)?", str(scholarship.get("min_percentage", ""))
    )
    student_marks_match = re.search(r"\d+(?:\.\d+)?", marks_text)
    if (
        "%" in marks_text
        and minimum_marks_match
        and student_marks_match
        and float(student_marks_match.group()) < float(minimum_marks_match.group())
    ):
        return False

    return True


def deadline_details(value, today=None, application_start=None):
    deadline = pd.to_datetime(value, errors="coerce")
    if pd.isna(deadline):
        return {"deadline_status": "Not listed", "days_remaining": None}

    today = today or date.today()
    deadline_date = deadline.date()
    days_remaining = (deadline_date - today).days
    if days_remaining < 0:
        status = "Closed"
    elif application_start and not pd.isna(pd.to_datetime(application_start, errors="coerce")):
        start_date = pd.to_datetime(application_start).date()
        if start_date > today:
            status = "Opens soon"
        elif days_remaining <= 14:
            status = "Closing soon"
        else:
            status = "Open"
    elif days_remaining <= 14:
        status = "Closing soon"
    else:
        status = "Open"
    return {"deadline_status": status, "days_remaining": days_remaining}


def _matches_filters(scholarship, filters):
    def normalized(value):
        return str(value or "").strip().casefold()

    for filter_name, column in (
        ("provider_type", "provider_type"),
        ("field", "field"),
        ("level", "level"),
    ):
        expected = normalized(filters.get(filter_name))
        actual = normalized(scholarship.get(column, ""))
        if expected and expected not in {"all", "any"} and expected not in actual:
            return False

    deadline_filter = normalized(filters.get("deadline_status"))
    if deadline_filter and deadline_filter not in {"all", "any"}:
        status = deadline_details(
            scholarship.get("application_deadline"),
            application_start=scholarship.get("application_start"),
        )["deadline_status"]
        if deadline_filter == "closing" and status != "Closing soon":
            return False
        if deadline_filter == "open" and status not in {"Open", "Closing soon"}:
            return False
        if deadline_filter == "upcoming" and status != "Opens soon":
            return False
        if deadline_filter == "closed" and status != "Closed":
            return False

    return True


def _profile_match_score(scholarship, profile):
    checks = []
    education = str(profile.get("education", "")).strip().lower()
    scholarship_level = str(scholarship.get("level", "")).strip().lower()
    if education and scholarship_level and scholarship_level not in {"any", "not specified"}:
        education_terms = {
            "ug": ("ug", "undergraduate", "bachelor"),
            "diploma": ("diploma",),
            "pg": ("pg", "postgraduate", "master"),
            "phd": ("phd", "doctoral"),
        }.get(education, (education,))
        checks.append(any(term in scholarship_level for term in education_terms))

    student_field = field_groups(profile.get("field", ""))
    award_field = field_groups(scholarship.get("field", ""))
    if student_field and award_field:
        checks.append(not student_field.isdisjoint(award_field))

    gender = str(profile.get("gender", "")).strip().lower()
    award_gender = str(scholarship.get("gender", "")).strip().lower()
    if gender in {"female", "male"} and award_gender in {"female", "male"}:
        checks.append(gender == award_gender)

    category = str(profile.get("category", "")).strip().lower()
    award_category = str(scholarship.get("category", "")).strip().lower()
    if category and award_category and award_category not in {"any", "general", "not specified"}:
        checks.append(category in award_category or award_category in category)

    state = str(profile.get("state", "")).strip().lower()
    award_state = str(scholarship.get("state", "")).strip().lower()
    if state and award_state and award_state not in {"all india", "any", "not specified"}:
        checks.append(state == award_state or award_state == "north eastern region" and state in {
            "arunachal pradesh", "assam", "manipur", "meghalaya", "mizoram",
            "nagaland", "sikkim", "tripura",
        })

    return round(sum(checks) / len(checks) * 100, 2) if checks else None


def recommend_scholarships(user_input, top_n=5, profile=None, filters=None):

    # ----------------------------------------
    # Preprocess user input
    # ----------------------------------------

    filters = filters or {}
    processed_query = preprocess_text(user_input)

    # ----------------------------------------
    # Convert user input into TF-IDF vector
    # ----------------------------------------

    query_vector = vectorizer.transform(
        [processed_query]
    )

    # ----------------------------------------
    # Calculate cosine similarity
    # ----------------------------------------

    similarity_scores = cosine_similarity(
        query_vector,
        tfidf_matrix
    ).flatten()

    eligible_indexes = [
        index
        for index, scholarship in df.iterrows()
        if profile_is_eligible(scholarship, profile or {})
        and _matches_filters(scholarship, filters)
    ]
    profile_scores = {
        index: _profile_match_score(df.iloc[index], profile or {})
        for index in eligible_indexes
    }

    def ranking_score(index):
        similarity = float(similarity_scores[index]) * 100
        profile_score = profile_scores[index]
        return similarity if profile_score is None else similarity * 0.65 + profile_score * 0.35

    sort_by = str(filters.get("sort_by", "relevance")).lower()
    if sort_by == "deadline":
        def deadline_sort_key(index):
            details = deadline_details(
                df.iloc[index]["application_deadline"],
                application_start=df.iloc[index]["application_start"],
            )
            days_remaining = details["days_remaining"]
            return (
                days_remaining is None,
                days_remaining is None or days_remaining < 0,
                days_remaining if days_remaining is not None and days_remaining >= 0 else float("inf"),
            )

        eligible_indexes.sort(key=deadline_sort_key)
    else:
        eligible_indexes.sort(key=ranking_score, reverse=True)
    top_indexes = eligible_indexes[:top_n]

    # ----------------------------------------
    # Store recommendations
    # ----------------------------------------

    recommendations = []

    for index in top_indexes:

        scholarship = {

            "id": int(
                df.iloc[index]["id"]
            ),

            "name": df.iloc[index]["name"],

            "provider": df.iloc[index]["provider"],

            "provider_type":
                df.iloc[index]["provider_type"],

            "description":
                df.iloc[index]["description"],

            "field":
                df.iloc[index]["field"],

            "level":
                df.iloc[index]["level"],

            "gender":
                df.iloc[index]["gender"],

            "state":
                df.iloc[index]["state"],

            "category":
                df.iloc[index]["category"],

            "max_income":
                df.iloc[index]["max_income"],

            "min_percentage":
                df.iloc[index]["min_percentage"],

            "age_requirement":
                df.iloc[index]["age_requirement"],

            "application_start":
                df.iloc[index]["application_start"],

            "application_deadline":
                df.iloc[index]["application_deadline"],

            "similarity":
                round(
                    float(
                        similarity_scores[index]
                    ) * 100,
                    2
                ),
            "profile_match": profile_scores[index],
            "match_score": round(ranking_score(index), 2),
            **deadline_details(
                df.iloc[index]["application_deadline"],
                application_start=df.iloc[index]["application_start"],
            ),

            "application_url":
                (
                    "" if pd.isna(df.iloc[index]["application_url"])
                    else df.iloc[index]["application_url"]
                ),

            "guidelines_url":
                (
                    "" if pd.isna(df.iloc[index].get("guidelines_url", ""))
                    else df.iloc[index]["guidelines_url"]
                )
        }

        recommendations.append(
            scholarship
        )

    return recommendations


# ============================================================
# 10. TEST THE RECOMMENDATION SYSTEM
# ============================================================

if __name__ == "__main__":

    print("\n================================================")
    print("     AI GRANT & SCHOLARSHIP FINDER")
    print("================================================")

    user_query = input(
        "\nEnter your profile/interests: "
    )

    results = recommend_scholarships(
        user_query,
        top_n=5
    )

    print(
        "\n================ RECOMMENDED SCHOLARSHIPS ================\n"
    )

    if not results:

        print("No scholarships found.")

    else:

        for i, scholarship in enumerate(
            results,
            start=1
        ):

            print(
                f"{i}. {scholarship['name']}"
            )

            print(
                f"   Provider: "
                f"{scholarship['provider']}"
            )

            print(
                f"   Provider Type: "
                f"{scholarship['provider_type']}"
            )

            print(
                f"   Field: "
                f"{scholarship['field']}"
            )

            print(
                f"   Education Level: "
                f"{scholarship['level']}"
            )

            print(
                f"   Gender: "
                f"{scholarship['gender']}"
            )

            print(
                f"   State: "
                f"{scholarship['state']}"
            )

            print(
                f"   Category: "
                f"{scholarship['category']}"
            )

            print(
                f"   Maximum Income: "
                f"{scholarship['max_income']}"
            )

            print(
                f"   Minimum Percentage: "
                f"{scholarship['min_percentage']}"
            )

            print(
                f"   Age Requirement: "
                f"{scholarship['age_requirement']}"
            )

            print(
                f"   Match Score: "
                f"{scholarship['similarity']}%"
            )

            print(
                f"   Application Deadline: "
                f"{scholarship['application_deadline']}"
            )

            print(
                f"   Application URL: "
                f"{scholarship['application_url']}"
            )

            print(
                "\n   Description:"
            )

            print(
                f"   {scholarship['description']}"
            )

            print("\n" + "-" * 70)
