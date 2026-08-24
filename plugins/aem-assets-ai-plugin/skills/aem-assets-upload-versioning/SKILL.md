---
name: aem-assets-upload-versioning
description: >
  Upload files to AEM DAM using the correct 3-step Cloud Service binary upload
  protocol (initiateUpload, blob PUT, completeUpload). Supports both new asset
  creation and versioning existing assets with labels and comments. Use after
  editing a PDF/Word/image to put it back in AEM as a new version.
  Triggers: upload to AEM, save as new version, replace the file in AEM,
  put this back in DAM, update the asset, upload modified file, version up.
type: skill
license: Apache-2.0
metadata:
  author: KM Robin
  version: "1.0"
---

# AEM Assets Upload and Versioning

| | |
|---|---|
| **ID** | `aem-assets-upload-versioning` |
| **Description** | 3-step binary upload for AEM Cloud Service with version support. |

## Tools

- `api_request` (service="aem")
- `execute_code`

## Key Concept

- Upload to an existing asset path: creates a new version
- Upload to a new path: creates a new asset

## Protocol (3 Steps)

### Step 1: Initiate Upload

POST to `<folder>.initiateUpload.json` with `fileName` and `fileSize`.
Returns presigned blob storage URL and upload token.

### Step 2: Upload Binary

PUT file bytes directly to the presigned blob storage URL.
Headers: `Content-Type: application/octet-stream`, `x-ms-blob-type: BlockBlob`.

### Step 3: Complete Upload

POST to `<folder>.completeUpload.json` with `fileName`, `fileSize`, `uploadToken`, `mimeType`.
Optional: `createVersion=true`, `versionLabel`, `versionComment`.

This triggers DAM processing (thumbnails, text extraction, workflows).

## MIME Types

| Extension | MIME Type |
|-----------|----------|
| .pdf | `application/pdf` |
| .docx | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| .jpg | `image/jpeg` |
| .png | `image/png` |

## Important Notes

- The `createasset.html` Sling servlet does NOT trigger DAM processing on Cloud Service.
- Step 2 goes to blob storage directly (no AEM auth needed, presigned URL is the auth).
- File size must be exact across all 3 steps.
- For files larger than 10MB, split into parts using `minPartSize` from initiate response.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| 401/403 on initiate | Insufficient permissions | User needs dam:write |
| 404 on initiate | Folder not found | Create folder first |
| Blob 403 | Presigned URL expired | Re-initiate from Step 1 |
| Asset stays unProcessed | completeUpload not called | Ensure Step 3 succeeded |
