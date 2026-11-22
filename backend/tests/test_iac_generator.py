"""
@purpose IaC module generator：三檔樹、路徑不外逃、非主要雲保留
@story US2.2 US2.3 BR1.8
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from iac.iac_generate import (
    EXPERIMENTAL_MARKER,
    REQUIRED_PATHS,
    generate_module_tree,
    is_safe_relative_path,
    resources_from_diagram_summary,
)
from iac.iac_types import Resource

_IAC = Path(__file__).resolve().parents[1] / "iac"
_FORBIDDEN_ROOTS = {"httpx", "sqlalchemy", "fastapi"}
_FORBIDDEN_NAMES = {"HTTPException", "Session"}


def _names(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append((node.module or "").split(".")[0])
            found.extend(alias.name for alias in node.names)
    return found


class IacGeneratorTests(unittest.TestCase):
    def test_module_tree_contains_required_files(self):
        """
        @purpose 成功產出含 main.tf、variables.tf、outputs.tf
        @given 一個 aws 資源
        @step 呼叫 generate_module_tree
        @pass 三個路徑都在產物中且內容非空白
        @story US2.2
        """
        files = generate_module_tree([Resource("web", "aws", "node")])
        paths = {entry.path for entry in files}
        self.assertTrue(set(REQUIRED_PATHS) <= paths)
        self.assertTrue(all(entry.content.strip() for entry in files))

    def test_relative_paths_do_not_escape(self):
        """
        @purpose 資源名稱即使像路徑，產物路徑仍留在模組根
        @given 名稱為 ../../etc/passwd 的資源
        @step 呼叫 generate_module_tree 並檢查每個 path
        @pass 每個 path 通過 is_safe_relative_path 且屬於固定三檔
        @story US2.2
        """
        files = generate_module_tree([Resource("../../etc/passwd", "aws", "node")])
        for entry in files:
            self.assertTrue(is_safe_relative_path(entry.path))
            self.assertIn(entry.path, REQUIRED_PATHS)
        self.assertNotIn("../", files[0].path)

    def test_non_primary_cloud_is_not_dropped(self):
        """
        @purpose 非主要雲資源仍出現，並帶 experimental 標記
        @given 兩個 aws 與一個 gcp
        @step 產生模組樹
        @pass main.tf 同時含 gcp 與 experimental
        @story US2.2 BR1.8
        """
        files = generate_module_tree(
            [
                Resource("web", "aws", "node"),
                Resource("db", "aws", "node"),
                Resource("fn", "gcp", "node"),
            ]
        )
        main = next(entry.content for entry in files if entry.path == "main.tf")
        self.assertIn("fn", main)
        self.assertIn("gcp", main)
        self.assertIn(EXPERIMENTAL_MARKER, main)

    def test_pure_modules_do_not_import_io_or_http(self):
        """
        @purpose 純函式核心不 import httpx、資料庫 Session 或 HTTPException
        @given iac_generate.py、iac_scan.py、iac_redact.py 原始碼
        @step 以 ast 走訪 import
        @pass 沒有禁用模組或名稱
        @story BR1.8
        """
        for name in ("iac_generate.py", "iac_scan.py", "iac_redact.py"):
            tree = ast.parse((_IAC / name).read_text(encoding="utf-8"))
            found = set(_names(tree))
            self.assertTrue(found.isdisjoint(_FORBIDDEN_ROOTS), name)
            self.assertTrue(found.isdisjoint(_FORBIDDEN_NAMES), name)

    def test_empty_input_is_not_an_empty_tree(self):
        """
        @purpose 空資源清單仍回傳三個檔案
        @given 空 list
        @step 呼叫 generate_module_tree
        @pass 檔案數為 3 且每個 content 去除空白後非空
        @story US2.2
        """
        files = generate_module_tree([])
        self.assertEqual(len(files), 3)
        self.assertTrue(all(entry.content.strip() for entry in files))

    def test_emitted_files_are_terraform_only(self):
        """
        @purpose 產物副檔名只有 .tf
        @given 一個資源
        @step 檢查 path
        @pass 每個 path 以 .tf 結尾
        @story US2.2
        """
        files = generate_module_tree([Resource("web", "aws", "node")])
        self.assertTrue(all(entry.path.endswith(".tf") for entry in files))

    def test_diagram_summary_keeps_each_cloud(self):
        """
        @purpose 圖摘要的每個節點都變成資源，雲別不合併成單一值
        @given aws 與 azure 兩個節點
        @step 呼叫 resources_from_diagram_summary 再產生樹
        @pass 兩種雲都出現在 main.tf
        @story US2.2 BR1.8
        """
        resources = resources_from_diagram_summary(
            {
                "nodes": [
                    {"id": "a", "label": "ec2", "style": "aws"},
                    {"id": "b", "label": "aks", "style": "azure"},
                ]
            }
        )
        main = next(
            entry.content
            for entry in generate_module_tree(resources)
            if entry.path == "main.tf"
        )
        self.assertIn("aws", main)
        self.assertIn("azure", main)

    def test_diagram_labels_become_real_terraform_types(self):
        """
        @purpose 節點標籤對應到 Checkov 認得的 provider 資源，而不是佔位類型
        @given S3、EC2 與 Cloud SQL 三個節點
        @step 由圖摘要產生 main.tf
        @pass 三個真實類型都在，佔位類型 aws_node／gcp_node 不在
        @story US2.2 US3.1
        """
        resources = resources_from_diagram_summary(
            {
                "nodes": [
                    {"id": "a", "label": "S3", "style": "aws"},
                    {"id": "b", "label": "ec2", "style": "aws"},
                    {"id": "c", "label": "Cloud SQL", "style": "gcp"},
                ]
            }
        )
        main = next(
            entry.content
            for entry in generate_module_tree(resources)
            if entry.path == "main.tf"
        )
        self.assertIn('resource "aws_s3_bucket"', main)
        self.assertIn('resource "aws_instance"', main)
        self.assertIn('resource "google_sql_database_instance"', main)
        self.assertNotIn('resource "aws_node"', main)
        self.assertNotIn('resource "gcp_node"', main)

    def test_azure_diagram_ignores_icon_bytes(self):
        """
        @purpose Azure 服務名稱產出 azurerm 資源，圖示編碼裡的 aws 字不被當成雲別
        @given 含 image=data 且編碼中有 aws/ec2/s3 的 Azure 節點，外層群組為 Microsoft Azure
        @step 由圖摘要產生 main.tf 與 variables.tf
        @pass 出現 azurerm 虛擬機器、儲存體與 SQL；沒有 aws_ 資源，也沒有 non-primary cloud aws
        @story US2.2 US3.1
        """
        noise = "aws" + "ec2vpc s3amazon" * 8
        resources = resources_from_diagram_summary(
            {
                "nodes": [
                    {"id": "g", "label": "Microsoft Azure", "style": "rounded=0", "parent": "1"},
                    {
                        "id": "a",
                        "label": "Virtual Machine (Web)",
                        "style": f"shape=image;image=data:image/svg+xml,{noise}",
                        "parent": "g",
                    },
                    {
                        "id": "b",
                        "label": "Azure Blob Storage",
                        "style": f"shape=image;image=data:image/svg+xml,{noise}",
                        "parent": "1",
                    },
                    {
                        "id": "c",
                        "label": "NAT Gateway",
                        "style": f"shape=image;image=data:image/svg+xml,{noise}",
                        "parent": "1",
                    },
                    {
                        "id": "d",
                        "label": "Azure SQL Database",
                        "style": f"shape=image;image=data:image/svg+xml,{noise}",
                        "parent": "g",
                    },
                ]
            }
        )
        files = generate_module_tree(resources)
        main = next(entry.content for entry in files if entry.path == "main.tf")
        variables = next(entry.content for entry in files if entry.path == "variables.tf")
        self.assertIn('resource "azurerm_linux_virtual_machine"', main)
        self.assertIn('resource "azurerm_storage_account"', main)
        self.assertIn('resource "azurerm_mssql_server"', main)
        self.assertNotIn('resource "aws_', main)
        self.assertNotIn("non-primary cloud aws", main)
        self.assertIn('default     = "eastus"', variables)

    def test_unrecognized_gcp_node_is_not_a_compute_instance(self):
        """
        @purpose 認不出的 GCP 元件不產生 GCE 虛擬機器；可辨識的產生對應類型，缺資料的只標記待補充
        @given GKE、Cloud Run、VPC、Apigee 與一個無法辨識的 Zone
        @step 由圖摘要產生 main.tf
        @pass GKE、Cloud Run、VPC 是對應資源；Apigee 為待補充；雲端外框與 Zone 不出現；沒有 google_compute_instance
        @story US2.2 US3.1
        """
        resources = resources_from_diagram_summary(
            {
                "nodes": [
                    {"id": "g", "label": "Google Cloud Platform", "style": "shape=mxgraph.aws4.group;", "parent": "1"},
                    {"id": "vpc", "label": "VPC Network", "style": "shape=mxgraph.aws4.group;", "parent": "g"},
                    {"id": "gke", "label": "GKE", "style": "shape=image;image=data:image/svg+xml,awsec2", "parent": "vpc"},
                    {"id": "run", "label": "Cloud Run", "style": "shape=image;image=data:image/svg+xml,awsec2", "parent": "vpc"},
                    {"id": "api", "label": "Apigee", "style": "shape=image;image=data:image/svg+xml,awsec2", "parent": "g"},
                    {"id": "zone", "label": "Zone A", "style": "shape=mxgraph.aws4.group;", "parent": "g"},
                ]
            }
        )
        main = next(
            entry.content for entry in generate_module_tree(resources) if entry.path == "main.tf"
        )
        self.assertIn('resource "google_container_cluster"', main)
        self.assertIn('resource "google_cloud_run_v2_service"', main)
        self.assertIn('resource "google_compute_network"', main)
        self.assertIn("待補充", main)
        self.assertIn("google_apigee_organization", main)
        self.assertNotIn("無法轉換", main)
        self.assertNotIn("Google_Cloud_Platform", main)
        self.assertNotIn("Zone_A", main)
        self.assertNotIn('resource "google_compute_instance"', main)

    def test_descriptive_zone_and_layer_frames_are_omitted(self):
        """
        @purpose 名稱後面帶說明的可用區與 layer 框不寫進草稿，VPC 與 subnet 仍保留
        @given Zone A — multi-agent orchestration、Ingress & API Layer，以及 VPC 與帶 region 字樣的 subnet
        @step 由圖摘要產生 main.tf
        @pass 兩個圖層名稱不出現；VPC 與 subnet 有對應資源
        @story US2.2 US3.1
        """
        frame = "shape=mxgraph.aws4.group;fillcolor=#fffdf0;"
        resources = resources_from_diagram_summary(
            {
                "nodes": [
                    {"id": "g", "label": "Google Cloud Platform", "style": frame, "parent": "1"},
                    {"id": "vpc", "label": "VPC Network", "style": frame, "parent": "g"},
                    {"id": "za", "label": "Zone A — multi-agent orchestration", "style": frame, "parent": "vpc"},
                    {"id": "zb", "label": "Zone B — multi-agent orchestration (HA standby)", "style": frame, "parent": "vpc"},
                    {"id": "ing", "label": "Ingress & API Layer", "style": frame, "parent": "vpc"},
                    {"id": "ai", "label": "AI & Model Layer", "style": frame, "parent": "vpc"},
                    {"id": "data", "label": "Data & Memory Layer (multi-region)", "style": frame, "parent": "vpc"},
                    {"id": "sub", "label": "Application Subnet (region 2 - us)", "style": frame, "parent": "za"},
                    {"id": "gke", "label": "GKE", "style": "shape=image;image=data:image/svg+xml,awsec2", "parent": "za"},
                ]
            }
        )
        main = next(entry.content for entry in generate_module_tree(resources) if entry.path == "main.tf")
        self.assertIn('resource "google_compute_network"', main)
        self.assertIn('resource "google_compute_subnetwork"', main)
        self.assertIn('resource "google_container_cluster"', main)
        for gone in ("multi_agent_orchestration", "API_Layer", "Model_Layer", "Memory_Layer"):
            self.assertNotIn(gone, main)

    def test_prompt_service_names_follow_the_drawing_catalog(self):
        """
        @purpose 畫圖 prompt 裡的服務名稱要對到 Terraform 類型，外框與使用者節點不產生資源
        @given 畫圖清單中的 Pub/Sub、Cloud KMS、Cloud NAT、Route 53、Secrets Manager、DB Subnet、Internet Gateway、Azure DNS，以及 User 與 Zone
        @step 由圖摘要產生 main.tf
        @pass 可產出的服務是對應資源；缺欄位的標成待補充；外框與 Zone 不出現；User 標成無法轉換
        @story US2.2 US3.1
        """
        resources = resources_from_diagram_summary(
            {
                "nodes": [
                    {"id": "g", "label": "Google Cloud Platform", "style": "", "parent": "1"},
                    {"id": "pub", "label": "Pub/Sub", "style": "", "parent": "g"},
                    {"id": "kms", "label": "Cloud KMS", "style": "", "parent": "g"},
                    {"id": "nat", "label": "Cloud NAT", "style": "", "parent": "g"},
                    {"id": "zone", "label": "Zone A", "style": "", "parent": "g"},
                    {"id": "user", "label": "User", "style": "", "parent": "1"},
                    {"id": "aws", "label": "AWS Cloud", "style": "", "parent": "1"},
                    {"id": "vpc", "label": "VPC", "style": "", "parent": "aws"},
                    {"id": "dbsub", "label": "DB Subnet 1", "style": "", "parent": "vpc"},
                    {"id": "igw", "label": "Internet Gateway (IGW)", "style": "", "parent": "vpc"},
                    {"id": "r53", "label": "Route 53", "style": "", "parent": "aws"},
                    {"id": "sec", "label": "Secrets Manager", "style": "", "parent": "aws"},
                    {"id": "az", "label": "Microsoft Azure", "style": "", "parent": "1"},
                    {"id": "dns", "label": "Azure DNS", "style": "", "parent": "az"},
                    {"id": "files", "label": "Azure Files", "style": "", "parent": "az"},
                    {"id": "redis", "label": "Azure Cache for Redis", "style": "", "parent": "az"},
                    {"id": "lb", "label": "Azure Load Balancer (Internal)", "style": "", "parent": "az"},
                ]
            }
        )
        main = next(entry.content for entry in generate_module_tree(resources) if entry.path == "main.tf")
        self.assertIn('resource "google_pubsub_topic"', main)
        self.assertIn('resource "google_kms_key_ring"', main)
        self.assertIn("google_compute_router_nat", main)
        self.assertIn('resource "aws_subnet"', main)
        self.assertNotIn('resource "aws_db_instance"', main)
        self.assertIn('resource "aws_internet_gateway"', main)
        self.assertIn("aws_vpc.", main)
        self.assertIn("aws_route53_zone", main)
        self.assertIn('resource "aws_secretsmanager_secret"', main)
        self.assertIn("azurerm_dns_zone", main)
        self.assertIn("azurerm_storage_share", main)
        self.assertIn("azurerm_redis_cache", main)
        self.assertIn("azurerm_lb", main)
        self.assertIn("無法轉換: User_", main)
        self.assertNotIn("Google_Cloud_Platform", main)
        self.assertNotIn("Zone_A", main)
        self.assertNotIn("AWS_Cloud", main)
        self.assertNotIn("Microsoft_Azure", main)
        self.assertNotIn('resource "google_compute_instance"', main)
        self.assertNotIn('resource "aws_instance"', main)

    def test_aws_group_frame_does_not_override_an_azure_label(self):
        """
        @purpose Azure 圖即使外框使用 mxgraph.aws4.group，仍產出 azurerm 資源
        @given 標籤為 azure subscription／azure vnet，樣式為 AWS group frame，子節點為 public subnet 與 WAF
        @step 由圖摘要產生 main.tf
        @pass 沒有 aws_ 資源，subnet 為 azurerm_subnet，WAF 跟著 Azure
        @story US2.2 US3.1
        """
        frame = "shape=mxgraph.aws4.group;strokecolor=#0078d4;fillcolor=none;"
        resources = resources_from_diagram_summary(
            {
                "nodes": [
                    {"id": "az_cloud", "label": "azure subscription", "style": frame, "parent": "1"},
                    {"id": "vnet", "label": "azure vnet", "style": frame, "parent": "az_cloud"},
                    {"id": "pub_sub", "label": "public subnet", "style": frame, "parent": "vnet"},
                    {
                        "id": "waf",
                        "label": "web application firewall",
                        "style": "shape=image;image=data:image/svg+xml,awsec2s3vpc",
                        "parent": "pub_sub",
                    },
                ]
            }
        )
        main = next(
            entry.content for entry in generate_module_tree(resources) if entry.path == "main.tf"
        )
        self.assertIn('resource "azurerm_virtual_network"', main)
        self.assertIn('resource "azurerm_subnet"', main)
        self.assertIn("azurerm_virtual_network.azure_vnet_1.name", main)
        self.assertIn('resource "azurerm_web_application_firewall_policy"', main)
        self.assertIn('resource "azurerm_resource_group"', main)
        self.assertIn("features {}", main)
        self.assertNotIn("vnet-placeholder", main)
        self.assertNotIn("nic-placeholder", main)
        self.assertNotIn('resource "aws_', main)
        self.assertNotIn("non-primary cloud aws", main)


class IacGeneratorProperties(unittest.TestCase):
    @given(
        st.lists(
            st.tuples(
                st.sampled_from(["aws", "gcp", "azure", "generic"]),
                st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,8}", fullmatch=True),
            ),
            min_size=1,
            max_size=6,
            unique_by=lambda item: item[1],
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_every_name_and_non_primary_marker(self, pairs):
        """
        @purpose 每個輸入名稱都出現；非主要雲帶 experimental
        @given 1 到 6 個不重複名稱與雲別
        @step 產生 main.tf
        @pass 每個名稱都在內容中；非主要雲的標記與雲名都在
        @story US2.2 BR1.8
        """
        resources = [Resource(name, cloud, "node") for cloud, name in pairs]
        main = next(
            entry.content
            for entry in generate_module_tree(resources)
            if entry.path == "main.tf"
        )
        for resource in resources:
            self.assertIn(resource.name, main)
        self.assertNotRegex(main, r'resource "(?:aws|gcp|azure|generic)_node"')
        counts: dict[str, int] = {}
        for resource in resources:
            counts[resource.cloud] = counts.get(resource.cloud, 0) + 1
        primary = sorted(counts, key=lambda cloud: (-counts[cloud], cloud))[0]
        for cloud in counts:
            if cloud != primary:
                self.assertIn(EXPERIMENTAL_MARKER, main)
                self.assertIn(cloud, main)


if __name__ == "__main__":
    unittest.main()
