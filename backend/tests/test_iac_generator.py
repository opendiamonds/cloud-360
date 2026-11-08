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
