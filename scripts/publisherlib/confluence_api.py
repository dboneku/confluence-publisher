import json

import requests


def list_spaces(base_url: str, headers: dict) -> list[dict]:
    response = requests.get(
        f"{base_url}/wiki/api/v2/spaces",
        params={"limit": 250},
        headers=headers,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def resolve_space_id(base_url: str, headers: dict, space_key: str) -> str:
    response = requests.get(
        f"{base_url}/wiki/api/v2/spaces",
        params={"keys": space_key, "limit": 1},
        headers=headers,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError(f"Space '{space_key}' not found")
    return results[0]["id"]


def resolve_parent_id(base_url: str, headers: dict, space_key: str, parent_title: str) -> str | None:
    if not parent_title or not parent_title.strip():
        return None
    response = requests.get(
        f"{base_url}/wiki/rest/api/content/search",
        params={"cql": f'space="{space_key}" AND title="{parent_title.strip()}"', "limit": 5},
        headers=headers,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError(f"Parent page or folder '{parent_title}' not found in space {space_key}")
    return results[0]["id"]


def find_existing_page(base_url: str, headers: dict, space_id: str, title: str) -> dict | None:
    response = requests.get(
        f"{base_url}/wiki/api/v2/pages",
        params={"spaceId": space_id, "title": title, "limit": 1},
        headers=headers,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None


def get_page_version(base_url: str, headers: dict, page_id: str) -> int:
    response = requests.get(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()["version"]["number"]


def list_child_pages(base_url: str, headers: dict, parent_id: str) -> list[dict]:
    results = []
    url = f"{base_url}/wiki/api/v2/pages/{parent_id}/children"
    params: dict = {"limit": 250}
    while url:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))
        url = data.get("_links", {}).get("next")
        params = {}
    return results


def delete_page(base_url: str, headers: dict, page_id: str):
    response = requests.delete(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        headers=headers,
    )
    response.raise_for_status()


def create_page(
    base_url: str,
    headers: dict,
    space_id: str,
    title: str,
    adf_body: dict,
    parent_id: str = None,
    labels: list[str] = None,
    status: str = "current",
) -> dict:
    payload = {
        "spaceId": space_id,
        "status": status,
        "title": title,
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(adf_body),
        },
    }
    if parent_id:
        payload["parentId"] = parent_id
    if labels:
        payload["metadata"] = {"labels": [{"name": label} for label in labels]}

    response = requests.post(
        f"{base_url}/wiki/api/v2/pages",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def update_page(
    base_url: str,
    headers: dict,
    page_id: str,
    title: str,
    adf_body: dict,
    version: int,
    status: str = "current",
) -> dict:
    payload = {
        "id": page_id,
        "status": status,
        "title": title,
        "version": {"number": version + 1},
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(adf_body),
        },
    }
    response = requests.put(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def page_url(base_url: str, page: dict) -> str:
    return f"{base_url}/wiki{page['_links']['webui']}"


def build_space_tree(base_url: str, headers: dict, space_key: str) -> list[dict]:
    results = []
    start = 0
    while True:
        response = requests.get(
            f"{base_url}/wiki/rest/api/content/search",
            params={
                "cql": f'space="{space_key}" ORDER BY title',
                "limit": 200,
                "start": start,
                "expand": "ancestors",
            },
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        batch = data.get("results", [])
        results.extend(batch)
        if not batch or len(results) >= data.get("totalSize", 0):
            break
        start += len(batch)

    nodes = {}
    for item in results:
        nodes[item["id"]] = {
            "id": item["id"],
            "title": item["title"],
            "type": item["type"],
            "children": [],
            "parent_id": (item.get("ancestors") or [None])[-1],
        }
        if nodes[item["id"]]["parent_id"] and isinstance(nodes[item["id"]]["parent_id"], dict):
            nodes[item["id"]]["parent_id"] = nodes[item["id"]]["parent_id"]["id"]

    root_nodes = []
    for node in nodes.values():
        parent_id = node["parent_id"]
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            root_nodes.append(node)

    root_nodes.sort(key=lambda node: node["title"])
    return root_nodes


def fetch_page_adf(base_url: str, headers: dict, page_id: str) -> tuple[dict, str]:
    response = requests.get(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        params={"body-format": "atlas_doc_format"},
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    title = data["title"]
    body_value = data.get("body", {}).get("atlas_doc_format", {}).get("value", "{}")
    return json.loads(body_value), title


def walk_descendant_pages(base_url: str, headers: dict, parent_id: str) -> list[dict]:
    results = []
    start = 0
    while True:
        response = requests.get(
            f"{base_url}/wiki/rest/api/content/search",
            params={
                "cql": f"ancestor={parent_id} AND type=page ORDER BY title",
                "limit": 100,
                "start": start,
            },
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        batch = data.get("results", [])
        results.extend(batch)
        if not batch or len(results) >= data.get("totalSize", 0):
            break
        start += len(batch)
    return results


def walk_space_pages(base_url: str, headers: dict, space_key: str) -> list[dict]:
    results = []
    start = 0
    while True:
        response = requests.get(
            f"{base_url}/wiki/rest/api/content/search",
            params={
                "cql": f'space="{space_key}" AND type=page ORDER BY title',
                "limit": 100,
                "start": start,
            },
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        batch = data.get("results", [])
        results.extend(batch)
        if not batch or len(results) >= data.get("totalSize", 0):
            break
        start += len(batch)
    return results