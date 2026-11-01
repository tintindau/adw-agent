"""Đồng bộ thư mục knowledge/ lên một Knowledge trên Open WebUI.

Repo là nguồn gốc: file mới được thêm, file đổi nội dung được cập nhật và
embed lại, file không đổi được bỏ qua. Với --prune, file trên Open WebUI
không còn trong repo sẽ bị gỡ khỏi Knowledge.

Cấu hình (.env hoặc biến môi trường):
    OPENWEBUI_URL           vd http://localhost:3000
    OPENWEBUI_API_KEY       API key của tài khoản admin
    OPENWEBUI_KNOWLEDGE_ID  id của Knowledge (lấy trên URL)

Ví dụ:
    python scripts/sync_knowledge.py --dry-run
    python scripts/sync_knowledge.py --prune
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
EXCLUDED_FILES = {"README.md"}
PAGE_SIZE = 100

logger = logging.getLogger("sync_knowledge")


@dataclass
class Plan:
    to_add: list[Path]
    to_update: list[tuple[Path, str]]  # (file local, file_id trên Open WebUI)
    unchanged: list[Path]
    to_remove: list[tuple[str, str]]  # (tên file, file_id)


def local_files(directory: Path = KNOWLEDGE_DIR) -> list[Path]:
    """Các file markdown cần đồng bộ, sắp theo tên."""
    return sorted(
        path
        for path in directory.glob("*.md")
        if path.is_file() and path.name not in EXCLUDED_FILES
    )


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


class OpenWebUIClient:
    def __init__(self, base_url: str, api_key: str, knowledge_id: str, timeout: float = 120):
        self.knowledge_id = knowledge_id
        self.http = httpx.Client(
            base_url=base_url.rstrip("/") + "/api/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def _check(self, response: httpx.Response) -> dict:
        if response.is_error:
            detail = response.text[:300]
            raise RuntimeError(f"{response.request.method} {response.request.url.path} → {response.status_code}: {detail}")
        return response.json() if response.content else {}

    def list_files(self) -> dict[str, str]:
        """Trả về {tên file: file_id} của các file trong Knowledge."""
        files: dict[str, str] = {}
        page = 1
        while True:
            data = self._check(
                self.http.get(
                    f"/knowledge/{self.knowledge_id}/files",
                    params={"page": page, "limit": PAGE_SIZE},
                )
            )
            items = data.get("items", [])
            for item in items:
                name = item.get("filename") or (item.get("meta") or {}).get("name")
                if name:
                    files[name] = item["id"]
            if not items or len(files) >= data.get("total", 0):
                return files
            page += 1

    def get_content(self, file_id: str) -> str:
        return self._check(self.http.get(f"/files/{file_id}/data/content")).get("content", "")

    def upload(self, path: Path) -> str:
        """Upload và xử lý file (đồng bộ, không chạy nền), trả về file_id."""
        with path.open("rb") as fh:
            data = self._check(
                self.http.post(
                    "/files/",
                    params={"process": "true", "process_in_background": "false"},
                    files={"file": (path.name, fh, "text/markdown")},
                )
            )
        return data["id"]

    def add_to_knowledge(self, file_id: str) -> None:
        self._check(self.http.post(f"/knowledge/{self.knowledge_id}/file/add", json={"file_id": file_id}))

    def update_content(self, file_id: str, content: str) -> None:
        # Cập nhật nội dung file rồi embed lại trong collection của Knowledge.
        self._check(self.http.post(f"/files/{file_id}/data/content/update", json={"content": content}))
        self._check(self.http.post(f"/knowledge/{self.knowledge_id}/file/update", json={"file_id": file_id}))

    def remove_from_knowledge(self, file_id: str) -> None:
        self._check(self.http.post(f"/knowledge/{self.knowledge_id}/file/remove", json={"file_id": file_id}))


def build_plan(client: OpenWebUIClient, files: list[Path], prune: bool) -> Plan:
    remote = client.list_files()
    plan = Plan(to_add=[], to_update=[], unchanged=[], to_remove=[])

    for path in files:
        file_id = remote.get(path.name)
        if file_id is None:
            plan.to_add.append(path)
        elif normalize(client.get_content(file_id)) == normalize(path.read_text(encoding="utf-8")):
            plan.unchanged.append(path)
        else:
            plan.to_update.append((path, file_id))

    if prune:
        local_names = {path.name for path in files}
        plan.to_remove = [(name, fid) for name, fid in sorted(remote.items()) if name not in local_names]
    return plan


def apply_plan(client: OpenWebUIClient, plan: Plan) -> None:
    for path in plan.to_add:
        file_id = client.upload(path)
        client.add_to_knowledge(file_id)
        logger.info("Đã thêm %s", path.name)
    for path, file_id in plan.to_update:
        client.update_content(file_id, path.read_text(encoding="utf-8"))
        logger.info("Đã cập nhật %s", path.name)
    for name, file_id in plan.to_remove:
        client.remove_from_knowledge(file_id)
        logger.info("Đã gỡ %s", name)


def print_plan(plan: Plan) -> None:
    for path in plan.to_add:
        logger.info("+ thêm      %s", path.name)
    for path, _ in plan.to_update:
        logger.info("~ cập nhật  %s", path.name)
    for path in plan.unchanged:
        logger.info("= giữ nguyên %s", path.name)
    for name, _ in plan.to_remove:
        logger.info("- gỡ        %s", name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đồng bộ knowledge/ lên Open WebUI Knowledge")
    parser.add_argument("--dry-run", action="store_true", help="chỉ in thay đổi, không ghi")
    parser.add_argument("--prune", action="store_true", help="gỡ file trên Open WebUI không còn trong repo")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    load_dotenv(REPO_ROOT / ".env")

    config = {key: os.getenv(key, "") for key in ("OPENWEBUI_URL", "OPENWEBUI_API_KEY", "OPENWEBUI_KNOWLEDGE_ID")}
    missing = [key for key, value in config.items() if not value]
    if missing:
        logger.error("Thiếu cấu hình: %s", ", ".join(missing))
        return 2

    files = local_files()
    if not files:
        logger.error("Không có file .md nào trong %s", KNOWLEDGE_DIR)
        return 2

    client = OpenWebUIClient(
        config["OPENWEBUI_URL"], config["OPENWEBUI_API_KEY"], config["OPENWEBUI_KNOWLEDGE_ID"]
    )
    try:
        plan = build_plan(client, files, prune=args.prune)
        print_plan(plan)
        if args.dry_run:
            logger.info("(dry-run: không thay đổi gì)")
            return 0
        apply_plan(client, plan)
    except (RuntimeError, httpx.HTTPError) as exc:
        logger.error("Đồng bộ thất bại: %s", exc)
        return 1

    logger.info("Xong: %d thêm, %d cập nhật, %d gỡ.", len(plan.to_add), len(plan.to_update), len(plan.to_remove))
    return 0


if __name__ == "__main__":
    sys.exit(main())
