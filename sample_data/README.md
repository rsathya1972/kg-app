# Sample Data

This directory contains sample documents for testing the Ontology Graph Studio ingestion pipeline.

## Structure

```
sample_data/
├── raw/          # Raw source documents (PDF, DOCX, TXT)
└── README.md
```

## Usage

Place source documents in `sample_data/raw/` and use the **Upload Documents** module in the UI to ingest them.

Supported formats (planned):
- `.txt` — plain text
- `.pdf` — PDF documents
- `.docx` — Microsoft Word
- `.md` — Markdown

## Sample Documents

The `raw/placeholder.txt` file is included as a starter. Replace it with real domain documents to begin entity extraction and ontology building.
