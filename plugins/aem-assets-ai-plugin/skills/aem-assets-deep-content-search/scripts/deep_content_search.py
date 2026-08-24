"""
AEM Assets Deep Content Search — Reference Implementation

This script demonstrates the Phase 2 (text rendition semantic search) workflow.
It is used by the skill when AEM's native metadata search returns 0 results.

Usage (inside execute_code):
    Invoked programmatically within the skill workflow. Not a standalone CLI tool.
"""

# --- Configuration ---
MAX_DOCUMENTS = 200        # Max docs to process per search
MAX_WORKERS = 10           # Concurrent text rendition fetches
MAX_TEXT_LENGTH = 50000    # Truncate extracted text at this length
SNIPPET_CONTEXT = 150      # Characters of context around a match


def build_structural_query(folder_path: str, mime_types: list[str]) -> dict:
    """Build a structural-only AEM search body (no text match)."""
    query = [{"term": {"repositoryMetadata.repo:ancestors": [folder_path]}}]
    if len(mime_types) == 1:
        query.append({"term": {"repositoryMetadata.dc:format": mime_types}})
    else:
        # Multiple MIME types → OR
        query.append({"or": [
            {"term": {"repositoryMetadata.dc:format": [m]}} for m in mime_types
        ]})
    return {
        "query": query,
        "limit": 50,
        "projectedFields": {
            "includes": [
                "repositoryMetadata.repo:name",
                "repositoryMetadata.repo:path",
                "repositoryMetadata.dc:format",
            ]
        }
    }


def text_rendition_url(aem_host: str, asset_path: str) -> str:
    """Construct the URL for an asset's extracted text rendition."""
    return f"{aem_host}{asset_path}/jcr:content/renditions/cqdam.text.txt"


def score_relevance(text: str, keyword: str) -> tuple[str, str]:
    """
    Score the relevance of document text against a keyword/phrase.
    Returns (tier, snippet).
    
    Tiers:
      EXACT    — phrase appears verbatim
      STRONG   — all significant words present within ~500 chars of each other
      PARTIAL  — majority of words present somewhere in text
      NONE     — no meaningful match
    """
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    # 1. Exact match
    idx = text_lower.find(keyword_lower)
    if idx >= 0:
        start = max(0, idx - SNIPPET_CONTEXT)
        end = min(len(text), idx + len(keyword) + SNIPPET_CONTEXT)
        snippet = text[start:end].replace("\n", " ").strip()
        return "EXACT", snippet
    
    # 2. Keyword co-occurrence (proximity)
    words = [w for w in keyword_lower.split() if len(w) > 2]  # skip short words
    if not words:
        return "NONE", ""
    
    word_positions = {}
    for w in words:
        pos = text_lower.find(w)
        if pos >= 0:
            word_positions[w] = pos
    
    found_ratio = len(word_positions) / len(words)
    
    if found_ratio == 1.0:
        # All words found — check proximity
        positions = list(word_positions.values())
        span = max(positions) - min(positions)
        center = (min(positions) + max(positions)) // 2
        start = max(0, center - SNIPPET_CONTEXT)
        end = min(len(text), center + SNIPPET_CONTEXT)
        snippet = text[start:end].replace("\n", " ").strip()
        
        if span < 500:
            return "STRONG", snippet
        else:
            return "PARTIAL", snippet
    elif found_ratio >= 0.6:
        # Most words found
        first_pos = min(word_positions.values()) if word_positions else 0
        start = max(0, first_pos - SNIPPET_CONTEXT)
        end = min(len(text), first_pos + SNIPPET_CONTEXT * 2)
        snippet = text[start:end].replace("\n", " ").strip()
        return "PARTIAL", snippet
    
    return "NONE", ""


# --- Example usage pattern (inside execute_code with PTC) ---
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

aem_host = "https://author-pXXXXX-eYYYYYY.adobeaemcloud.com"
folder = "/content/dam/moe"
keyword = "optimism about page length"

# 1. List all PDFs
search_body = build_structural_query(folder, ["application/pdf"])
response = api_request(
    service="aem",
    path=f"{aem_host}/adobe/assets/search?allowUnsafeSearch=true",
    method="POST",
    body=json.dumps(search_body),
    _status_update="Listing PDFs",
    _op_type="read"
)

assets = response["body"]["hits"]["results"]

# 2. Fetch text renditions concurrently
def fetch_text(asset):
    path = asset["repositoryMetadata"]["repo:path"]
    url = text_rendition_url(aem_host, path)
    result = api_request(service="aem", path=url, _status_update="Fetching text", _op_type="read")
    return path, result

texts = {}
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
    futures = {pool.submit(fetch_text, a): a for a in assets}
    for f in as_completed(futures):
        path, res = f.result()
        if res.get("status_code") == 200:
            texts[path] = str(res.get("body", ""))[:MAX_TEXT_LENGTH]

# 3. Score each document
results_by_tier = {"EXACT": [], "STRONG": [], "PARTIAL": []}
for path, text in texts.items():
    tier, snippet = score_relevance(text, keyword)
    if tier != "NONE":
        filename = path.split("/")[-1]
        results_by_tier[tier].append({
            "filename": filename,
            "path": path,
            "snippet": snippet
        })

# 4. Present results
for tier in ["EXACT", "STRONG", "PARTIAL"]:
    if results_by_tier[tier]:
        print(f"\\n### {tier} MATCH")
        for r in results_by_tier[tier]:
            print(f"  {r['filename']}")
            print(f"  Path: {r['path']}")
            print(f"  > ...{r['snippet']}...")
"""
