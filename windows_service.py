from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import threading
import traceback
from pathlib import Path
from typing import Any

import servicemanager
import uvicorn
import win32event
import win32service
import win32serviceutil


SERVICE_NAME = "InsuranceBackendService"
SERVICE_DISPLAY_NAME = "Insurance Manager Backend Service"
SERVICE_DESCRIPTION = "Runs the Insurance Manager FastAPI backend."


def get_app_dir() -> Path:
    """Return the installed application folder, both in source and frozen exe mode."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.lower() == "runtime":
            return exe_dir.parent
        return exe_dir
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
BACKEND_DIR = APP_DIR / "backend"
CONFIG_PATH = APP_DIR / "backend_service_config.json"
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "backend_service.log"


def setup_logging() -> logging.Logger:
    """Configure rotating file logs before the Windows service starts."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    return logging.getLogger(SERVICE_NAME)


logger = setup_logging()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    app = config.get("app")
    host = config.get("host")
    port = config.get("port")
    log_level = config.get("log_level", "info")

    if not BACKEND_DIR.exists() or not BACKEND_DIR.is_dir():
        raise FileNotFoundError(f"Missing backend folder: {BACKEND_DIR}")
    if not isinstance(app, str) or ":" not in app or not app.strip():
        raise ValueError('Config value "app" must look like "server:app".')
    if not isinstance(host, str) or not host.strip():
        raise ValueError('Config value "host" must be a non-empty string.')
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Config value "port" must be an integer from 1 to 65535.')
    if not isinstance(log_level, str) or not log_level.strip():
        raise ValueError('Config value "log_level" must be a non-empty string.')

    return {
        "app": app.strip(),
        "host": host.strip(),
        "port": port,
        "log_level": log_level.strip().lower(),
    }


class InsuranceBackendService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args: list[str]) -> None:
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server: uvicorn.Server | None = None
        self.server_thread: threading.Thread | None = None

    def SvcStop(self) -> None:
        logger.info("Stop requested for %s", SERVICE_DISPLAY_NAME)
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        if self.server is not None:
            self.server.should_exit = True

        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self) -> None:
        servicemanager.LogInfoMsg(f"{SERVICE_DISPLAY_NAME} is starting.")
        logger.info("%s is starting from %s", SERVICE_DISPLAY_NAME, APP_DIR)

        try:
            self._run_service()
        except Exception:
            logger.error("Fatal service error:\n%s", traceback.format_exc())
            servicemanager.LogErrorMsg(f"{SERVICE_DISPLAY_NAME} failed to start.")
            raise
        finally:
            logger.info("%s has stopped", SERVICE_DISPLAY_NAME)
            servicemanager.LogInfoMsg(f"{SERVICE_DISPLAY_NAME} has stopped.")

    def _run_service(self) -> None:
        config = load_config()

        # Make imports like "server:app" resolve exactly as they do in run_backend.bat.
        os.chdir(BACKEND_DIR)
        sys.path.insert(0, str(BACKEND_DIR))

        uvicorn_config = uvicorn.Config(
            app=config["app"],
            host=config["host"],
            port=config["port"],
            log_level=config["log_level"],
            reload=False,
            access_log=True,
        )
        self.server = uvicorn.Server(uvicorn_config)

        self.server_thread = threading.Thread(
            target=self.server.run,
            name="uvicorn-server",
            daemon=True,
        )
        self.server_thread.start()

        logger.info(
            "Uvicorn started for %s on http://%s:%s",
            config["app"],
            config["host"],
            config["port"],
        )

        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

        logger.info("Waiting for Uvicorn to shut down")
        if self.server is not None:
            self.server.should_exit = True
        if self.server_thread is not None:
            self.server_thread.join(timeout=30)
            if self.server_thread.is_alive():
                logger.warning("Uvicorn did not stop within 30 seconds.")


if __name__ == "__main__":
    if getattr(sys, "frozen", False) and len(sys.argv) == 1:
        # When the PyInstaller exe is launched by the Windows Service Control
        # Manager, there are no command-line arguments. In that case pywin32
        # must connect to the SCM dispatcher directly; HandleCommandLine is for
        # install/start/stop/debug commands run from a console.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(InsuranceBackendService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(InsuranceBackendService)
