# Confluence Cloud API Reference

## Authentication

All requests use HTTP Basic Auth with Base64-encoded `email:api_token`:

```python
import base64
auth = base64.b64encode(f"{email}:{token}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
```

Generate tokens at: https://id.atlassian.com/manage-profile/security/api-tokens

---

## Critical Gotchas

### v2 API silently omits folders

`GET /wiki/api/v2/pages` returns only `page` type content. Confluence folders (type `folder`) are completely invisible to this endpoint. Always use CQL for tree discovery.

### Space type filter drops real spaces

`GET /wiki/api/v2/spaces?type=global` misses `knowledge_base` and `collaboration` spaces. Always query without a type filter: `?limit=250` only.

### Folders are only findable via CQL

```python
# WRONG — misses folders
GET /wiki/api/v2/pages?spaceId={id}&title=Hiring

# CORRECT — finds pages AND folders
GET /wiki/rest/api/content/search?cql=space="OHH" AND title="Hiring"
```

### Parent ID for folders

To publish under a folder, set `parentId` to the folder's ID. The v2 create/update page endpoints accept folder IDs as `parentId` correctly.

---

## Spaces

### List all spaces
```
GET /wiki/api/v2/spaces?limit=250
```
Returns: `{ results: [{ id, key, name, type }] }`
Types: `global`, `knowledge_base`, `collaboration`, `personal`

### Resolve space by key
```
GET /wiki/api/v2/spaces?keys={KEY}&limit=1
```

---

## Pages

### Create page
```
POST /wiki/api/v2/pages
Body: {
  "spaceId": "884740",
  "status": "current",
  "title": "Page Title",
  "parentId": "4751361",       // optional — page or folder ID
  "body": {
    "representation": "atlas_doc_format",
    "value": "<json-stringified ADF>"
  }
}
```

### Get page (includes version)
```
GET /wiki/api/v2/pages/{page_id}
Returns: { id, title, version: { number }, _links: { webui } }
```

### Update page
```
PUT /wiki/api/v2/pages/{page_id}
Body: {
  "id": "{page_id}",
  "status": "current",
  "title": "Page Title",
  "version": { "number": <current + 1> },
  "body": { "representation": "atlas_doc_format", "value": "..." }
}
```

### Delete page
```
DELETE /wiki/api/v2/pages/{page_id}
```

### List children of a page
```
GET /wiki/api/v2/pages/{page_id}/children?limit=250
```
Note: does NOT return folder children — use CQL for that.

---

## CQL Search (use for tree scans and parent resolution)

```
GET /wiki/rest/api/content/search?cql={query}&limit=200&start={offset}
```

### Useful CQL queries

```
# All content in a space (pages + folders)
space="OHH"

# Direct children of a page or folder
parent=4751361

# Find by title in space
space="OHH" AND title="Hiring"

# Find by type
space="OHH" AND type=folder

# Paginate
space="OHH"&limit=200&start=200
```

Response: `{ results: [{ id, type, title, _links: { webui } }], size, _links: { next } }`

---

## Building SESSION_TREE

```python
def build_session_tree(spaces, headers, base_url):
    tree = {}
    for space in spaces:
        key = space['key']
        nodes = []
        start = 0
        while True:
            r = requests.get(
                f"{base_url}/wiki/rest/api/content/search",
                params={"cql": f'space="{key}"', "limit": 200, "start": start},
                headers=headers
            )
            results = r.json().get("results", [])
            nodes.extend(results)
            if len(results) < 200:
                break
            start += 200
        # Build parent→children map
        children = {}
        for node in nodes:
            pid = node.get("_expandable", {}).get("parent", "").split("/")[-1]
            children.setdefault(pid, []).append({
                "id": node["id"],
                "title": node["title"],
                "type": node["type"],
                "children": []
            })
        tree[key] = children
    return tree
```

---

## Page URL Construction

```python
def page_url(page, base_url):
    return f"{base_url}/wiki{page['_links']['webui']}"
```
