"""Pure HCL module generator.

Must not import httpx, a database session, or HTTPException. LLM notes are
ignored here; the agent port lives outside this module.
"""

from __future__ import annotations

import re

from iac.iac_types import FileEntry, Resource

REQUIRED_PATHS = ("main.tf", "variables.tf", "outputs.tf")
EXPERIMENTAL_MARKER = "experimental"

# Icon bytes are base64 and accidentally contain short tokens such as aws / s3 / ec2.
_IMAGE_DATA = re.compile(r"image=data:[^;]*", re.IGNORECASE)
_STENCIL = re.compile(r"mxgraph\.(aws|azure|gcp)")
# The diagram builder reuses the AWS group frame for Azure and GCP containers.
_GROUP_SHAPE = re.compile(r"shape=mxgraph\.(?:aws|azure|gcp)[a-z0-9]*\.group(?:;|$)")
_EXPLICIT = (
    ("gcp", ("google cloud", "gcp", "google")),
    ("azure", ("azure", "microsoft")),
    ("aws", ("amazon", "aws")),
)
# Phrases match the label text. Short tokens match whole words, never the icon payload.
_SERVICE_HINTS = (
    (
        "gcp",
        (
            "cloud sql",
            "cloud run",
            "bigquery",
            "big query",
            "compute engine",
            "cloud storage",
            "cloud kms",
            "cloud nat",
            "cloud armor",
            "cloud cdn",
            "cloud dns",
            "cloud load balancing",
            "secret manager",
            "pub/sub",
            "pubsub",
            "spanner",
            "alloydb",
            "bigtable",
            "memorystore",
            "firestore",
            "apigee",
            "observability",
            "instance group",
            "gke",
            "gce",
        ),
    ),
    (
        "azure",
        (
            "virtual machine scale set",
            "virtual machine",
            "storage account",
            "blob storage",
            "application gateway",
            "key vault",
            "app service",
            "function app",
            "front door",
            "virtual network",
            "resource group",
            "network security group",
            "sql database",
            "azure dns",
            "azure files",
            "azure cache",
            "vmss",
            "vnet",
            "aks",
            "vm",
        ),
    ),
    (
        "aws",
        (
            "elastic load balancing",
            "application load balancer",
            "internet gateway",
            "secrets manager",
            "route 53",
            "simple storage",
            "cloudfront",
            "cloudwatch",
            "elasticache",
            "documentdb",
            "cognito",
            "dynamodb",
            "lambda",
            "ec2",
            "rds",
            "eks",
            "ecs",
            "sqs",
            "sns",
            "alb",
            "nlb",
            "s3",
        ),
    ),
)

_SAFE = re.compile(r"[^A-Za-z0-9_]")


def is_safe_relative_path(path: str) -> bool:
    """True when ``path`` is a relative module path with no escape."""
    if not path or path.startswith(("/", "\\")) or "\\" in path or "\x00" in path:
        return False
    return ".." not in path.split("/")


def safe_label(value: str) -> str:
    cleaned = _SAFE.sub("_", value or "").strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"r_{cleaned}" if cleaned else "resource"
    return cleaned[:64]


def _style_text(style: str) -> str:
    """Drop embedded icon bytes before looking for a cloud name."""
    return _IMAGE_DATA.sub(" ", style or "").lower()


def _has_hint(label: str, hint: str) -> bool:
    if " " in hint or len(hint) >= 5:
        squashed = re.sub(r"[^a-z0-9]", "", label)
        return hint in label or hint.replace(" ", "") in squashed
    return re.search(rf"(?<![a-z0-9]){re.escape(hint)}(?![a-z0-9])", label) is not None


def cloud_of_node(label: str, style: str = "") -> str:
    """Cloud of one node. The label wins; a group frame is not a cloud."""
    text = _style_text(style)
    name = (label or "").lower()
    for cloud, hints in _EXPLICIT:
        if any(_has_hint(name, hint) for hint in hints):
            return cloud
    if not _GROUP_SHAPE.search(text):
        stencil = _STENCIL.search(text)
        if stencil:
            return stencil.group(1)
    for cloud, hints in _SERVICE_HINTS:
        if any(_has_hint(name, hint) for hint in hints):
            return cloud
    return "generic"


def _inherit_cloud(nodes: list[dict], clouds: list[str]) -> list[str]:
    """A node with no cloud of its own keeps the cloud of its parent group."""
    index_by_id: dict[str, int] = {}
    for index, node in enumerate(nodes):
        node_id = str(node.get("id") or "")
        if node_id and node_id not in index_by_id:
            index_by_id[node_id] = index

    def resolve(index: int, seen: set[str]) -> str:
        if clouds[index] != "generic":
            return clouds[index]
        parent = str(nodes[index].get("parent") or "")
        if parent and parent in index_by_id and parent not in seen:
            return resolve(index_by_id[parent], seen | {parent})
        return "generic"

    return [resolve(index, {str(nodes[index].get("id") or "")}) for index in range(len(nodes))]


def resources_from_diagram_summary(summary: dict) -> list[Resource]:
    """Map an existing diagram summary (nodes with label/style) to resources."""
    nodes = [node for node in summary.get("nodes") or [] if isinstance(node, dict)]
    clouds = [
        cloud_of_node(str(node.get("label") or node.get("id") or "resource"), str(node.get("style") or ""))
        for node in nodes
    ]
    clouds = _inherit_cloud(nodes, clouds)
    counts = {cloud: clouds.count(cloud) for cloud in clouds if cloud != "generic"}
    if counts:
        primary = sorted(counts, key=lambda cloud: (-counts[cloud], cloud))[0]
        clouds = [primary if cloud == "generic" else cloud for cloud in clouds]
    resources: list[Resource] = []
    for node, cloud in zip(nodes, clouds):
        label = str(node.get("label") or node.get("id") or "resource")
        resources.append(
            Resource(
                name=label,
                cloud=cloud,
                kind="node",
                node_id=str(node.get("id") or ""),
                parent_id=str(node.get("parent") or ""),
                style=str(node.get("style") or ""),
            )
        )
    return resources


def primary_cloud(resources: list[Resource]) -> str:
    if not resources:
        return "aws"
    counts: dict[str, int] = {}
    for resource in resources:
        counts[resource.cloud] = counts.get(resource.cloud, 0) + 1
    return sorted(counts, key=lambda cloud: (-counts[cloud], cloud))[0]


# Phrase is matched against the whole label. Token is matched on whole words.
# Earlier rules win, so "s3" is not swallowed by a generic compute default.
_TYPE_RULES: dict[str, tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...]] = {
    "aws": (
        (("s3", "bucket"), (), "aws_s3_bucket"),
        (("internet gateway",), ("igw",), "aws_internet_gateway"),
        (("load balancer",), ("alb", "nlb", "elb", "loadbalancer"), "aws_lb"),
        (("api gateway",), ("apigateway",), "aws_api_gateway_rest_api"),
        (("secrets manager",), (), "aws_secretsmanager_secret"),
        (("public subnet", "private subnet", "db subnet"), ("subnet",), "aws_subnet"),
        ((), ("lambda", "function"), "aws_lambda_function"),
        ((), ("vpc",), "aws_vpc"),
        ((), ("kms",), "aws_kms_key"),
        ((), ("cognito",), "aws_cognito_user_pool"),
        ((), ("ecs",), "aws_ecs_cluster"),
        ((), ("rds", "aurora", "database", "db", "postgres", "mysql"), "aws_db_instance"),
        ((), ("dynamodb",), "aws_dynamodb_table"),
        ((), ("eks", "kubernetes", "k8s"), "aws_eks_cluster"),
        ((), ("sqs", "queue"), "aws_sqs_queue"),
        ((), ("sns", "topic"), "aws_sns_topic"),
        ((), ("iam", "role"), "aws_iam_role"),
        ((), ("cloudfront", "cdn"), "aws_cloudfront_distribution"),
        ((), ("ec2", "instance", "vm", "compute", "server", "web"), "aws_instance"),
    ),
    "gcp": (
        (("cloud sql", "cloudsql"), ("sql", "database", "db"), "google_sql_database_instance"),
        (("cloud run", "cloudrun"), (), "google_cloud_run_v2_service"),
        (("big query",), ("bigquery",), "google_bigquery_dataset"),
        (("pub/sub", "pubsub", "pub sub"), (), "google_pubsub_topic"),
        (("cloud kms",), ("kms",), "google_kms_key_ring"),
        (("vpc network",), ("vpc",), "google_compute_network"),
        (("subnetwork", "subnet"), (), "google_compute_subnetwork"),
        ((), ("gcs", "bucket", "storage"), "google_storage_bucket"),
        ((), ("gke", "kubernetes", "k8s"), "google_container_cluster"),
        (("compute engine",), ("gce",), "google_compute_instance"),
    ),
    "azure": (
        (("microsoft azure", "resource group", "subscription"), (), "azurerm_resource_group"),
        (("cosmos",), (), "azurerm_cosmosdb_account"),
        (("web application firewall",), ("waf",), "azurerm_web_application_firewall_policy"),
        (("application gateway",), (), "azurerm_application_gateway"),
        (("front door",), (), "azurerm_cdn_frontdoor_profile"),
        (("key vault",), (), "azurerm_key_vault"),
        (("log analytics", "azure monitor", "monitor"), (), "azurerm_log_analytics_workspace"),
        (("nat gateway",), (), "azurerm_nat_gateway"),
        (("cdn",), (), "azurerm_cdn_profile"),
        (("virtual machine scale set", "virtual machine"), ("vmss", "vm"), "azurerm_linux_virtual_machine"),
        ((), ("aks", "kubernetes", "k8s"), "azurerm_kubernetes_cluster"),
        (("blob storage", "storage account"), ("storage", "blob", "bucket"), "azurerm_storage_account"),
        (("subnet",), ("subnet",), "azurerm_subnet"),
        (("sql database",), ("sql", "database", "db"), "azurerm_mssql_server"),
        (("virtual network",), ("vnet", "vpc", "network"), "azurerm_virtual_network"),
        ((), ("instance", "compute"), "azurerm_linux_virtual_machine"),
    ),
}

# Identified products whose required deployment fields are not on the diagram.
# These never fall through to a compute instance.
_SUPPLEMENT_RULES: dict[str, tuple[tuple[tuple[str, ...], tuple[str, ...], str, tuple[str, ...]], ...]] = {
    "aws": (
        (("route 53", "route53"), (), "aws_route53_zone", ("zone name",)),
        (("cloudwatch", "cloud watch"), (), "aws_cloudwatch_log_group", ("是 log group、alarm 還是 dashboard",)),
        (("nat gateway",), (), "aws_nat_gateway", ("subnet", "elastic IP")),
        (("aws waf",), ("waf",), "aws_wafv2_web_acl", ("scope", "default action")),
        (("shield",), (), "aws_shield_protection", ("要保護的資源 ARN",)),
        (("elasticache", "elasti cache"), (), "aws_elasticache_cluster", ("engine", "node type")),
        (("documentdb", "document db"), (), "aws_docdb_cluster", ("master username",)),
    ),
    "gcp": (
        (("apigee",), (), "google_apigee_organization", ("analytics region", "authorized network", "billing type")),
        (("cloud armor",), (), "google_compute_security_policy", ("security rules",)),
        (("cloud load balancing", "load balancing"), (), "google_compute_forwarding_rule", ("backend", "port")),
        (("cloud dns",), ("dns",), "google_dns_managed_zone", ("dns name",)),
        (("cloud cdn",), ("cdn",), "google_compute_backend_bucket", ("origin",)),
        (("cloud nat",), ("nat",), "google_compute_router_nat", ("Cloud Router", "subnet")),
        (("spanner",), (), "google_spanner_instance", ("instance config", "capacity")),
        (("alloydb", "alloy db"), (), "google_alloydb_cluster", ("network", "instance type")),
        (("bigtable", "big table"), (), "google_bigtable_instance", ("zone", "node count")),
        (("memorystore",), ("redis",), "google_redis_instance", ("tier", "memory size")),
        (("managed instance group", "instance group"), (), "google_compute_instance_group_manager", ("instance template", "zone")),
        (("cloud iam",), ("iam",), "google_project_iam_member", ("member", "role")),
        (("vertex",), (), "google_vertex_ai_endpoint", ("model",)),
        (("firestore",), (), "google_firestore_database", ("database type",)),
        (("secret manager",), (), "google_secret_manager_secret", ("replication",)),
        (("cloud monitoring", "observability"), (), "google_monitoring_dashboard", ("dashboard definition",)),
    ),
    "azure": (
        (("azure dns",), ("dns",), "azurerm_dns_zone", ("dns name",)),
        (("azure files",), (), "azurerm_storage_share", ("storage account", "share 名稱")),
        (("azure cache for redis", "cache for redis"), ("redis",), "azurerm_redis_cache", ("SKU", "capacity")),
        (("load balancer",), (), "azurerm_lb", ("subnet", "frontend IP")),
    ),
}

_DEFAULT_TYPE = {
    "aws": "aws_unsupported",
    "gcp": "gcp_unsupported",
    "azure": "azure_unsupported",
    "generic": "generic_unsupported",
}

_LOCATION_DEFAULT = {
    "aws": "us-east-1",
    "gcp": "us-central1",
    "azure": "eastus",
    "generic": "us-east-1",
}

_PROVIDER_SOURCE = {
    "aws": "hashicorp/aws",
    "google": "hashicorp/google",
    "azurerm": "hashicorp/azurerm",
}


_RESOURCE_FRAME = re.compile(
    r"(?<![a-z0-9])(?:subnet|subnetwork|vpc|vnet|virtual network|resource group)(?![a-z0-9])"
)
_LAYOUT_WORD = re.compile(r"(?<![a-z0-9])(?:layer|availability zone|zone|region)(?![a-z0-9])")


def is_layout_label(label: str, style: str = "") -> bool:
    """True for a diagram frame. VPC, subnet, and resource group stay."""
    text = re.sub(r"[^a-z0-9]+", " ", (label or "").lower()).strip()
    if _RESOURCE_FRAME.search(text):
        return False
    if text in {
        "google cloud platform",
        "aws cloud",
        "microsoft azure",
        "azure cloud",
        "azure subscription",
        "subscription",
    }:
        return True
    if _LAYOUT_WORD.search(text):
        return True
    return _GROUP_SHAPE.search(_style_text(style)) is not None


def component_plan(resource: Resource) -> dict:
    """Map one node. Unrecognized components are not turned into a compute instance."""
    if is_layout_label(resource.name, resource.style):
        return {"status": "layout", "tf_type": "", "missing": ()}
    text = f"{resource.name} {resource.kind}".lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    for phrases, words, tf_type in _TYPE_RULES.get(resource.cloud, ()):
        if any(phrase in text for phrase in phrases) or tokens.intersection(words):
            return {"status": "ready", "tf_type": tf_type, "missing": ()}
    for phrases, words, tf_type, missing in _SUPPLEMENT_RULES.get(resource.cloud, ()):
        if any(phrase in text for phrase in phrases) or tokens.intersection(words):
            return {"status": "supplement", "tf_type": tf_type, "missing": missing}
    return {
        "status": "unsupported",
        "tf_type": _DEFAULT_TYPE.get(resource.cloud, "generic_unsupported"),
        "missing": (),
    }


def terraform_type(resource: Resource) -> str:
    """Terraform type for a ready node. Other nodes return a non-resource marker."""
    plan = component_plan(resource)
    if plan["status"] == "ready":
        return plan["tf_type"]
    if plan["status"] == "layout":
        return ""
    if plan["status"] == "supplement":
        return f"{resource.cloud}_supplement"
    return plan["tf_type"]


def generate_module_tree(resources: list[Resource]) -> list[FileEntry]:
    """Build main/variables/outputs. Non-primary clouds stay, marked experimental."""
    primary = primary_cloud(resources)
    plans = [component_plan(resource) for resource in resources]
    types = [terraform_type(resource) for resource in resources]
    addresses = [_address(resource, index) for index, resource in enumerate(resources)]
    links, extras = _azure_links(resources, types, addresses)
    _gcp_links(resources, plans, types, addresses, links)
    _aws_links(resources, plans, types, addresses, links)
    for index, plan in enumerate(plans):
        if plan["status"] in {"ready", "layout"}:
            continue
        links[index]["gap"] = plan["status"]
        links[index]["intended"] = plan["tf_type"] if plan["status"] == "supplement" else ""
        links[index]["missing"] = "、".join(plan["missing"])
    blocks: list[str] = [f"# primary_cloud = {primary}"]
    providers = _provider_block(types)
    if providers:
        blocks.append(providers)
        blocks.append(_provider_config(types))
    if not resources:
        blocks.append("# no resources in diagram")
    blocks.extend(extras)
    for index, resource in enumerate(resources):
        if plans[index]["status"] == "layout":
            continue
        experimental = resource.cloud != primary
        blocks.append(
            _resource_block(
                resource,
                index,
                types[index],
                experimental=experimental,
                link=links[index],
            )
        )
    main = "\n\n".join(block for block in blocks if block.strip()) + "\n"
    variables = _variables(primary, types)
    outputs = 'output "module_ready" {\n  value = true\n}\n'
    return [
        FileEntry("main.tf", main),
        FileEntry("variables.tf", variables),
        FileEntry("outputs.tf", outputs),
    ]


def _address(resource: Resource, index: int) -> str:
    return f"{safe_label(resource.name)}_{index}"


def _provider_names(types: list[str]) -> list[str]:
    names = []
    for tf_type in types:
        provider = tf_type.split("_", 1)[0]
        if provider in _PROVIDER_SOURCE and provider not in names:
            names.append(provider)
    return names


def _variables(primary: str, types: list[str]) -> str:
    location = _LOCATION_DEFAULT.get(primary, "us-east-1")
    parts = [
        'variable "name_prefix" {\n'
        "  type        = string\n"
        '  description = "Prefix for generated resources"\n'
        '  default     = "cloud360"\n'
        "}\n",
        'variable "location" {\n'
        "  type        = string\n"
        '  description = "Region or location for generated resources"\n'
        f'  default     = "{location}"\n'
        "}\n",
    ]
    if "azurerm" in _provider_names(types):
        parts.append(
            'variable "subscription_id" {\n'
            "  type        = string\n"
            '  description = "Azure subscription id supplied outside this draft"\n'
            "}\n"
        )
    if "google" in _provider_names(types):
        parts.append(
            'variable "project_id" {\n'
            "  type        = string\n"
            '  description = "GCP project id supplied outside this draft"\n'
            "}\n"
        )
    if "azurerm_mssql_server" in types:
        parts.append(
            'variable "administrator_login_password" {\n'
            "  type        = string\n"
            "  sensitive   = true\n"
            '  description = "SQL administrator password supplied outside this draft"\n'
            "}\n"
        )
    if "azurerm_linux_virtual_machine" in types:
        parts.append(
            'variable "admin_ssh_public_key" {\n'
            "  type        = string\n"
            '  description = "SSH public key supplied outside this draft"\n'
            "}\n"
        )
    if "azurerm_key_vault" in types:
        parts.append(
            'variable "tenant_id" {\n'
            "  type        = string\n"
            '  description = "Azure tenant id supplied outside this draft"\n'
            "}\n"
        )
    return "\n".join(parts) + "\n"


def _ancestor(resources: list[Resource], parent_id: str, predicate) -> int | None:
    index_by_id = {}
    for index, resource in enumerate(resources):
        if resource.node_id and resource.node_id not in index_by_id:
            index_by_id[resource.node_id] = index
    seen: set[str] = set()
    current = parent_id
    while current and current not in seen:
        seen.add(current)
        index = index_by_id.get(current)
        if index is None:
            return None
        if predicate(index):
            return index
        current = resources[index].parent_id
    return None


def _azure_links(
    resources: list[Resource],
    types: list[str],
    addresses: list[str],
) -> tuple[list[dict], list[str]]:
    """Wire Azure resources to a real resource group, VNet, and subnet."""
    links: list[dict] = [{} for _ in resources]
    extras: list[str] = []
    if not any(tf_type.startswith("azurerm_") for tf_type in types):
        return links, extras

    def of_type(tf_type: str) -> list[int]:
        return [index for index, item in enumerate(types) if item == tf_type]

    groups = of_type("azurerm_resource_group")
    vnets = of_type("azurerm_virtual_network")
    subnets = of_type("azurerm_subnet")

    if groups:
        rg_name = f"azurerm_resource_group.{addresses[groups[0]]}.name"
        rg_loc = f"azurerm_resource_group.{addresses[groups[0]]}.location"
    else:
        rg_name = "azurerm_resource_group.generated.name"
        rg_loc = "azurerm_resource_group.generated.location"
        extras.append(
            'resource "azurerm_resource_group" "generated" {\n'
            '  name     = "${var.name_prefix}-rg"\n'
            "  location = var.location\n"
            "}\n"
        )

    needs_subnet = {
        "azurerm_linux_virtual_machine",
        "azurerm_application_gateway",
        "azurerm_nat_gateway",
        "azurerm_kubernetes_cluster",
    }
    generated_vnet = "azurerm_virtual_network.generated.name"
    generated_subnet = "azurerm_subnet.generated.id"
    if any(types[index] in needs_subnet for index in range(len(types))) and not subnets:
        if not vnets:
            extras.append(
                'resource "azurerm_virtual_network" "generated" {\n'
                '  name                = "${var.name_prefix}-vnet"\n'
                "  address_space       = [\"10.0.0.0/16\"]\n"
                f"  location            = {rg_loc}\n"
                f"  resource_group_name = {rg_name}\n"
                "}\n"
            )
        vnet_for_generated = generated_vnet if not vnets else f"azurerm_virtual_network.{addresses[vnets[0]]}.name"
        extras.append(
            'resource "azurerm_subnet" "generated" {\n'
            '  name                 = "workload"\n'
            f"  resource_group_name  = {rg_name}\n"
            f"  virtual_network_name = {vnet_for_generated}\n"
            '  address_prefixes     = ["10.0.240.0/24"]\n'
            "}\n"
        )

    for offset, index in enumerate(subnets):
        vnet_index = _ancestor(resources, resources[index].parent_id, lambda item: types[item] == "azurerm_virtual_network")
        if vnet_index is None and vnets:
            vnet_index = vnets[0]
        vnet_name = generated_vnet if vnet_index is None else f"azurerm_virtual_network.{addresses[vnet_index]}.name"
        if vnet_index is None and not any('azurerm_virtual_network" "generated"' in item for item in extras):
            extras.append(
                'resource "azurerm_virtual_network" "generated" {\n'
                '  name                = "${var.name_prefix}-vnet"\n'
                "  address_space       = [\"10.0.0.0/16\"]\n"
                f"  location            = {rg_loc}\n"
                f"  resource_group_name = {rg_name}\n"
                "}\n"
            )
        links[index]["vnet"] = vnet_name
        links[index]["prefix"] = f"10.0.{offset + 1}.0/24"

    def subnet_expr(index: int) -> str:
        found = _ancestor(resources, resources[index].parent_id, lambda item: types[item] == "azurerm_subnet")
        if found is not None:
            return f"azurerm_subnet.{addresses[found]}.id"
        if subnets:
            return f"azurerm_subnet.{addresses[subnets[0]]}.id"
        return generated_subnet

    def group_expr(index: int) -> tuple[str, str]:
        if types[index] == "azurerm_resource_group":
            return rg_name, "var.location"
        found = _ancestor(resources, resources[index].parent_id, lambda item: types[item] == "azurerm_resource_group")
        if found is None:
            return rg_name, rg_loc
        return (
            f"azurerm_resource_group.{addresses[found]}.name",
            f"azurerm_resource_group.{addresses[found]}.location",
        )

    wafs = of_type("azurerm_web_application_firewall_policy")
    for index, tf_type in enumerate(types):
        if not tf_type.startswith("azurerm_") or tf_type == "azurerm_unmapped":
            continue
        name_expr, loc_expr = group_expr(index)
        links[index]["rg"] = name_expr
        links[index]["loc"] = loc_expr
        if tf_type in needs_subnet:
            links[index]["subnet_id"] = subnet_expr(index)
        if tf_type == "azurerm_linux_virtual_machine":
            links[index]["nic_id"] = f"azurerm_network_interface.{addresses[index]}.id"
            extras.append(
                f'resource "azurerm_network_interface" "{addresses[index]}" {{\n'
                f'  name                = "nic-{_dns_name(safe_label(resources[index].name), index, 48)}"\n'
                f"  location            = {loc_expr}\n"
                f"  resource_group_name = {name_expr}\n"
                "  ip_configuration {\n"
                '    name                          = "internal"\n'
                f"    subnet_id                     = {links[index]['subnet_id']}\n"
                '    private_ip_address_allocation = "Dynamic"\n'
                "  }\n"
                "}\n"
            )
        if tf_type == "azurerm_application_gateway":
            pip = f"azurerm_public_ip.{addresses[index]}.id"
            links[index]["pip_id"] = pip
            extras.append(
                f'resource "azurerm_public_ip" "{addresses[index]}" {{\n'
                f'  name                = "pip-{_dns_name(safe_label(resources[index].name), index, 48)}"\n'
                f"  location            = {loc_expr}\n"
                f"  resource_group_name = {name_expr}\n"
                '  allocation_method   = "Static"\n'
                '  sku                 = "Standard"\n'
                "}\n"
            )
            if wafs:
                links[index]["waf_id"] = f"azurerm_web_application_firewall_policy.{addresses[wafs[0]]}.id"
        if tf_type == "azurerm_nat_gateway":
            extras.append(
                f'resource "azurerm_public_ip" "{addresses[index]}" {{\n'
                f'  name                = "pip-{_dns_name(safe_label(resources[index].name), index, 48)}"\n'
                f"  location            = {loc_expr}\n"
                f"  resource_group_name = {name_expr}\n"
                '  allocation_method   = "Static"\n'
                '  sku                 = "Standard"\n'
                "}\n"
            )
            extras.append(
                f'resource "azurerm_nat_gateway_public_ip_association" "{addresses[index]}" {{\n'
                f"  nat_gateway_id       = azurerm_nat_gateway.{addresses[index]}.id\n"
                f"  public_ip_address_id = azurerm_public_ip.{addresses[index]}.id\n"
                "}\n"
            )
            if "subnet_id" in links[index]:
                extras.append(
                    f'resource "azurerm_subnet_nat_gateway_association" "{addresses[index]}" {{\n'
                    f"  subnet_id      = {links[index]['subnet_id']}\n"
                    f"  nat_gateway_id = azurerm_nat_gateway.{addresses[index]}.id\n"
                    "}\n"
                )
    return links, extras


def _gcp_links(
    resources: list[Resource],
    plans: list[dict],
    types: list[str],
    addresses: list[str],
    links: list[dict],
) -> None:
    """Point each subnetwork at a VPC. A subnet with no VPC stays ungenerated."""
    networks = [index for index, tf_type in enumerate(types) if tf_type == "google_compute_network"]
    subnets = [index for index, tf_type in enumerate(types) if tf_type == "google_compute_subnetwork"]
    for offset, index in enumerate(subnets):
        found = _ancestor(
            resources,
            resources[index].parent_id,
            lambda item: types[item] == "google_compute_network",
        )
        chosen = found if found is not None else (networks[0] if networks else None)
        if chosen is None:
            plans[index] = {
                "status": "supplement",
                "tf_type": "google_compute_subnetwork",
                "missing": ("VPC",),
            }
            types[index] = "gcp_supplement"
            continue
        links[index]["network"] = f"google_compute_network.{addresses[chosen]}.id"
        links[index]["prefix"] = f"10.0.{offset + 1}.0/24"


def _aws_links(
    resources: list[Resource],
    plans: list[dict],
    types: list[str],
    addresses: list[str],
    links: list[dict],
) -> None:
    """Attach an internet gateway to a VPC. Without a VPC it stays ungenerated."""
    vpcs = [index for index, tf_type in enumerate(types) if tf_type == "aws_vpc"]
    for index, tf_type in enumerate(types):
        if tf_type != "aws_internet_gateway":
            continue
        found = _ancestor(resources, resources[index].parent_id, lambda item: types[item] == "aws_vpc")
        chosen = found if found is not None else (vpcs[0] if vpcs else None)
        if chosen is None:
            plans[index] = {
                "status": "supplement",
                "tf_type": "aws_internet_gateway",
                "missing": ("VPC",),
            }
            types[index] = "aws_supplement"
            continue
        links[index]["vpc_id"] = f"aws_vpc.{addresses[chosen]}.id"


def _provider_block(types: list[str]) -> str:
    names = _provider_names(types)
    if not names:
        return ""
    lines = ["terraform {", "  required_providers {"]
    for name in names:
        lines.append(f"    {name} = {{")
        lines.append(f'      source  = "{_PROVIDER_SOURCE[name]}"')
        version = {"azurerm": "~> 4.81", "aws": "~> 5.0", "google": "~> 6.0"}.get(name)
        if version:
            lines.append(f'      version = "{version}"')
        lines.append("    }")
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def _provider_config(types: list[str]) -> str:
    names = _provider_names(types)
    parts = []
    if "azurerm" in names:
        parts.append(
            'provider "azurerm" {\n'
            "  features {}\n"
            "  subscription_id = var.subscription_id\n"
            "}"
        )
    if "aws" in names:
        parts.append('provider "aws" {\n  region = var.location\n}')
    if "google" in names:
        parts.append('provider "google" {\n  project = var.project_id\n  region  = var.location\n}')
    return "\n\n".join(parts)


def _resource_block(
    resource: Resource,
    index: int,
    tf_type: str,
    *,
    experimental: bool,
    link: dict | None = None,
) -> str:
    label = safe_label(resource.name)
    cloud = safe_label(resource.cloud)
    header = ""
    if experimental:
        header = f"# {EXPERIMENTAL_MARKER}: non-primary cloud {cloud}\n"
    link = link or {}
    if link.get("gap") == "supplement" or tf_type.endswith("_supplement"):
        intended = link.get("intended") or "unknown"
        missing = link.get("missing") or "部署所需欄位"
        return (
            f"{header}# 待補充: {label}_{index} 可對應 {intended}，"
            f"缺少 {missing}。未產生資源。\n"
        )
    if tf_type.endswith("_unsupported") or tf_type == "azurerm_unmapped":
        return f"{header}# 無法轉換: {label}_{index} 沒有支援的 Terraform 資源，未產生資源。\n"
    body = _resource_body(tf_type, label, index, link)
    return f'{header}resource "{tf_type}" "{label}_{index}" {{\n{body}}}\n'


def _dns_name(label: str, index: int, limit: int = 63) -> str:
    slug = re.sub(r"[^a-z0-9]", "-", label.lower()).strip("-") or "resource"
    return f"cloud360-{slug}-{index}"[:limit].strip("-")


def _storage_account_name(label: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]", "", label.lower()) or "res"
    return f"c360{slug}{index}"[:24]


def _application_gateway(dns: str, loc: str, rg: str, subnet_id: str, pip_id: str, waf_id: str) -> str:
    sku = "WAF_v2" if waf_id else "Standard_v2"
    firewall = f"  firewall_policy_id  = {waf_id}\n" if waf_id else ""
    return (
        f'  name                = "{dns}"\n'
        f"  resource_group_name = {rg}\n"
        f"  location            = {loc}\n"
        f"{firewall}"
        "  sku {\n"
        f'    name     = "{sku}"\n'
        f'    tier     = "{sku}"\n'
        "    capacity = 1\n"
        "  }\n"
        "  gateway_ip_configuration {\n"
        '    name      = "gateway"\n'
        f"    subnet_id = {subnet_id}\n"
        "  }\n"
        "  frontend_port {\n"
        '    name = "http"\n'
        "    port = 80\n"
        "  }\n"
        "  frontend_ip_configuration {\n"
        '    name                 = "frontend"\n'
        f"    public_ip_address_id = {pip_id}\n"
        "  }\n"
        "  backend_address_pool {\n"
        '    name = "pool"\n'
        "  }\n"
        "  backend_http_settings {\n"
        '    name                  = "http"\n'
        '    cookie_based_affinity = "Disabled"\n'
        "    port                  = 80\n"
        '    protocol              = "Http"\n'
        "    request_timeout       = 30\n"
        "  }\n"
        "  http_listener {\n"
        '    name                           = "http"\n'
        '    frontend_ip_configuration_name = "frontend"\n'
        '    frontend_port_name             = "http"\n'
        '    protocol                       = "Http"\n'
        "  }\n"
        "  request_routing_rule {\n"
        '    name                       = "http"\n'
        '    rule_type                  = "Basic"\n'
        "    priority                   = 100\n"
        '    http_listener_name         = "http"\n'
        '    backend_address_pool_name  = "pool"\n'
        '    backend_http_settings_name = "http"\n'
        "  }\n"
    )


def _resource_body(tf_type: str, label: str, index: int, link: dict | None = None) -> str:
    dns = _dns_name(label, index)
    short = _dns_name(label, index, 32)
    account = _storage_account_name(label, index)
    link = link or {}
    rg = link.get("rg", "var.resource_group_name")
    loc = link.get("loc", "var.location")
    vnet = link.get("vnet", "azurerm_virtual_network.generated.name")
    prefix = link.get("prefix", "10.0.1.0/24")
    subnet_id = link.get("subnet_id", "azurerm_subnet.generated.id")
    nic_id = link.get("nic_id", f"azurerm_network_interface.{label}_{index}.id")
    pip_id = link.get("pip_id", f"azurerm_public_ip.{label}_{index}.id")
    waf_id = link.get("waf_id", "")
    role = "arn:aws:iam::123456789012:role/cloud360"
    bodies = {
        "aws_s3_bucket": f'  bucket = "{dns}"\n  tags   = {{ Name = "{label}" }}\n',
        "aws_instance": (
            '  ami           = "ami-00000000000000000"\n'
            '  instance_type = "t3.micro"\n'
            f'  tags          = {{ Name = "{label}" }}\n'
        ),
        "aws_vpc": (
            '  cidr_block = "10.0.0.0/16"\n'
            f'  tags       = {{ Name = "{label}" }}\n'
        ),
        "aws_subnet": (
            '  vpc_id     = "vpc-00000000"\n'
            '  cidr_block = "10.0.1.0/24"\n'
            f'  tags       = {{ Name = "{label}" }}\n'
        ),
        "aws_db_instance": (
            f'  identifier        = "{dns}"\n'
            '  engine            = "postgres"\n'
            '  instance_class    = "db.t3.micro"\n'
            "  allocated_storage = 20\n"
            '  username          = "cloud360"\n'
            f'  tags              = {{ Name = "{label}" }}\n'
        ),
        "aws_dynamodb_table": (
            f'  name         = "{dns}"\n'
            '  billing_mode = "PAY_PER_REQUEST"\n'
            '  hash_key     = "id"\n'
            "  attribute {\n"
            '    name = "id"\n'
            '    type = "S"\n'
            "  }\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "aws_lambda_function": (
            f'  function_name = "{dns}"\n'
            f'  role          = "{role}"\n'
            '  handler       = "index.handler"\n'
            '  runtime       = "nodejs20.x"\n'
            '  filename      = "placeholder.zip"\n'
            f'  tags          = {{ Name = "{label}" }}\n'
        ),
        "aws_eks_cluster": (
            f'  name     = "{dns}"\n'
            f'  role_arn = "{role}"\n'
            "  vpc_config {\n"
            '    subnet_ids = ["subnet-00000000"]\n'
            "  }\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "aws_lb": (
            f'  name               = "{short}"\n'
            '  load_balancer_type = "application"\n'
            '  subnets            = ["subnet-00000000", "subnet-00000001"]\n'
            f'  tags               = {{ Name = "{label}" }}\n'
        ),
        "aws_internet_gateway": (
            f'  vpc_id = {link.get("vpc_id", "aws_vpc.generated.id")}\n'
            f'  tags   = {{ Name = "{label}" }}\n'
        ),
        "aws_secretsmanager_secret": f'  name = "{dns}"\n  tags = {{ Name = "{label}" }}\n',
        "aws_kms_key": f'  description = "{label}"\n  tags        = {{ Name = "{label}" }}\n',
        "aws_cognito_user_pool": f'  name = "{dns}"\n',
        "aws_ecs_cluster": f'  name = "{dns}"\n  tags = {{ Name = "{label}" }}\n',
        "aws_sqs_queue": f'  name = "{dns}"\n  tags = {{ Name = "{label}" }}\n',
        "aws_sns_topic": f'  name = "{dns}"\n  tags = {{ Name = "{label}" }}\n',
        "aws_iam_role": (
            f'  name = "{dns}"\n'
            "  assume_role_policy = jsonencode({\n"
            '    Version = "2012-10-17"\n'
            "    Statement = [{\n"
            '      Effect    = "Allow"\n'
            '      Principal = { Service = "ec2.amazonaws.com" }\n'
            '      Action    = "sts:AssumeRole"\n'
            "    }]\n"
            "  })\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "aws_api_gateway_rest_api": (
            f'  name = "{dns}"\n'
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "aws_cloudfront_distribution": (
            "  enabled = true\n"
            "  origin {\n"
            f'    domain_name = "{dns}.example.com"\n'
            f'    origin_id   = "{label}"\n'
            "  }\n"
            "  default_cache_behavior {\n"
            '    allowed_methods        = ["GET", "HEAD"]\n'
            '    cached_methods         = ["GET", "HEAD"]\n'
            f'    target_origin_id       = "{label}"\n'
            '    viewer_protocol_policy = "allow-all"\n'
            "  }\n"
            "  restrictions {\n"
            "    geo_restriction {\n"
            '      restriction_type = "none"\n'
            "    }\n"
            "  }\n"
            "  viewer_certificate {\n"
            "    cloudfront_default_certificate = true\n"
            "  }\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "google_storage_bucket": (
            f'  name     = "{dns}"\n'
            '  location = "US"\n'
            f'  labels = {{ name = "{label}" }}\n'
        ),
        "google_compute_network": (
            f'  name                    = "{dns}"\n'
            "  project                 = var.project_id\n"
            "  auto_create_subnetworks = false\n"
        ),
        "google_compute_subnetwork": (
            f'  name          = "{dns}"\n'
            "  project       = var.project_id\n"
            "  region        = var.location\n"
            f'  ip_cidr_range = "{link.get("prefix", "10.0.1.0/24")}"\n'
            f'  network       = {link.get("network", "google_compute_network.generated.id")}\n'
        ),
        "google_compute_instance": (
            f'  name         = "{dns}"\n'
            '  machine_type = "e2-micro"\n'
            '  zone         = "us-central1-a"\n'
            "  boot_disk {\n"
            "    initialize_params {\n"
            '      image = "debian-cloud/debian-12"\n'
            "    }\n"
            "  }\n"
            "  network_interface {\n"
            '    network = "default"\n'
            "  }\n"
            f'  labels = {{ name = "{label}" }}\n'
        ),
        "google_sql_database_instance": (
            f'  name             = "{dns}"\n'
            '  database_version = "POSTGRES_15"\n'
            '  region           = "us-central1"\n'
            "  settings {\n"
            '    tier = "db-f1-micro"\n'
            "  }\n"
        ),
        "google_container_cluster": (
            f'  name     = "{dns}"\n'
            '  location = "us-central1"\n'
        ),
        "google_cloud_run_v2_service": (
            f'  name     = "{dns}"\n'
            '  location = "us-central1"\n'
            "  template {\n"
            "    containers {\n"
            '      image = "us-docker.pkg.dev/cloudrun/container/hello"\n'
            "    }\n"
            "  }\n"
        ),
        "google_bigquery_dataset": (
            f'  dataset_id = "{label}_{index}"\n'
            '  location   = "US"\n'
        ),
        "google_pubsub_topic": (
            f'  name    = "{dns}"\n'
            "  project = var.project_id\n"
        ),
        "google_kms_key_ring": (
            f'  name     = "{dns}"\n'
            "  project  = var.project_id\n"
            "  location = var.location\n"
        ),
        "azurerm_resource_group": (
            f'  name     = "{dns}"\n'
            "  location = var.location\n"
        ),
        "azurerm_storage_account": (
            f'  name                     = "{account}"\n'
            f"  resource_group_name      = {rg}\n"
            f"  location                 = {loc}\n"
            '  account_tier             = "Standard"\n'
            '  account_replication_type = "LRS"\n'
            f'  tags                     = {{ Name = "{label}" }}\n'
        ),
        "azurerm_kubernetes_cluster": (
            f'  name                = "{dns}"\n'
            f"  location            = {loc}\n"
            f"  resource_group_name = {rg}\n"
            f'  dns_prefix          = "{dns}"\n'
            "  default_node_pool {\n"
            '    name           = "default"\n'
            "    node_count     = 1\n"
            '    vm_size        = "Standard_B2s"\n'
            f"    vnet_subnet_id = {subnet_id}\n"
            "  }\n"
            "  identity {\n"
            '    type = "SystemAssigned"\n'
            "  }\n"
            "  network_profile {\n"
            '    network_plugin = "azure"\n'
            "  }\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "azurerm_mssql_server": (
            f'  name                         = "{dns}"\n'
            f"  resource_group_name          = {rg}\n"
            f"  location                     = {loc}\n"
            '  version                      = "12.0"\n'
            '  administrator_login          = "cloud360"\n'
            "  administrator_login_password = var.administrator_login_password\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "azurerm_cosmosdb_account": (
            f'  name                = "{dns}"\n'
            f"  location            = {loc}\n"
            f"  resource_group_name = {rg}\n"
            '  offer_type          = "Standard"\n'
            "  consistency_policy {\n"
            '    consistency_level = "Session"\n'
            "  }\n"
            "  geo_location {\n"
            f"    location          = {loc}\n"
            "    failover_priority = 0\n"
            "  }\n"
        ),
        "azurerm_virtual_network": (
            f'  name                = "{dns}"\n'
            '  address_space       = ["10.0.0.0/16"]\n'
            f"  location            = {loc}\n"
            f"  resource_group_name = {rg}\n"
            f'  tags                = {{ Name = "{label}" }}\n'
        ),
        "azurerm_subnet": (
            f'  name                 = "{short}"\n'
            f"  resource_group_name  = {rg}\n"
            f"  virtual_network_name = {vnet}\n"
            f'  address_prefixes     = ["{prefix}"]\n'
        ),
        "azurerm_nat_gateway": (
            f'  name                = "{dns}"\n'
            f"  location            = {loc}\n"
            f"  resource_group_name = {rg}\n"
            '  sku_name            = "Standard"\n'
        ),
        "azurerm_cdn_profile": (
            f'  name                = "{dns}"\n'
            f"  location            = {loc}\n"
            f"  resource_group_name = {rg}\n"
            '  sku                 = "Standard_Microsoft"\n'
        ),
        "azurerm_cdn_frontdoor_profile": (
            f'  name                = "{dns}"\n'
            f"  resource_group_name = {rg}\n"
            '  sku_name            = "Standard_AzureFrontDoor"\n'
        ),
        "azurerm_log_analytics_workspace": (
            f'  name                = "{dns}"\n'
            f"  location            = {loc}\n"
            f"  resource_group_name = {rg}\n"
            '  sku                 = "PerGB2018"\n'
            "  retention_in_days   = 30\n"
        ),
        "azurerm_key_vault": (
            f'  name                       = "{_dns_name(label, index, 24)}"\n'
            f"  location                   = {loc}\n"
            f"  resource_group_name        = {rg}\n"
            "  tenant_id                  = var.tenant_id\n"
            '  sku_name                   = "standard"\n'
            "  soft_delete_retention_days = 7\n"
        ),
        "azurerm_web_application_firewall_policy": (
            f'  name                = "{short}"\n'
            f"  location            = {loc}\n"
            f"  resource_group_name = {rg}\n"
            "  policy_settings {\n"
            "    enabled = true\n"
            '    mode    = "Prevention"\n'
            "  }\n"
            "  managed_rules {\n"
            "    managed_rule_set {\n"
            '      type    = "OWASP"\n'
            '      version = "3.2"\n'
            "    }\n"
            "  }\n"
        ),
        "azurerm_application_gateway": _application_gateway(dns, loc, rg, subnet_id, pip_id, waf_id),
        "azurerm_linux_virtual_machine": (
            f'  name                            = "{dns}"\n'
            f'  computer_name                   = "c360{index}"\n'
            f"  resource_group_name             = {rg}\n"
            f"  location                        = {loc}\n"
            '  size                            = "Standard_B1s"\n'
            '  admin_username                  = "cloud360"\n'
            "  disable_password_authentication = true\n"
            f"  network_interface_ids           = [{nic_id}]\n"
            "  os_disk {\n"
            '    caching              = "ReadWrite"\n'
            '    storage_account_type = "Standard_LRS"\n'
            "  }\n"
            "  admin_ssh_key {\n"
            '    username   = "cloud360"\n'
            "    public_key = var.admin_ssh_public_key\n"
            "  }\n"
            "  source_image_reference {\n"
            '    publisher = "Canonical"\n'
            '    offer     = "0001-com-ubuntu-server-jammy"\n'
            '    sku       = "22_04-lts"\n'
            '    version   = "latest"\n'
            "  }\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
    }
    return bodies.get(tf_type, f'  tags = {{ Name = "{label}" }}\n')
