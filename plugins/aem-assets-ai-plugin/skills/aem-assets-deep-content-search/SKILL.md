---
name: aem-assets-deep-content-search
description: >
  Search inside document content (PDF/DOCX body text) using extracted text
  renditions when AEM metadata search returns no results. Two-phase approach
  that first tries AEM native metadata search, then falls back to fetching
  cqdam.text.txt renditions and applying AI-powered semantic matching.
  Triggers: find documents about, search PDFs for keyword, which files mention,
  find assets containing, search inside documents, full text search, content search.
type: skill
license: Apache-2.0
metadata:
  author: KM Robin
  version: "1.0"
---

# AEM Assets Deep Content Search

| | |
|---|---|
| **ID** | `aem-assets-deep-content-search` |
| **Description** | Searches document body text via text renditions when metadata search fails. |

## Tools

- `api_request` (service="aem")
- `execute_code`
- `bash`

## Workflow

### Phase 1: AEM Native Search

Use AEM Assets Search API with HYBRID mode to search metadata.

If results found, present them and stop. If 0 results, proceed to Phase 2.

### Phase 2: Text Rendition Semantic Search

1. List all documents of the requested type in the target folder (structural search, no match clause).
2. Fetch text renditions for each document at `<asset-path>/jcr:content/renditions/cqdam.text.txt`.
3. Apply AI semantic matching against the extracted text.
4. Present results grouped by relevance tier (EXACT / STRONG / PARTIAL).

### Supported Formats

| User says | MIME filter |
|-----------|------------|
| PDF | `application/pdf` |
| Word, docx | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| PowerPoint | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |

### Performance

- Document limit: 200 per search
- Concurrent fetching: 10 workers
- Text truncation: 50,000 characters per document

### Error Handling

| Condition | Action |
|-----------|--------|
| Text rendition 404 | Skip asset |
| AEM 401/403 | Report permission issue |
| Folder not found | Report invalid path |
