# AEM Assets AI Plugin

A Coworker marketplace plugin providing two skills for AEM DAM operations:

1. **aem-assets-deep-content-search** — Semantic search inside document content (PDF/DOCX body text) via text renditions, with automatic fallback when AEM metadata search returns nothing.

2. **aem-assets-upload-versioning** — Correct 3-step binary upload protocol for AEM as a Cloud Service, supporting both new assets and versioning existing assets.

## Installation

Add this repository as a marketplace in your Coworker settings.

## Repository Structure

```
.claude-plugin/
└── marketplace.json          ← Required by Coworker
skills/
├── aem-assets-deep-content-search/
│   ├── SKILL.md
│   └── scripts/
│       └── deep_content_search.py
└── aem-assets-upload-versioning/
    └── SKILL.md
README.md
```

## Prerequisites

- AEM as a Cloud Service author instance
- `aem` API service configured in the Coworker agent manifest
- Text extraction enabled on the AEM instance (default for AEMaaCS)
