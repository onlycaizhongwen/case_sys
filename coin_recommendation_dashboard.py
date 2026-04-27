#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""推荐币子系统本地服务：每小时自动执行分析并提供可视化页面。"""

import argparse
import json
import mimetypes
import threading
import time
from urllib.parse import urlsplit
from dataclasses import asdict, dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from binance_day_contract_realtime_v5 import (
    RecommendationConfig,
    RuntimeConfig,
    build_recommendation_config,
    execute_analysis,
    load_json_config,
)

DEFAULT_DASHBOARD_CONFIG = "dashboard_runtime_config.json"


@dataclass
class DashboardServiceState:
    """仪表盘服务状态。"""

    running: bool = False
    last_run_at: str = ""
    last_success_at: str = ""
    last_error: str = ""
    last_duration_seconds: float = 0.0
    run_count: int = 0
    next_run_at: str = ""
    latest_result: Dict[str, Any] = field(
        default_factory=lambda: {
            "generated_at": "",
            "metadata": {},
            "total": 0,
            "recommendations": [],
            "strategy_results": {},
            "view_results": {},
            "default_view": "bullish",
            "default_strategy": "long_term",
        }
    )


class RecommendationDashboardService:
    """调度与状态管理服务。"""

    def __init__(
        self,
        runtime_config: RuntimeConfig,
        recommendation_config: RecommendationConfig,
        interval_seconds: int = 3600,
    ):
        self.runtime_config = runtime_config
        self.recommendation_config = recommendation_config
        self.interval_seconds = interval_seconds
        self.state = DashboardServiceState()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.scheduler_thread: Optional[threading.Thread] = None
        self.latest_result_mtime: float = 0.0
        self.load_latest_result_from_disk()

    def load_latest_result_from_disk(self) -> None:
        """从最新 JSON 结果中恢复状态。"""
        latest_json = Path(self.runtime_config.output_dir) / self.runtime_config.latest_json_name
        if not latest_json.exists():
            return

        try:
            current_mtime = latest_json.stat().st_mtime
            with latest_json.open("r", encoding="utf-8-sig") as file:
                payload = json.load(file)

            with self.lock:
                self.state.latest_result = payload
                self.state.last_success_at = payload.get("generated_at", "")
                self.latest_result_mtime = current_mtime
        except Exception as exc:
            with self.lock:
                self.state.last_error = f"恢复本地结果失败: {exc}"

    def refresh_latest_result_from_disk(self) -> None:
        """如果磁盘结果更新了，就同步到当前服务状态。"""
        latest_json = Path(self.runtime_config.output_dir) / self.runtime_config.latest_json_name
        if not latest_json.exists():
            return

        try:
            current_mtime = latest_json.stat().st_mtime
            if current_mtime <= self.latest_result_mtime:
                return

            with latest_json.open("r", encoding="utf-8-sig") as file:
                payload = json.load(file)

            with self.lock:
                if current_mtime > self.latest_result_mtime:
                    self.state.latest_result = payload
                    self.state.last_success_at = payload.get("generated_at", "")
                    self.latest_result_mtime = current_mtime
        except Exception as exc:
            with self.lock:
                self.state.last_error = f"读取最新结果失败: {exc}"

    def build_status_payload(self) -> Dict[str, Any]:
        """输出当前服务状态。"""
        self.refresh_latest_result_from_disk()
        with self.lock:
            recommendations = self.state.latest_result.get("recommendations", [])
            tier_summary: Dict[str, int] = {}
            for item in recommendations:
                tier = item.get("tier", "UNKNOWN")
                tier_summary[tier] = tier_summary.get(tier, 0) + 1

            return {
                "service": {
                    "running": self.state.running,
                    "last_run_at": self.state.last_run_at,
                    "last_success_at": self.state.last_success_at,
                    "last_error": self.state.last_error,
                    "last_duration_seconds": self.state.last_duration_seconds,
                    "run_count": self.state.run_count,
                    "next_run_at": self.state.next_run_at,
                    "interval_seconds": self.interval_seconds,
                },
                "summary": {
                    "recommendation_total": self.state.latest_result.get("total", 0),
                    "tier_summary": tier_summary,
                    "generated_at": self.state.latest_result.get("generated_at", ""),
                    "latest_file": str(
                        Path(self.runtime_config.output_dir) / self.runtime_config.latest_json_name
                    ),
                    "strategy_results": self.state.latest_result.get("strategy_results", {}),
                    "view_results": self.state.latest_result.get("view_results", {}),
                    "default_view": self.state.latest_result.get("default_view", "bullish"),
                    "default_strategy": self.state.latest_result.get("default_strategy", "long_term"),
                },
            }

    def build_recommendation_payload(self) -> Dict[str, Any]:
        """输出最近一次推荐结果。"""
        self.refresh_latest_result_from_disk()
        with self.lock:
            return self.state.latest_result

    def run_analysis_once(self, reason: str = "manual") -> None:
        """执行一次分析任务。"""
        with self.lock:
            if self.state.running:
                return
            self.state.running = True
            self.state.last_run_at = datetime.now().isoformat()
            self.state.last_error = ""

        start_time = time.time()
        try:
            result = execute_analysis(
                self.runtime_config,
                self.recommendation_config,
                verbose=False,
            )
            with self.lock:
                self.state.latest_result = result["recommendation_payload"]
                self.state.last_success_at = datetime.now().isoformat()
                self.state.last_duration_seconds = round(time.time() - start_time, 2)
                self.state.run_count += 1
        except Exception as exc:
            with self.lock:
                self.state.last_error = f"{reason} 触发失败: {exc}"
                self.state.last_duration_seconds = round(time.time() - start_time, 2)
        finally:
            with self.lock:
                self.state.running = False
                self.state.next_run_at = datetime.fromtimestamp(
                    time.time() + self.interval_seconds
                ).isoformat()

    def trigger_run(self, reason: str = "manual") -> bool:
        """异步触发一次分析。"""
        with self.lock:
            if self.state.running:
                return False

        threading.Thread(
            target=self.run_analysis_once,
            kwargs={"reason": reason},
            daemon=True,
            name=f"analysis-{reason}",
        ).start()
        return True

    def scheduler_loop(self) -> None:
        """后台调度：启动即执行一次，然后每小时执行。"""
        self.trigger_run(reason="startup")
        while not self.stop_event.is_set():
            with self.lock:
                if not self.state.next_run_at:
                    self.state.next_run_at = datetime.fromtimestamp(
                        time.time() + self.interval_seconds
                    ).isoformat()

            if self.stop_event.wait(self.interval_seconds):
                break
            self.trigger_run(reason="scheduled")

    def start_scheduler(self) -> None:
        """启动调度线程。"""
        self.scheduler_thread = threading.Thread(
            target=self.scheduler_loop,
            daemon=True,
            name="recommendation-scheduler",
        )
        self.scheduler_thread.start()

    def stop(self) -> None:
        """停止服务。"""
        self.stop_event.set()


def build_configs(config_path: str) -> tuple[RuntimeConfig, RecommendationConfig]:
    """从配置文件恢复服务配置。"""
    config_data = load_json_config(config_path) if config_path else {}

    runtime = RuntimeConfig()
    recommendation = RecommendationConfig()

    for field_name, value in config_data.get("runtime", {}).items():
        if field_name in RuntimeConfig.__dataclass_fields__:
            setattr(runtime, field_name, value)

    for field_name, value in config_data.get("recommendation", {}).items():
        if field_name in RecommendationConfig.__dataclass_fields__:
            setattr(recommendation, field_name, value)

    return runtime, recommendation


def resolve_dashboard_config_path(config_path: str, static_dir: str) -> str:
    """解析仪表盘服务专用配置路径。"""
    if config_path:
        return config_path

    static_path = Path(static_dir)
    candidates = [
        Path.cwd() / DEFAULT_DASHBOARD_CONFIG,
        static_path.parent / DEFAULT_DASHBOARD_CONFIG,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""


def parse_args() -> argparse.Namespace:
    """解析服务端参数。"""
    parser = argparse.ArgumentParser(description="推荐币子系统本地仪表盘")
    parser.add_argument("--host", default="127.0.0.1", help="绑定地址")
    parser.add_argument("--port", type=int, default=8011, help="绑定端口")
    parser.add_argument("--interval-seconds", type=int, default=3600, help="自动执行间隔秒数")
    parser.add_argument("--config", default="", help="分析脚本 JSON 配置文件路径")
    parser.add_argument("--static-dir", default="web", help="前端静态资源目录")
    return parser.parse_args()


def create_handler(
    service: RecommendationDashboardService, static_dir: Path
) -> type[BaseHTTPRequestHandler]:
    """创建绑定服务实例的请求处理器。"""

    class DashboardHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, file_path: Path) -> None:
            if not file_path.exists() or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "File not found")
                return

            content = file_path.read_bytes()
            mime_type, _ = mimetypes.guess_type(str(file_path))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:  # noqa: N802
            request_path = urlsplit(self.path).path

            if request_path == "/api/status":
                self._send_json(service.build_status_payload())
                return

            if request_path == "/api/recommendations":
                self._send_json(service.build_recommendation_payload())
                return

            if request_path in {"/", "/index.html"}:
                self._send_file(static_dir / "index.html")
                return

            safe_path = request_path.lstrip("/")
            self._send_file(static_dir / safe_path)

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/api/run":
                triggered = service.trigger_run(reason="manual")
                self._send_json(
                    {
                        "ok": triggered,
                        "message": "已触发分析任务" if triggered else "当前已有任务在执行中",
                    },
                    status=HTTPStatus.ACCEPTED if triggered else HTTPStatus.CONFLICT,
                )
                return

            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DashboardHandler


def main() -> None:
    """启动仪表盘服务。"""
    args = parse_args()
    resolved_config_path = resolve_dashboard_config_path(args.config, args.static_dir)
    runtime_config, recommendation_config = build_configs(resolved_config_path)
    static_dir = Path(args.static_dir)

    if resolved_config_path:
        runtime_config.config_path = resolved_config_path

    if not static_dir.exists():
        raise FileNotFoundError(f"静态资源目录不存在: {static_dir}")

    service = RecommendationDashboardService(
        runtime_config=runtime_config,
        recommendation_config=recommendation_config,
        interval_seconds=args.interval_seconds,
    )
    service.start_scheduler()

    server = ThreadingHTTPServer(
        (args.host, args.port),
        create_handler(service, static_dir),
    )
    print(f"仪表盘已启动: http://{args.host}:{args.port}")
    print(f"自动执行间隔: {args.interval_seconds} 秒")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        server.server_close()


if __name__ == "__main__":
    main()
