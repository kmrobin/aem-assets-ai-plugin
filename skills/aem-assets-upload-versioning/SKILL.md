# AEM Assets Upload & Versioning

> **Tools:** `api_request` (service="aem"), `execute_code`, `bash`, `read`

## Purpose

Upload a file to AEM DAM — either as a **new asset** or as a **new version of an
existing asset** — using the AEM as a Cloud Service direct binary upload protocol.
This is the correct 3-step upload flow that triggers DAM processing (thumbnails,
text extraction, metadata extraction, workflows).

Use this skill whenever:
- A user edits a PDF/Word/image and wants to put it back in AEM as a version
- A user asks to upload a modified file to the same location
- A user wants to create a new asset with proper DAM processing
- Any workflow that generates a file needing upload to AEM DAM

## When To Use (Trigger Phrases)

- "upload this back to AEM"
- "save as a new version"
- "replace the file in AEM"
- "put this back in DAM"
- "update the asset with the edited file"
- "upload to /content/dam/..."
- "version up the asset"
- Any post-edit step where a local file needs to land in AEM DAM

## Key Concept: Versioning vs New Asset

AEM handles versioning automatically:
- **New version of existing asset**: Upload to the **same path**. AEM creates a
  version checkpoint and replaces the binary. The asset keeps its UUID, metadata,
  tags, and references.
- **New asset**: Upload to a path where no asset exists yet.

The upload API is identical in both cases — the path determines the behavior.

## Prerequisites

- AEM as a Cloud Service author instance
- File to upload available in the sandbox (e.g., `/workspace/edited-file.pdf`)
- Target DAM path known (e.g., `/content/dam/moe/sample-local-pdf.pdf`)

---

## Upload Protocol (3 Steps)

### Step 1: Initiate Upload

Call the `initiateUpload.json` endpoint on the **parent folder** to get a
presigned upload URL from Azure/S3 blob storage.

```
POST https://<aem-host>/content/dam/<parent-folder>.initiateUpload.json
Content-Type: application/x-www-form-urlencoded

fileName=<filename>&fileSize=<size-in-bytes>
```

**Parameters (form-encoded body):**
| Parameter | Description |
|-----------|-------------|
| `fileName` | Target filename (e.g., `sample-local-pdf.pdf`) |
| `fileSize` | Exact file size in bytes |

**Response (JSON):**
```json
{
  "completeURI": "/content/dam/moe.completeUpload.json",
  "folderPath": "/content/dam/moe",
  "files": [
    {
      "fileName": "sample-local-pdf.pdf",
      "uploadToken": "<opaque-token>",
      "uploadURIs": ["https://<blob-storage-url>"],
      "minPartSize": 10485760,
      "maxPartSize": 104857600
    }
  ]
}
```

**Implementation:**
```python
import os, json

file_path = "/workspace/edited-file.pdf"
file_size = os.path.getsize(file_path)
target_filename = "sample-local-pdf.pdf"
parent_folder = "/content/dam/moe"
aem_host = "https://author-pXXXXX-eYYYYYY.adobeaemcloud.com"

# Initiate upload
result = api_request(
    service="aem",
    path=f"{aem_host}{parent_folder}.initiateUpload.json",
    method="POST",
    body=f"fileName={target_filename}&fileSize={file_size}",
    extra_headers='{"Content-Type": "application/x-www-form-urlencoded"}',
    _status_update="Initiating upload",
    _op_type="create"
)
init_response = result["body"]
```

### Step 2: Upload Binary to Blob Storage

Upload the file directly to the presigned blob storage URL returned in Step 1.
This is a direct PUT to Azure Blob / AWS S3 — NOT through AEM.

**Important headers:**
- `Content-Type: application/octet-stream`
- `Content-Length: <file-size>`
- For Azure: `x-ms-blob-type: BlockBlob`

**For files smaller than `minPartSize` (single-part upload):**
```
PUT <uploadURIs[0]>
Content-Type: application/octet-stream
Content-Length: <fileSize>
x-ms-blob-type: BlockBlob

<binary-data>
```

**Implementation:**
```python
import base64

upload_uri = init_response["files"][0]["uploadURIs"][0]

# Read file as bytes
with open(file_path, "rb") as f:
    file_bytes = f.read()

# Upload to blob storage (this is a direct HTTP call, not through AEM auth)
# Use execute_code with urllib since this goes to blob storage, not AEM
import urllib.request

req = urllib.request.Request(
    upload_uri,
    data=file_bytes,
    method="PUT",
    headers={
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(file_bytes)),
        "x-ms-blob-type": "BlockBlob",
    }
)
response = urllib.request.urlopen(req)
# Expect 201 Created
```

**For large files (multi-part upload):**
If `fileSize > minPartSize`, split the file into parts and upload each to the
corresponding URI in the `uploadURIs` array. Each part goes to its indexed URI.
After all parts are uploaded, no additional assembly step is needed — the
`completeUpload` call handles it.

### Step 3: Complete Upload

Notify AEM that the binary upload is done. This triggers DAM asset processing
(rendition generation, metadata extraction, workflows).

```
POST https://<aem-host><completeURI>
Content-Type: application/x-www-form-urlencoded

fileName=<filename>&fileSize=<size>&uploadToken=<token>&mimeType=<mime>&createVersion=true&versionLabel=<label>&versionComment=<comment>
```

**Parameters (form-encoded body):**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `fileName` | Yes | Same filename as Step 1 |
| `fileSize` | Yes | Same file size as Step 1 |
| `uploadToken` | Yes | Token from Step 1 response |
| `mimeType` | Yes | MIME type (e.g., `application/pdf`) |
| `createVersion` | No | `true` to explicitly create a version checkpoint |
| `versionLabel` | No | Human-readable version label (e.g., "v2 - text updated") |
| `versionComment` | No | Description of what changed |
| `replace` | No | `true` to replace existing asset (default for same path) |

**Implementation:**
```python
import urllib.parse

upload_token = init_response["files"][0]["uploadToken"]
complete_uri = init_response["completeURI"]

params = {
    "fileName": target_filename,
    "fileSize": str(file_size),
    "uploadToken": upload_token,
    "mimeType": "application/pdf",
    "createVersion": "true",
    "versionLabel": "v2 - AI edited",
    "versionComment": "Replaced 'This PDF is three pages long' with '3 Pages Only'"
}

result = api_request(
    service="aem",
    path=f"{aem_host}{complete_uri}",
    method="POST",
    body=urllib.parse.urlencode(params),
    extra_headers='{"Content-Type": "application/x-www-form-urlencoded"}',
    _status_update="Completing upload",
    _op_type="create"
)
# Expect 200 with asset path in response
```

---

## Complete Reference Implementation

```python
"""
Full upload workflow: edit an existing AEM asset and upload as new version.
"""
import os, json, urllib.parse, urllib.request

# === Configuration ===
aem_host = "https://author-p153659-e1620914.adobeaemcloud.com"
local_file = "/workspace/ai-generated.pdf"          # edited file
target_path = "/content/dam/moe/sample-local-pdf.pdf"  # existing asset path

# Derive folder and filename
parent_folder = "/".join(target_path.split("/")[:-1])   # /content/dam/moe
target_filename = target_path.split("/")[-1]            # sample-local-pdf.pdf
file_size = os.path.getsize(local_file)
mime_type = "application/pdf"

# === Step 1: Initiate ===
init_result = api_request(
    service="aem",
    path=f"{aem_host}{parent_folder}.initiateUpload.json",
    method="POST",
    body=f"fileName={urllib.parse.quote(target_filename)}&fileSize={file_size}",
    extra_headers='{"Content-Type": "application/x-www-form-urlencoded"}',
    _status_update="Initiating upload",
    _op_type="create"
)

if init_result.get("status_code") != 200:
    raise Exception(f"Initiate failed: {init_result}")

init_data = init_result["body"]
upload_uri = init_data["files"][0]["uploadURIs"][0]
upload_token = init_data["files"][0]["uploadToken"]
complete_uri = init_data["completeURI"]

print(f"✓ Upload initiated. Token received. URI count: {len(init_data['files'][0]['uploadURIs'])}")

# === Step 2: Upload binary to blob storage ===
with open(local_file, "rb") as f:
    file_bytes = f.read()

req = urllib.request.Request(
    upload_uri,
    data=file_bytes,
    method="PUT",
    headers={
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(file_bytes)),
        "x-ms-blob-type": "BlockBlob",
    }
)
resp = urllib.request.urlopen(req)
print(f"✓ Binary uploaded to blob storage. Status: {resp.status}")

# === Step 3: Complete upload (triggers DAM processing) ===
complete_params = urllib.parse.urlencode({
    "fileName": target_filename,
    "fileSize": str(file_size),
    "uploadToken": upload_token,
    "mimeType": mime_type,
    "createVersion": "true",
    "versionLabel": "v2 - AI edited",
    "versionComment": "Text replacement: updated heading"
})

complete_result = api_request(
    service="aem",
    path=f"{aem_host}{complete_uri}",
    method="POST",
    body=complete_params,
    extra_headers='{"Content-Type": "application/x-www-form-urlencoded"}',
    _status_update="Completing upload",
    _op_type="create"
)

if complete_result.get("status_code") == 200:
    print(f"✓ Upload complete! Asset versioned at: {target_path}")
    print(f"  Version label: v2 - AI edited")
    print(f"  DAM processing triggered (thumbnails, text extraction, etc.)")
else:
    print(f"✗ Complete failed: {complete_result.get('status_code')}")
    print(complete_result.get("body", ""))
```

---

## MIME Type Reference

| Extension | MIME Type |
|-----------|----------|
| .pdf | `application/pdf` |
| .docx | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| .pptx | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| .xlsx | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| .jpg/.jpeg | `image/jpeg` |
| .png | `image/png` |
| .svg | `image/svg+xml` |
| .mp4 | `video/mp4` |
| .mov | `video/quicktime` |

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| 401/403 on initiateUpload | Auth token expired or insufficient permissions | Re-authenticate; user needs `dam:write` on the folder |
| 404 on initiateUpload | Parent folder doesn't exist | Create the folder first or check the path |
| 409 on completeUpload | Concurrent modification conflict | Retry once; if persists, check if another process is updating the asset |
| Blob upload fails (403) | Presigned URL expired (typically 30 min TTL) | Re-initiate upload from Step 1 |
| `dam:assetState = unProcessed` after upload | completeUpload was not called or failed | Ensure Step 3 completed successfully |

---

## Versioning Behavior

- Uploading to an **existing asset path** with `createVersion=true` creates a
  version checkpoint BEFORE replacing the binary. The old binary is preserved
  in version history.
- Without `createVersion=true`, the binary is still replaced but without an
  explicit version label (AEM may still auto-version depending on config).
- Version history is viewable in the AEM Assets Timeline panel.
- Previous versions can be restored from the Timeline.

## Important Notes

1. **The `createasset.html` Sling servlet is NOT sufficient** — it creates the
   node but does NOT trigger the full DAM Update Asset workflow on AEM Cloud
   Service. Always use the 3-step protocol.

2. **Step 2 goes directly to blob storage** — it does NOT use AEM authentication.
   The presigned URL IS the auth. Use `urllib` or equivalent, not `api_request`.

3. **File size must be exact** — the size in Step 1 and Step 3 must match the
   actual uploaded bytes. A mismatch causes silent failures.

4. **For large files (>10MB)**: split into parts using `minPartSize` from the
   initiate response. Upload part N to `uploadURIs[N]`. All parts must be
   uploaded before calling completeUpload.
