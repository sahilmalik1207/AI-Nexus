# AI Nexus — AI Ecosystem Intelligence Platform

AI Nexus is a data ingestion and intelligence platform that collects, processes, organizes, and explores information from across the AI ecosystem.

The platform transforms data from multiple sources into a structured **entity and relationship graph**, allowing users to explore AI repositories, models, tools, companies, tasks, news, and other AI-related entities.

## 🚀 Features

* 📡 Multi-source AI data collection
* 🧹 Data cleaning and normalization
* 🔍 Entity deduplication
* 🏷️ Entity classification and categorization
* 🔗 Relationship mapping
* ✅ Data validation and quarantine reporting
* 📊 Interactive Streamlit dashboard
* 🔎 Search and category filtering
* 📈 AI ecosystem insights and analytics

---

## 🏗️ Data Pipeline

```text
Discovery → Extraction → Cleaning → Normalization → Deduplication
→ Classification → Relationship Mapping → Validation
```

Each stage processes the data before it is stored as structured entities and relationships.

## 📁 Project Structure

```text
src/
  config.py
  http_client.py

  models/
    entity.py

  extraction/
    github_extractor.py
    huggingface_extractor.py
    tasks_extractor.py
    collections_extractor.py
    news_extractor.py
    youtube_extractor.py
    curated_extractor.py

  processing/
    cleaning.py
    deduplication.py
    classification.py
    relationships.py
    validation.py

data/
  entities.json
  relationships.json
  run_report.json

run.py
app.py
```

---

# 🤖 AI Nexus Dashboard

The Streamlit dashboard provides an interactive interface for exploring the AI ecosystem.

### Platform Overview

The dashboard displays:

* 🧠 Knowledge Entities
* 🔗 Connected Relationships
* 📂 AI Categories
* ⚠️ Data Quality Issues

### AI Ecosystem Insights

Users can view the distribution of entities across different AI categories and identify:

* Largest category
* Category share
* Number of visible entities

### AI Entity Explorer

Users can:

* Search AI entities
* Filter by category
* View descriptions and URLs
* Explore available categories

### Relationship Explorer

The platform maps relationships between entities and displays:

* Source entity
* Relationship type
* Target entity
* Confidence score
* Supporting evidence

---

# 📊 Current Dataset

The current dataset contains approximately:

* **354 Knowledge Entities**
* **177 Connected Relationships**
* **12 AI Entity Categories**
* **0 Data Quality Issues**

Entity categories include:

* Repository
* Model
* MCP
* Task
* Collection
* Company
* Tool
* News
* Robot
* Device
* Personal
* Creative

---

# 🧠 Technical Design

## Deterministic Entity IDs

Entities use deterministic identifiers generated from their entity type and canonical key.

This helps maintain consistency between pipeline runs and improves duplicate detection.

## Data Deduplication

The pipeline uses multiple levels of duplicate detection:

1. Exact entity ID matching
2. Normalized URL matching
3. Fuzzy name matching

## Relationship Extraction

Relationships between entities are extracted using deterministic rules and text matching.

Each relationship can contain supporting evidence to make the relationship easier to inspect and validate.

## Data Validation

Invalid entities and relationships are quarantined rather than silently discarded.

Validation results are recorded in:

```text
data/run_report.json
```

---

# ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/sahilmalik1207/AI-Nexus.git
cd AI-Nexus
```

Create a virtual environment.

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ Running the Data Pipeline

Run the complete pipeline:

```bash
python run.py
```

Skip specific sources:

```bash
python run.py --skip youtube,news
```

Enable verbose logging:

```bash
python run.py --verbose
```

The pipeline generates data files inside:

```text
data/
```

including:

* `entities.json`
* `relationships.json`
* `run_report.json`

---

# 🖥️ Running the Dashboard

Start the Streamlit application:

```bash
python -m streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

---

# 🧪 Running Tests

```bash
pytest tests/ -v
```

---

# 🛠️ Technologies Used

* Python
* Streamlit
* Pandas
* Pydantic
* GitHub API
* Hugging Face API
* RSS Feeds
* YouTube Data API

---

# 📌 Future Improvements

* Interactive graph visualization
* User authentication
* Advanced relationship analytics
* Real-time data updates
* AI-powered entity classification
* Advanced search capabilities
* Dashboard export functionality
* Cloud deployment automation

---

# 🙏 Credits

AI Nexus was developed by extending and customizing an existing AI ecosystem data ingestion project.

The project was rebranded and enhanced with a redesigned **AI Nexus dashboard**, improved entity exploration, ecosystem insights, filtering, and relationship visualization.

Original project inspiration/source:

https://github.com/vishal24241/Ai-Orbit-Pipeline

## Developer

**Sahil Malik**

GitHub: https://github.com/sahilmalik1207
