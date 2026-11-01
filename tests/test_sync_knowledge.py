"""Test script đồng bộ knowledge với Open WebUI giả lập (không gọi mạng)."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import httpx

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_knowledge.py"
spec = importlib.util.spec_from_file_location("sync_knowledge", SCRIPT)
sync = importlib.util.module_from_spec(spec)
sys.modules["sync_knowledge"] = sync
spec.loader.exec_module(sync)


class FakeOpenWebUI:
    """Open WebUI tối giản: một Knowledge 'kb' với các file trong bộ nhớ."""

    def __init__(self, files: dict[str, str]):
        self.files = {f"id-{name}": {"name": name, "content": content} for name, content in files.items()}
        self.knowledge = set(self.files)
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/api/v1")
        self.calls.append(f"{request.method} {path}")

        if path == "/knowledge/kb/files":
            items = [{"id": fid, "filename": self.files[fid]["name"]} for fid in sorted(self.knowledge)]
            return httpx.Response(200, json={"items": items, "total": len(items)})
        if path.startswith("/files/") and path.endswith("/data/content"):
            fid = path.split("/")[2]
            return httpx.Response(200, json={"content": self.files[fid]["content"]})
        if path.endswith("/data/content/update"):
            fid = path.split("/")[2]
            self.files[fid]["content"] = json.loads(request.content)["content"]
            return httpx.Response(200, json={})
        if path == "/files/":
            name = request.content.split(b'filename="')[1].split(b'"')[0].decode()
            fid = f"id-{name}"
            self.files[fid] = {"name": name, "content": ""}
            return httpx.Response(200, json={"id": fid})
        if path == "/knowledge/kb/file/add":
            self.knowledge.add(json.loads(request.content)["file_id"])
            return httpx.Response(200, json={})
        if path == "/knowledge/kb/file/remove":
            self.knowledge.discard(json.loads(request.content)["file_id"])
            return httpx.Response(200, json={})
        if path == "/knowledge/kb/file/update":
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"detail": "not found"})


class SyncKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "README.md").write_text("không đồng bộ", encoding="utf-8")
        (self.dir / "same.md").write_text("giống\n", encoding="utf-8")
        (self.dir / "changed.md").write_text("nội dung mới", encoding="utf-8")
        (self.dir / "new.md").write_text("file mới", encoding="utf-8")

        self.server = FakeOpenWebUI({"same.md": "giống", "changed.md": "nội dung cũ", "old.md": "cũ"})
        self.client = sync.OpenWebUIClient("http://owui", "key", "kb")
        self.client.http = httpx.Client(
            base_url="http://owui/api/v1", transport=httpx.MockTransport(self.server.handler)
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_readme_is_excluded(self):
        names = [p.name for p in sync.local_files(self.dir)]
        self.assertEqual(names, ["changed.md", "new.md", "same.md"])

    def test_plan_classifies_files(self):
        plan = sync.build_plan(self.client, sync.local_files(self.dir), prune=True)

        self.assertEqual([p.name for p in plan.to_add], ["new.md"])
        self.assertEqual([p.name for p, _ in plan.to_update], ["changed.md"])
        self.assertEqual([p.name for p in plan.unchanged], ["same.md"])
        self.assertEqual([name for name, _ in plan.to_remove], ["old.md"])

    def test_without_prune_nothing_is_removed(self):
        plan = sync.build_plan(self.client, sync.local_files(self.dir), prune=False)
        self.assertEqual(plan.to_remove, [])

    def test_apply_updates_remote(self):
        plan = sync.build_plan(self.client, sync.local_files(self.dir), prune=True)
        sync.apply_plan(self.client, plan)

        self.assertEqual(self.server.files["id-changed.md"]["content"], "nội dung mới")
        self.assertIn("POST /knowledge/kb/file/update", self.server.calls)
        self.assertIn("id-new.md", self.server.knowledge)
        self.assertNotIn("id-old.md", self.server.knowledge)

    def test_error_response_raises(self):
        self.client.knowledge_id = "missing"
        with self.assertRaises(RuntimeError):
            self.client.list_files()
