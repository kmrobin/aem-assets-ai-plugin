# AEM Assets Deep Content Search & Upload Plugin

A Coworker plugin providing two skills for AEM DAM operations that go beyond native AEM capabilities:

1. **aem-assets-deep-content-search** — Semantic search inside document content (PDF/DOCX body text) via text renditions, with automatic fallback when AEM metadata search returns nothing.

2. **aem-assets-upload-versioning** — Correct 3-step binary upload protocol for AEM as a Cloud Service, supporting both new assets and versioning existing assets.

## Installation

Add this plugin to your Coworker via the GitHub integration:
1. Push this repository to GitHub
2. In Coworker settings, add the GitHub repo as a plugin source
3. Both skills will be available automatically

## Plugin Structure

```
plugin.json                          # Plugin manifest
skills/
├── aem-assets-deep-content-search/
│   ├── SKILL.md                     # Skill definition
│   └── scripts/
│       └── deep_content_search.py   # Reference implementation
└── aem-assets-upload-versioning/
    └── SKILL.md                     # Skill definition
```

## Prerequisites

- AEM as a Cloud Service author instance
- `aem` API service configured in the Coworker agent manifest
- Text extraction enabled on the AEM instance (default for AEMaaCS)
