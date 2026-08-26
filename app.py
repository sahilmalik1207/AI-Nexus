"""
AI Orbit — public read-only viewer for the ingested dataset.

Deployed on Streamlit Community Cloud (free tier), fully accessible without
any login/signup, satisfying the trial's "Live deployment URL" requirement.

Run locally: streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"

st.set_page_config(page_title="AI Orbit — Ecosystem Graph", page_icon="🪐", layout="wide")


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

st.title("🪐 AI Orbit — Ecosystem Data Ingestion Pipeline")
st.caption("Discovery → Extraction → Cleaning → Normalization → Deduplication → Classification → Relationship Mapping → Validation")

if not entities:
    st.warning("No data found yet. Run `python run.py` to populate data/entities.json first.")
    st.stop()

# --- Top-level stats ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Entities", len(entities))
col2.metric("Total Relationships", len(relationships))
col3.metric("Entity Types", len({e["entity_type"] for e in entities}))
col4.metric("Quarantined (last run)", report.get("quarantined_entities", 0))

st.divider()

df = pd.DataFrame(entities)

# --- Sidebar filters ---
st.sidebar.header("Filters")
type_options = sorted(df["entity_type"].unique())
selected_types = st.sidebar.multiselect("Entity type", type_options, default=type_options)
search_query = st.sidebar.text_input("Search name/description")

filtered = df[df["entity_type"].isin(selected_types)]
if search_query:
    mask = (
        filtered["name"].str.contains(search_query, case=False, na=False)
        | filtered["description"].str.contains(search_query, case=False, na=False)
    )
    filtered = filtered[mask]

# --- Distribution chart ---
st.subheader("Entities by Type")
type_counts = filtered["entity_type"].value_counts()
st.bar_chart(type_counts)

# --- Table ---
st.subheader(f"Entities ({len(filtered)})")
display_cols = ["name", "entity_type", "description", "url", "categories"]
st.dataframe(filtered[display_cols], use_container_width=True, height=420)

# --- Relationships ---
st.divider()
st.subheader(f"Relationships ({len(relationships)})")
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

st.divider()
with st.expander("Last pipeline run report"):
    st.json(report)
