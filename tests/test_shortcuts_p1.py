"""Phase 5.1 P1 shortcut tools 测试（drive / wiki）。"""

import json
from unittest.mock import patch

import pytest

from lark_mcp_bridge.executor import ExecutionResult
from lark_mcp_bridge.server import (
    drive_download,
    drive_upload,
    wiki_get_node,
    wiki_search,
)


class TestDriveUpload:
    """lark.drive.upload 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_upload(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"file_token": "boxcnXXX"}},
            duration_ms=1000,
        )
        output = drive_upload(file="report.pdf")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+upload" in call_args
        assert "--file" in call_args
        assert "report.pdf" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_upload_to_folder(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=500
        )
        drive_upload(file="doc.pdf", folder_token="fldcnXXX")
        call_args = mock_execute.call_args[0][0]
        assert "--folder-token" in call_args
        assert "fldcnXXX" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_upload_to_wiki(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=500
        )
        drive_upload(file="doc.pdf", wiki_token="wikcnXXX")
        call_args = mock_execute.call_args[0][0]
        assert "--wiki-token" in call_args
        assert "--folder-token" not in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_upload_with_name(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=500
        )
        drive_upload(file="a.pdf", name="报告.pdf")
        call_args = mock_execute.call_args[0][0]
        assert "--name" in call_args
        assert "报告.pdf" in call_args


class TestDriveDownload:
    """lark.drive.download 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_download(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"path": "./report.pdf"}},
            duration_ms=800,
        )
        output = drive_download(file_token="boxcnXXX")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+download" in call_args
        assert "--file-token" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_download_with_output(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True}, duration_ms=600
        )
        drive_download(file_token="boxcnXXX", output="./downloads/file.pdf")
        call_args = mock_execute.call_args[0][0]
        assert "--output" in call_args
        assert "./downloads/file.pdf" in call_args


class TestWikiSearch:
    """lark.wiki.search 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_basic_search(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"docs": []}},
            duration_ms=300,
        )
        output = wiki_search(query="产品设计")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+search" in call_args
        assert "--query" in call_args
        assert "产品设计" in call_args
        assert "--format" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_search_with_doc_types(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        wiki_search(query="API", doc_types="docx,sheet")
        call_args = mock_execute.call_args[0][0]
        assert "--doc-types" in call_args
        assert "docx,sheet" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_search_custom_page_size(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        wiki_search(query="test", page_size=5)
        call_args = mock_execute.call_args[0][0]
        assert "5" in call_args


class TestWikiGetNode:
    """lark.wiki.get-node 测试。"""

    @patch("lark_mcp_bridge.server.execute")
    def test_get_by_token(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True,
            data={"ok": True, "data": {"node_token": "wikcnXXX", "title": "设计文档"}},
            duration_ms=200,
        )
        output = wiki_get_node(node_token="wikcnXXX")
        parsed = json.loads(output)
        assert parsed["ok"] is True
        call_args = mock_execute.call_args[0][0]
        assert "+node-get" in call_args
        assert "--node-token" in call_args
        assert "wikcnXXX" in call_args
        assert "--format" in call_args

    @patch("lark_mcp_bridge.server.execute")
    def test_get_by_url(self, mock_execute):
        mock_execute.return_value = ExecutionResult(
            success=True, data={"ok": True, "data": {}}, duration_ms=200
        )
        wiki_get_node(node_token="https://feishu.cn/wiki/wikcnXXX")
        call_args = mock_execute.call_args[0][0]
        assert "https://feishu.cn/wiki/wikcnXXX" in call_args
