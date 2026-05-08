# Architecture Overview

## Application Flow

```text
Upload
  ↓
Cleaning
  ↓
Validation
  ↓
Column Mapping
  ↓
Join Diagnostics
  ↓
Analytics
  ↓
Reporting / Export
```

---

## Core Modules

### app.py
Main Streamlit UI and orchestration layer.

### services/pipeline_service.py
Central processing pipeline coordination.

### data_cleaning/
Cleaning, normalization, and validation logic.

### analytics/
Business analysis modules:
- Sales
- Inventory
- Profitability

### reporting/
Excel export generation and visualization helpers.

### utils/
Shared utility modules:
- column mapping
- joins
- preflight scoring
- models

---

## Design Goals

- Stable business-first workflows
- Explainable diagnostics
- Low-friction Excel integration
- Modular extensibility
- Single-user desktop deployment