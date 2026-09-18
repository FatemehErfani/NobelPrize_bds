import requests
import pandas as pd
import streamlit as st
import plotly.express as px


# =========================================================
# 1. Page settings
# =========================================================

st.set_page_config(
    page_title="Nobel Prize Dashboard",
    page_icon="🏆",
    layout="wide"
)


# =========================================================
# 2. Page title
# =========================================================

st.title("🏆 Nobel Prize Dashboard")

st.caption(
    "Female Nobel laureates across years, countries, and categories"
)


# =========================================================
# 3. Get data from Nobel Prize API
# =========================================================

@st.cache_data
def get_nobel_data():

    url = "https://api.nobelprize.org/2.1/laureates"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    all_laureates = []

    offset = 0
    limit = 100

    while True:

        response = requests.get(
            url,
            params={
                "limit": limit,
                "offset": offset
            },
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        laureates = data.get("laureates", [])

        if not laureates:
            break

        all_laureates.extend(laureates)

        if len(laureates) < limit:
            break

        offset += limit

    return all_laureates


# =========================================================
# 4. Error handling
# =========================================================

try:

    laureates = get_nobel_data()

except requests.exceptions.RequestException:

    st.error(
        "The Nobel Prize API is currently unavailable."
    )

    st.stop()

except Exception:

    st.error(
        "Something went wrong while loading the Nobel Prize data."
    )

    st.stop()


if len(laureates) == 0:

    st.warning(
        "The API did not return any Nobel Prize laureates."
    )

    st.stop()


# =========================================================
# 5. Convert API data into a DataFrame
# =========================================================

rows = []

for laureate in laureates:

    # Keep only individual laureates
    if laureate.get("gender") not in ["male", "female"]:
        continue

    # Unique laureate ID
    laureate_id = laureate.get("id")

    # Laureate name
    name = (
        laureate
        .get("knownName", {})
        .get("en", "Unknown")
    )

    # Gender
    gender = laureate.get("gender")

    # Birth country
    birth_country = (
        laureate
        .get("birth", {})
        .get("place", {})
        .get("country", {})
        .get("en", "Unknown")
    )

    # Nobel prizes received by the laureate
    nobel_prizes = laureate.get(
        "nobelPrizes",
        []
    )

    for prize in nobel_prizes:

        category = (
            prize
            .get("category", {})
            .get("en")
        )

        award_year = prize.get("awardYear")

        if category and award_year:

            rows.append(
                {
                    "laureate_id": laureate_id,
                    "name": name,
                    "gender": gender,
                    "birth_country": birth_country,
                    "category": category,
                    "year": int(award_year)
                }
            )


df = pd.DataFrame(rows)


# =========================================================
# 6. Keep only data from 2000 onwards
# =========================================================

df = df[
    df["year"] >= 2000
].copy()


# =========================================================
# 7. Remove incomplete records
# =========================================================

df = df.dropna(
    subset=[
        "category",
        "year",
        "gender"
    ]
)


# =========================================================
# 8. Sidebar filters
# =========================================================

st.sidebar.header("Explore the data")


# ---------------------------------------------------------
# Year filter
# ---------------------------------------------------------

min_year = 2000
max_year = int(df["year"].max())

selected_years = st.sidebar.slider(
    "Choose a year range:",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year)
)


# ---------------------------------------------------------
# Birth country filter
# ---------------------------------------------------------

countries = sorted(
    df["birth_country"]
    .dropna()
    .unique()
)

selected_countries = st.sidebar.multiselect(
    "Select birth country:",
    countries,
    default=[]
)


# ---------------------------------------------------------
# Category filter
# ---------------------------------------------------------

categories = sorted(
    df["category"]
    .dropna()
    .unique()
)

selected_categories = st.sidebar.multiselect(
    "Select category:",
    categories,
    default=[]
)


# =========================================================
# 9. Apply filters
# =========================================================

filtered_df = df[
    (df["year"] >= selected_years[0]) &
    (df["year"] <= selected_years[1])
].copy()


# Apply birth country filter
if selected_countries:

    filtered_df = filtered_df[
        filtered_df["birth_country"].isin(
            selected_countries
        )
    ].copy()


# Apply category filter
if selected_categories:

    filtered_df = filtered_df[
        filtered_df["category"].isin(
            selected_categories
        )
    ].copy()


# =========================================================
# 10. Keep only female laureates
# =========================================================

female_df = filtered_df[
    filtered_df["gender"] == "female"
].copy()


# =========================================================
# 11. KPI calculations
# =========================================================

# Number of distinct female laureates
female_laureates = female_df[
    "laureate_id"
].nunique()


# Number of birth countries
birth_countries = female_df[
    "birth_country"
].nunique()


# ---------------------------------------------------------
# Peak year
# ---------------------------------------------------------

female_by_year = (
    female_df
    .groupby("year")["laureate_id"]
    .nunique()
)


if len(female_by_year) > 0:

    peak_year = female_by_year.idxmax()

    peak_year_count = female_by_year.max()

else:

    peak_year = "N/A"

    peak_year_count = 0


# ---------------------------------------------------------
# Top category
# ---------------------------------------------------------

female_by_category = (
    female_df
    .groupby("category")["laureate_id"]
    .nunique()
)


if len(female_by_category) > 0:

    top_category = female_by_category.idxmax()

else:

    top_category = "N/A"


# =========================================================
# 12. KPI cards
# =========================================================

col1, col2, col3, col4 = st.columns(4)


with col1:
    st.metric(
        label="Female laureates",
        value=female_laureates
    )


with col2:
    st.metric(
        label="Birth countries",
        value=birth_countries
    )


with col3:
    st.metric(
        label="Peak year",
        value=peak_year,
        delta=f"{peak_year_count} laureates"
    )


with col4:
    st.metric(
        label="Top category",
        value=top_category
    )


st.divider()


# =========================================================
# 13. Prepare yearly data
# =========================================================

year_result = (
    female_df
    .groupby("year")["laureate_id"]
    .nunique()
    .reset_index(
        name="female_count"
    )
    .sort_values("year")
)


# =========================================================
# 14. Create the chart
# =========================================================

fig_year = px.line(
    year_result,
    x="year",
    y="female_count",
    markers=True,
    labels={
        "year": "Year",
        "female_count": "Female laureates"
    },
    title="Female Nobel laureates over time"
)

fig_year.update_layout(
    hovermode="x unified",
    yaxis=dict(
        rangemode="tozero"
    )
)

st.plotly_chart(
    fig_year,
    use_container_width=True
)

# =========================================================
# 15. Data source
# =========================================================

st.caption(
    "Data source: Nobel Prize API | Period: 2000–present"
)