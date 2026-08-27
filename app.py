"""
AI Nexus — public AI ecosystem intelligence platform.

Deployed on Streamlit Community Cloud (free tier), fully accessible without
any login/signup, satisfying the trial's "Live deployment URL" requirement.

Run locally: streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(
    page_title="AI Nexus — AI Intelligence Platform",
    page_icon="🤖",
    layout="wide"
)


@st.cache_data(ttl=300)
def load_data():
    entities_path = DATA_DIR / "entities.json"
    relationships_path = DATA_DIR / "relationships.json"
    report_path = DATA_DIR / "run_report.json"

    entities = json.loads(entities_path.read_text()) if entities_path.exists() else []
    relationships = json.loads(relationships_path.read_text()) if relationships_path.exists() else []
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    return entities, relationships, report


entities, relationships, report = load_data()

st.title("🤖 AI Nexus")

st.subheader("AI Ecosystem Intelligence Platform")

st.caption(
    "Discover, organize and analyze AI ecosystem data from "
    "multiple sources in one intelligent platform."
)
st.caption(
    "📡 Collect  →  🧹 Clean  →  🔍 Deduplicate  →  "
    "✨ Enrich  →  🔗 Connect  →  📊 Analyze"
)

if not entities:
    st.warning("No data found yet. Run `python run.py` to populate data/entities.json first.")
    st.stop()

# --- Top-level stats ---
# --- AI Nexus Overview ---
st.subheader("📊 Platform Overview")

total_entities = len(entities)
total_relationships = len(relationships)
entity_types = len({e["entity_type"] for e in entities})
quarantined = report.get("quarantined_entities", 0)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🧠 Knowledge Entities",
        value=total_entities
    )

with col2:
    st.metric(
        label="🔗 Connected Relationships",
        value=total_relationships
    )

with col3:
    st.metric(
        label="📂 AI Categories",
        value=entity_types
    )

with col4:
    st.metric(
        label="⚠️ Data Quality Issues",
        value=quarantined
    )

st.divider()

df = pd.DataFrame(entities)

# --- Sidebar filters ---
st.sidebar.header("🤖 AI Nexus Controls")
st.sidebar.caption("Explore and filter the AI ecosystem dataset")
type_options = sorted(df["entity_type"].unique())
selected_types = st.sidebar.multiselect(
    "🏷️ Select AI Categories",
    type_options,
    default=type_options
)

search_query = st.sidebar.text_input(
    "🔎 Search AI entities"
)

filtered = df[df["entity_type"].isin(selected_types)]
if search_query:
    mask = (
        filtered["name"].str.contains(search_query, case=False, na=False)
        | filtered["description"].str.contains(search_query, case=False, na=False)
    )
    filtered = filtered[mask]


# --- AI Ecosystem Insights ---
st.subheader("📈 AI Ecosystem Insights")

type_counts = filtered["entity_type"].value_counts()

if not type_counts.empty:

    col_chart, col_insights = st.columns([2, 1])

    with col_chart:
        st.caption("Distribution of AI entities across categories")
        st.bar_chart(type_counts)

    with col_insights:
        st.markdown("### 🧠 Quick Insights")

        top_category = type_counts.index[0]
        top_category_count = type_counts.iloc[0]

        percentage = (
            top_category_count / len(filtered) * 100
            if len(filtered) > 0
            else 0
        )

        st.metric(
            "🏆 Largest Category",
            top_category
        )

        st.metric(
            "📊 Category Share",
            f"{percentage:.1f}%"
        )

        st.metric(
            "🔢 Visible Entities",
            len(filtered)
        )

else:
    st.info("No entities match the selected filters.")

# --- AI Entity Explorer ---
st.divider()

st.subheader("🔎 AI Entity Explorer")

st.caption(
    "Browse the AI ecosystem dataset and explore organizations, "
    "tools, technologies and other connected entities."
)

display_cols = [
    "name",
    "entity_type",
    "description",
    "url",
    "categories"
]

if not filtered.empty:

    explorer_col, summary_col = st.columns([3, 1])

    with explorer_col:

        st.dataframe(
            filtered[display_cols],
            use_container_width=True,
            height=420,
            hide_index=True
        )

    with summary_col:

        st.markdown("### 📋 Dataset Summary")

        st.metric(
            "Visible Results",
            len(filtered)
        )

        unique_categories = filtered["entity_type"].nunique()

        st.metric(
            "Entity Types",
            unique_categories
        )

        if "categories" in filtered.columns:

            non_empty_categories = filtered["categories"].notna().sum()

            st.metric(
                "Categorized Entities",
                non_empty_categories
            )

else:

    st.warning(
        "No entities were found with the current filters. "
        "Try selecting more categories or changing your search."
    )

# --- Relationships ---
st.divider()
st.subheader(f"🔗 Relationship Explorer ({len(relationships)})")
if relationships:
    rel_df = pd.DataFrame(relationships)
    id_to_name = {e["id"]: e["name"] for e in entities}
    rel_df["source_name"] = rel_df["source_id"].map(id_to_name)
    rel_df["target_name"] = rel_df["target_id"].map(id_to_name)
    st.dataframe(
        rel_df[["source_name", "relation_type", "target_name", "confidence", "evidence"]],
        use_container_width=True, height=300,
    )
else:
    st.info("No relationships extracted in the last run.")

