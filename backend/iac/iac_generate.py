"""Pure HCL module generator.

Must not import httpx, a database session, or HTTPException. LLM notes are
ignored here; the agent port lives outside this module.
"""

from __future__ import annotations

import re

from iac.iac_types import FileEntry, Resource

REQUIRED_PATHS = ("main.tf", "variables.tf", "outputs.tf")
EXPERIMENTAL_MARKER = "experimental"

_CLOUD_HINTS = (
    ("gcp", ("gcp", "google", "gke", "cloud sql", "cloud run", "gce", "bigquery")),
    ("azure", ("azure", "microsoft", "aks")),
    ("aws", ("aws", "amazon", "ec2", "vpc", "s3", "rds", "lambda", "eks")),
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


def cloud_of_node(label: str, style: str = "") -> str:
    blob = f"{label} {style}".lower()
    for cloud, hints in _CLOUD_HINTS:
        if any(hint in blob for hint in hints):
            return cloud
    return "generic"


def resources_from_diagram_summary(summary: dict) -> list[Resource]:
    """Map an existing diagram summary (nodes with label/style) to resources."""
    resources: list[Resource] = []
    for node in summary.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        label = str(node.get("label") or node.get("id") or "resource")
        style = str(node.get("style") or "")
        resources.append(
            Resource(name=label, cloud=cloud_of_node(label, style), kind="node")
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
        (("load balancer",), ("alb", "nlb", "elb", "loadbalancer"), "aws_lb"),
        (("api gateway",), ("apigateway", "gateway"), "aws_api_gateway_rest_api"),
        ((), ("rds", "aurora", "database", "db", "postgres", "mysql"), "aws_db_instance"),
        ((), ("dynamodb",), "aws_dynamodb_table"),
        ((), ("lambda", "function"), "aws_lambda_function"),
        ((), ("eks", "kubernetes", "k8s"), "aws_eks_cluster"),
        ((), ("vpc",), "aws_vpc"),
        ((), ("subnet",), "aws_subnet"),
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
        ((), ("gcs", "bucket", "storage"), "google_storage_bucket"),
        ((), ("gke", "kubernetes", "k8s"), "google_container_cluster"),
        ((), ("gce", "instance", "vm", "compute", "server"), "google_compute_instance"),
    ),
    "azure": (
        ((), ("aks", "kubernetes", "k8s"), "azurerm_kubernetes_cluster"),
        ((), ("storage", "blob", "bucket"), "azurerm_storage_account"),
        ((), ("sql", "database", "db"), "azurerm_mssql_server"),
        ((), ("vnet", "vpc", "network"), "azurerm_virtual_network"),
        ((), ("vm", "instance", "compute"), "azurerm_linux_virtual_machine"),
    ),
}

_DEFAULT_TYPE = {
    "aws": "aws_instance",
    "gcp": "google_compute_instance",
    "azure": "azurerm_linux_virtual_machine",
    "generic": "aws_instance",
}

_PROVIDER_SOURCE = {
    "aws": "hashicorp/aws",
    "google": "hashicorp/google",
    "azurerm": "hashicorp/azurerm",
}


def terraform_type(resource: Resource) -> str:
    """Real provider type for this node. Unknown labels use that cloud's compute default."""
    text = f"{resource.name} {resource.kind}".lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    for phrases, words, tf_type in _TYPE_RULES.get(resource.cloud, ()):
        if any(phrase in text for phrase in phrases) or tokens.intersection(words):
            return tf_type
    return _DEFAULT_TYPE.get(resource.cloud, "aws_instance")


def generate_module_tree(resources: list[Resource]) -> list[FileEntry]:
    """Build main/variables/outputs. Non-primary clouds stay, marked experimental."""
    primary = primary_cloud(resources)
    blocks: list[str] = [f"# primary_cloud = {primary}"]
    types = [terraform_type(resource) for resource in resources]
    providers = _provider_block(types)
    if providers:
        blocks.append(providers)
    if not resources:
        blocks.append("# no resources in diagram")
    for index, resource in enumerate(resources):
        experimental = resource.cloud != primary
        blocks.append(
            _resource_block(resource, index, types[index], experimental=experimental)
        )
    main = "\n\n".join(blocks) + "\n"
    variables = (
        'variable "name_prefix" {\n'
        "  type        = string\n"
        '  description = "Prefix for generated resources"\n'
        '  default     = "cloud360"\n'
        "}\n\n"
        'variable "location" {\n'
        "  type        = string\n"
        '  description = "Region or location for generated resources"\n'
        '  default     = "us-east-1"\n'
        "}\n\n"
        'variable "resource_group_name" {\n'
        "  type        = string\n"
        '  description = "Azure resource group name"\n'
        '  default     = "cloud360"\n'
        "}\n\n"
        'variable "administrator_login_password" {\n'
        "  type        = string\n"
        "  sensitive   = true\n"
        '  description = "SQL administrator password supplied outside this draft"\n'
        "}\n"
    )
    outputs = 'output "module_ready" {\n  value = true\n}\n'
    return [
        FileEntry("main.tf", main),
        FileEntry("variables.tf", variables),
        FileEntry("outputs.tf", outputs),
    ]


def _provider_block(types: list[str]) -> str:
    names = []
    for tf_type in types:
        provider = tf_type.split("_", 1)[0]
        if provider in _PROVIDER_SOURCE and provider not in names:
            names.append(provider)
    if not names:
        return ""
    lines = ["terraform {", "  required_providers {"]
    for name in names:
        lines.append(f"    {name} = {{")
        lines.append(f'      source = "{_PROVIDER_SOURCE[name]}"')
        lines.append("    }")
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def _resource_block(
    resource: Resource,
    index: int,
    tf_type: str,
    *,
    experimental: bool,
) -> str:
    label = safe_label(resource.name)
    cloud = safe_label(resource.cloud)
    header = ""
    if experimental:
        header = f"# {EXPERIMENTAL_MARKER}: non-primary cloud {cloud}\n"
    body = _resource_body(tf_type, label, index)
    return f'{header}resource "{tf_type}" "{label}_{index}" {{\n{body}}}\n'


def _dns_name(label: str, index: int, limit: int = 63) -> str:
    slug = re.sub(r"[^a-z0-9]", "-", label.lower()).strip("-") or "resource"
    return f"cloud360-{slug}-{index}"[:limit].strip("-")


def _storage_account_name(label: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]", "", label.lower()) or "res"
    return f"c360{slug}{index}"[:24]


def _resource_body(tf_type: str, label: str, index: int) -> str:
    dns = _dns_name(label, index)
    short = _dns_name(label, index, 32)
    account = _storage_account_name(label, index)
    role = "arn:aws:iam::123456789012:role/cloud360"
    bodies = {
        "aws_s3_bucket": f'  bucket = "{dns}"\n  tags = {{ Name = "{label}" }}\n',
        "aws_instance": (
            '  ami           = "ami-00000000000000000"\n'
            '  instance_type = "t3.micro"\n'
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "aws_vpc": (
            '  cidr_block = "10.0.0.0/16"\n'
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "aws_subnet": (
            '  vpc_id     = "vpc-00000000"\n'
            '  cidr_block = "10.0.1.0/24"\n'
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "aws_db_instance": (
            f'  identifier        = "{dns}"\n'
            '  engine            = "postgres"\n'
            '  instance_class    = "db.t3.micro"\n'
            "  allocated_storage = 20\n"
            '  username          = "cloud360"\n'
            f'  tags = {{ Name = "{label}" }}\n'
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
            f'  tags = {{ Name = "{label}" }}\n'
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
            f'  tags = {{ Name = "{label}" }}\n'
        ),
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
        "azurerm_storage_account": (
            f'  name                     = "{account}"\n'
            "  resource_group_name      = var.resource_group_name\n"
            "  location                 = var.location\n"
            '  account_tier             = "Standard"\n'
            '  account_replication_type = "LRS"\n'
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "azurerm_kubernetes_cluster": (
            f'  name                = "{dns}"\n'
            "  location            = var.location\n"
            "  resource_group_name = var.resource_group_name\n"
            f'  dns_prefix          = "{dns}"\n'
            "  default_node_pool {\n"
            '    name       = "default"\n'
            "    node_count = 1\n"
            '    vm_size    = "Standard_B2s"\n'
            "  }\n"
            "  identity {\n"
            '    type = "SystemAssigned"\n'
            "  }\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "azurerm_mssql_server": (
            f'  name                         = "{dns}"\n'
            "  resource_group_name          = var.resource_group_name\n"
            "  location                     = var.location\n"
            '  version                      = "12.0"\n'
            '  administrator_login          = "cloud360"\n'
            "  administrator_login_password = var.administrator_login_password\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "azurerm_virtual_network": (
            f'  name                = "{dns}"\n'
            '  address_space       = ["10.0.0.0/16"]\n'
            "  location            = var.location\n"
            "  resource_group_name = var.resource_group_name\n"
            f'  tags = {{ Name = "{label}" }}\n'
        ),
        "azurerm_linux_virtual_machine": (
            f'  name                  = "{dns}"\n'
            "  resource_group_name   = var.resource_group_name\n"
            "  location              = var.location\n"
            '  size                  = "Standard_B1s"\n'
            '  admin_username        = "cloud360"\n'
            '  network_interface_ids = ["nic-placeholder"]\n'
            "  os_disk {\n"
            '    caching              = "ReadWrite"\n'
            '    storage_account_type = "Standard_LRS"\n'
            "  }\n"
            "  admin_ssh_key {\n"
            '    username   = "cloud360"\n'
            '    public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPlaceholderKeyForDraftOnly cloud360"\n'
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
