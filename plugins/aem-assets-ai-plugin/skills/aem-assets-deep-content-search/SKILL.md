---
name: aem-assets-deep-content-search
description: >
  Search inside document content (PDF/DOCX body text) using extracted text
  renditions when AEM metadata search returns no results. Two-phase approach:
  first tries AEM native metadata search, then falls back to fetching
  cqdam.text.txt renditions and applying AI-powered semantic matching.
  Triggers: find documents about, search PDFs for keyword, which files mention,
  find assets containing, search inside documents, full text search, content search,
  locate files about.
type: skill
license: Apache-2.0
metadata:
  author: KM Robin
  version: "1.0"
---

# AEM Assets Deep Content Search

> **Tools:** `api_request` (service="aem"), `bash`, `execute_code`, `read`

## Purpose

Search for documents (PDFs, Word docs, etc.) in AEM Assets by keyword or phrase,
using a two-phase approach:

1. **Phase 1 — AEM Native Search:** Use the AEM Assets Search API with HYBRID/FULLTEXT
   mode to find assets whose metadata (title, description, tags, filename) matches
   the user's query.

2. **Phase 2 — Text Rendition Semantic Search (fallback):** If Phase 1 returns 0 results,
   automatically fetch the extracted-text renditions (`cqdam.text.txt`) of all matching
   documents in the target folder and perform AI-powered semantic matching against the
   full document content.

This skill enables users to find documents by content keywords without needing to know
about rendition paths or AEM internals. They simply say "find PDFs about X in folder Y."

## Trigger Phrases

- "find documents about X"
- "search PDFs for keyword X"
- "which files mention X"
- "find assets containing X"
- "search inside documents for X"
- "locate files about X in folder Y"
- Any request to find DAM assets by content/body keywords

## Prerequisites

- AEM Author instance (Cloud Service) with text extraction enabled
  (default for PDF, DOCX, PPTX, XLSX via Apache Tika)
- Text renditions must exist at:
  `<asset-path>/jcr:content/renditions/cqdam.text.txt`

## Workflow

### Step 1: Resolve AEM Repository

Use the standard repository discovery to identify the AEM author instance.
See `aem-assets-discovery` skill for the discovery script pattern.

### Step 2: Determine Search Scope

Extract from the user's request:
- **keyword/phrase**: the semantic concept to search for
- **folder**: the DAM path to search within (default: `/content/dam`)
- **format filter**: file type (default: `application/pdf` for PDF-specific
  requests; omit for "all documents")

Supported format mappings for document search:
| User says | MIME filter |
|-----------|------------|
| PDF, pdfs | `application/pdf` |
| Word, docx | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| PowerPoint, pptx | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| documents, files | use `startsWith` on multiple doc MIME families |

### Step 3: AEM Native Search (Phase 1)

Build and execute an AEM Assets Search API call:

```json
{
  "query": [
    {"term": {"repositoryMetadata.repo:ancestors": ["<folder-path>"]}},
    {"term": {"repositoryMetadata.dc:format": ["<mime-type>"]}},
    {"match": {"text": "<user-keyword>", "mode": "HYBRID"}}
  ],
  "limit": 20,
  "projectedFields": {
    "includes": [
      "repositoryMetadata.repo:name",
      "repositoryMetadata.repo:path",
      "assetMetadata.dc:title",
      "repositoryMetadata.dc:format",
      "repositoryMetadata.repo:size",
      "repositoryMetadata.repo:modifyDate"
    ]
  }
}
```

**If results are found:** Present them and stop. AEM's metadata search was sufficient.

**If 0 results:** Proceed to Phase 2 automatically. Inform the user:
> "No results found via metadata search. Searching inside document content..."

### Step 4: List All Matching Documents (for Phase 2)

Run a structural-only search (no `match` clause) to get all documents of the
requested type in the folder:

```json
{
  "query": [
    {"term": {"repositoryMetadata.repo:ancestors": ["<folder-path>"]}},
    {"term": {"repositoryMetadata.dc:format": ["<mime-type>"]}}
  ],
  "limit": 50,
  "projectedFields": {
    "includes": [
      "repositoryMetadata.repo:name",
      "repositoryMetadata.repo:path",
      "repositoryMetadata.dc:format"
    ]
  }
}
```

Paginate with cursor if more than 50 documents exist (up to 200 max for
performance). If 0 documents exist at all, report "No documents of this type
found in the specified folder."

### Step 5: Fetch Text Renditions

For each document found in Step 4, fetch the extracted text rendition:

```
GET https://<aem-host><asset-repo-path>/jcr:content/renditions/cqdam.text.txt
```

Use concurrent fetching (ThreadPoolExecutor, max 10 workers) for performance.
Handle 404s gracefully — some assets may not have text renditions (e.g., scanned
PDFs without OCR).

### Step 6: Semantic Matching

Apply AI reasoning to match the user's keyword/phrase against the extracted text.
Use a tiered matching strategy:

1. **Exact match**: Does the text contain the exact phrase?
2. **Keyword co-occurrence**: Do all significant words appear in proximity?
3. **Semantic match**: Does the content discuss the same concept even if
   different words are used?

For each document, assign a relevance tier:
- **EXACT**: Phrase appears verbatim in the text
- **STRONG**: All key terms present in close proximity or the concept is
  clearly discussed
- **PARTIAL**: Some terms match or a related concept is present

### Step 7: Present Results

Show results grouped by relevance tier. For each match, include:
- File name and path
- Relevance tier (EXACT / STRONG / PARTIAL)
- A snippet (50-100 words) showing the matching context

Example output:
```
## Deep Content Search Results for "optimism about page length"

### EXACT MATCH
1. **sample-local-pdf.pdf**
   Path: /content/dam/moe/sample-local-pdf.pdf
   > "...three short pages if you're optimistic. Is it the same as saying
   > 'three long minutes', knowing that all minutes are the same duration..."

### NO ADDITIONAL MATCHES
(Only 1 of 9 PDFs contained relevant content)
```

## Performance Considerations

- **Document limit**: Process up to 200 documents per search. If the folder
  contains more, inform the user and suggest narrowing the folder scope.
- **Concurrent fetching**: Fetch text renditions in parallel (10 workers).
- **Text size**: Truncate individual document text at 50,000 characters for
  analysis. Most extracted text is well under this.
- **Caching**: Within a single conversation, cache fetched text renditions
  to avoid re-fetching on refined queries.

## Limitations to Communicate

- Only works for documents with text extraction renditions (not scanned
  image-only PDFs without OCR)
- Searches the folder specified (including subfolders via `repo:ancestors`)
- For very large repositories (1000+ documents), recommend narrowing scope

## Error Handling

| Condition | Action |
|-----------|--------|
| Text rendition returns 404 | Skip asset, note in results as "no text extraction available" |
| AEM returns 401/403 | Report permission issue and stop |
| Folder path doesn't exist | Report invalid path |
| All renditions are 404 | Report that text extraction is not enabled for these assets |
