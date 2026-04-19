# Canonical Backend Contracts

## Purpose

This directory serves as the **single source of truth** for all core data structures used throughout the Gabes Copilot backend.

To maintain a clean and reliable architecture, avoid defining schemas inside individual agents. Instead, all agents and orchestrators should import and validate against the central models defined here. This ensures that every layer of the system speaks the exact same data language.

## Core Objects Defined

The domain models are separated logically by their operational stage in the pipeline:

### 1. `signals.py`
The foundational data extraction tier.
* **`RawSignal`**: The unprocessed input (e.g., raw text or payload) prior to analysis.
* **`EnrichedSignal`**: The standard structured object populated with extracted classifications (normalization, location, timestamp, domain, event type, severity).

### 2. `events.py`
The logical grouping of incident behavior.
* **`RegionalEvent`**: Aggregation of multiple related signals within a specific region, detailing an ongoing incident. 

### 3. `cases.py`
The operational object for delegation and action tracking.
* **`Case`**: An actionable entity assigned to an actor, tying together structured events and raw signals while maintaining status, priority, and clustering metadata.
	- Includes `priority_score`, `embedding`, `embedding_model`, `embedding_dim`, `embedding_count`, timestamps, and rationale fields.

### 4. `plans.py`
The downstream executive outcome deliverables.
* **`Insight`**: Abstracted summaries derived from deep pipeline analysis.
* **`Plan`**: Concrete, sequenced action items linked back to established cases.

## Persistence Note

In the current implementation, brief and plan outputs are persisted as JSON artifacts through `StorageService` from their orchestrators, while core schema contracts remain in this directory.
