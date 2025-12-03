# Custom OpenAPI schema metadata
import json
from typing import Any, Dict, Tuple

from .configs.env_config import env_config


def public_desc(desc: str) -> str:
    return f"**🔓 Public Endpoint**\n\n{desc}"


docs_summary = "The TGDex-Discussion service is a dedicated microservice built with FastAPI to handle all discussion-related functionalities within the TGDex ecosystem."
docs_description = (
    "`Apart from the response codes specified in each API, the API server may respond with other common "
    "responses based on standard API behavior.`"
)

docs_tags_metadata = [
    {
        "name": "Utility APIs",
        "description": (
            "The Utility APIs contain endpoints that serve operational or system-level purposes. "
            "These routes are not directly related to the core business logic of the API but "
            "are essential for overall functionality, monitoring, and accessibility."
        ),
    },
    {
        "name": "Discussion APIs",
        "description": (
            "The Discussion APIs handle all operations related to the discussions. "
            "These routes provide functionality for managing the discussion forums and its contents in TGDex ecosystem."
        ),
    },
    {
        "name": "Challenge APIs",
        "description": (
            "The Challenge APIs handle all operations related to the challenges. "
            "These routes provide functionality for managing the challenges and its contents in TGDex ecosystem."
        ),
    },
]


# Helper function to extract headers and payload from OpenAPI operation
def extract_headers_and_payload(
    operation: Dict[str, Any], components: Dict[str, Any]
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    headers = {
        param["name"]: (
            param["schema"].get("type")
            or (
                "Bearer <token>"
                if param["name"] == "Authorization"
                else " | ".join(v["type"] for v in param["schema"].get("anyOf", []))
            )
        )
        for param in operation.get("parameters", [])
        if param.get("in") == "header"
    }

    payload_example = {}
    request_body = operation.get("requestBody", {}).get("content", {})
    for content_type, content in request_body.items():
        if content_type in ("application/json", "application/x-www-form-urlencoded"):
            headers["Content-Type"] = content_type
            schema_ref = content["schema"].get("$ref", "")
            schema_name = schema_ref.split("/")[-1] if schema_ref else None
            if schema_name:
                properties = (
                    components["schemas"].get(schema_name, {}).get("properties", {})
                )
                for key, value in properties.items():
                    if "anyOf" in value:
                        output_type = []
                        for v in value["anyOf"]:
                            if "type" in v.keys():
                                output_type.append(v["type"])
                            elif "$ref" in v.keys():
                                ref_name = v["$ref"].split("/")[-1]
                                output_type.append(
                                    components["schemas"]
                                    .get(ref_name, {})
                                    .get("type", "")
                                )
                        payload_example[key] = " | ".join(output_type)
                    else:
                        payload_example[key] = value.get("type", "")
    return headers, payload_example


# Helper function to generate code samples
def generate_code_samples(
    path: str, method: str, operation: Dict[str, Any], components: Dict[str, Any]
) -> None:
    nl = "\n"
    tl = "    "
    base_url = env_config.BASE_URL

    headers, payload_example = extract_headers_and_payload(operation, components)

    # Constructing query string
    query_params = [
        param for param in operation.get("parameters", []) if param.get("in") == "query"
    ]
    query_string = "&".join(f"{param['name']}={{value}}" for param in query_params)
    query_string = f"?{query_string}" if query_string else ""

    # Generating cURL example
    curl_headers = "".join(f"{tl}-H '{k}: {v}'{nl}" for k, v in headers.items())
    curl_payload = (
        f"{tl}-d '{json.dumps(payload_example)}'{nl}" if payload_example else ""
    )
    curl_sample = (
        f"curl -X {method.upper()} {base_url}{path}{query_string}{nl}"
        f"{curl_headers}{curl_payload}"
    ).strip()

    js_sample_for_form = None
    python_sample_for_form = None
    if headers.get("Content-Type") and (
        "application/x-www-form-urlencoded" in headers.get("Content-Type")
    ):
        js_sample_for_form = (
            f"const url = '{base_url}{path}{query_string}';{nl}"
            f"const headers = {json.dumps(headers, indent=4)};{nl}"
            f"const formData = new URLSearchParams();{nl}"
            f"{''.join(f'data.append("{k}", {json.dumps(v)})' for k, v in payload_example.items())}{nl}"
            f"fetch(url, {{method: '{method.upper()}', headers, body: formData.toString()}}){nl}"
            f"    .then(response => response.json()){nl}"
            f"    .then(data => console.log(data)){nl}"
            f"    .catch(error => console.error('Error:', error));"
        )
        python_sample_for_form = (
            f"import requests{nl}{nl}"
            f"url = '{base_url}{path}{query_string}'{nl}"
            f"payload = {json.dumps(payload_example) if payload_example else {}}{nl}"
            f"headers = {json.dumps(headers)}{nl}{nl}"
            f"response = requests.{method.lower()}(url, headers=headers, data=payload){nl}"
            f"print(response.text()){nl}"
        )

    # Generating Python example
    python_sample = (
        (
            f"import requests{nl}import json{nl}{nl}"
            f"url = '{base_url}{path}{query_string}'{nl}"
            f"payload = {json.dumps(payload_example) if payload_example else {}}{nl}"
            f"headers = {json.dumps(headers)}{nl}{nl}"
            f"response = requests.{method.lower()}(url, headers=headers, json=payload){nl}"
            f"print(response.text)"
        )
        if not python_sample_for_form
        else python_sample_for_form
    )

    # Generating JavaScript (fetch) example
    js_sample = (
        (
            f"const url = '{base_url}{path}{query_string}';{nl}"
            f"const headers = {json.dumps(headers, indent=4)};{nl}"
            f"const payload = {json.dumps(payload_example, indent=4)};{nl}{nl}"
            f"fetch(url, {{method: '{method.upper()}', headers, body: JSON.stringify(payload)}}){nl}"
            f"    .then(response => response.json()){nl}"
            f"    .then(data => console.log(data)){nl}"
            f"    .catch(error => console.error('Error:', error));"
        )
        if not js_sample_for_form
        else js_sample_for_form
    )

    operation["x-code-samples"] = [
        {"lang": "curl", "source": curl_sample, "label": "Curl"},
        {"lang": "Python", "source": python_sample, "label": "Python3"},
        {"lang": "JavaScript", "source": js_sample, "label": "JavaScript (Fetch)"},
    ]
