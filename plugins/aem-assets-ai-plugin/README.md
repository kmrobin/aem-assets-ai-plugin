# AEM Assets AI Plugin

AEM DAM deep content search (text rendition semantic search) and proper binary upload with versioning support for AEM as a Cloud Service.

## Available Skills

### aem-assets-deep-content-search

Search inside document content (PDF/DOCX body text) using text renditions when AEM metadata search returns no results. Automatically fetches `cqdam.text.txt` renditions and applies AI semantic matching.

**Quick Start:**
```bash
# Say: "Find PDFs about optimism regarding page length in /content/dam/moe"
# Or: "Search documents for keyword 'sustainability' in /content/dam/marketing"
```

### aem-assets-upload-versioning

Upload files to AEM DAM using the correct 3-step binary upload protocol. Supports new assets and versioning.

**Quick Start:**
```bash
# Say: "Upload this edited PDF back to AEM as a new version"
# Or: "Replace the file at /content/dam/moe/sample.pdf with the edited version"
```

## Prerequisites

- AEM as a Cloud Service author instance
- `aem` API service configured
- Text extraction enabled (default for AEMaaCS)
