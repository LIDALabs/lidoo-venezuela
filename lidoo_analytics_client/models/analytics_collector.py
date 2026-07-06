import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
import time

import requests

import odoo
from odoo import api, models

_logger = logging.getLogger(__name__)

# Server start time captured at module load
_server_start_time = time.time()


class LidooAnalyticsCollector(models.AbstractModel):
    _name = "lidoo.analytics.collector"
    _description = "Analytics Data Collector"

    @api.model
    def _get_git_commit_info(self, repo_path):
        """
        Obtiene hash + mensaje + fecha del último commit de un repo local.
        Usa git si está disponible, fallback a lectura directa de .git.
        Returns: string like "abc1234 - Mensaje | 2025-06-10" o "N/A"
        """
        git_dir = os.path.join(repo_path, '.git')
        if not os.path.isdir(git_dir):
            return "N/A"

        # Plan A: git instalado (via Dockerfile) → datos completos
        try:
            output = subprocess.check_output(
                ['git', '-C', repo_path,
                 '-c', 'safe.directory=*',
                 'log', '-1', '--format=%h - %s | %ai'],
                stderr=subprocess.STDOUT, timeout=10
            ).decode('utf-8').strip()
            if output:
                return output
        except Exception:
            pass

        # Plan B: lectura directa de .git → solo hash
        try:
            with open(os.path.join(git_dir, 'HEAD')) as f:
                ref = f.read().strip()
            if ref.startswith('ref: '):
                ref_path = os.path.join(git_dir, ref[5:])
                with open(ref_path) as f:
                    full_hash = f.read().strip()
            else:
                full_hash = ref
            return full_hash[:7]
        except Exception:
            return "N/A"

    @api.model
    def _collect_data(self):
        """Gather all Odoo-level analytics data points."""
        ICP = self.env["ir.config_parameter"].sudo()
        Module = self.env["ir.module.module"].sudo()
        Users = self.env["res.users"].sudo()

        # Database UUID
        db_uuid = ICP.get_param("database.uuid", default="")

        # Odoo version
        odoo_version = odoo.release.version

        # Installed modules
        installed_modules = Module.search([("state", "=", "installed")])

        # Custom modules (author is not Odoo SA)
        custom_modules = installed_modules.filtered(
            lambda m: "Odoo" not in (m.author or "")
        )
        custom_module_names = set(custom_modules.mapped('name'))

        modules_list = [
            {"name": m.name, "version": m.installed_version or "",
             "is_custom": m.name in custom_module_names,
             "author": m.author or ""}
            for m in installed_modules
        ]

        # Uptime
        uptime_seconds = int(time.time() - _server_start_time)

        # Database size
        db_size = self._get_database_size()

        # Active users
        active_users = Users.search_count([("active", "=", True), ("share", "=", False)])

        # Last login
        last_login_user = Users.search(
            [("login_date", "!=", False)], order="login_date desc", limit=1
        )
        last_login = (
            last_login_user.login_date.isoformat() if last_login_user.login_date else ""
        )

        # OS & Python info
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        python_version = sys.version.split()[0]

        # Cron job status
        Cron = self.env["ir.cron"].sudo()
        active_crons = Cron.search_count([("active", "=", True)])

        data = {
            "lidoo_commit_hash": self._get_git_commit_info("/mnt/l10n_ve_fiscal"),
            "database_uuid": db_uuid,
            "odoo_version": odoo_version,
            "installed_modules": modules_list,
            "custom_module_count": len(custom_modules),
            "uptime_seconds": uptime_seconds,
            "database_size": db_size,
            "active_user_count": active_users,
            "last_login": last_login,
            "os_info": os_info,
            "python_version": python_version,
            "active_cron_count": active_crons,
        }

        return data

    @api.model
    def _collect_hardware_data(self):
        """Collect CPU and memory metrics. Requires psutil."""
        try:
            import psutil

            return {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
            }
        except ImportError:
            _logger.warning(
                "psutil not installed — hardware metrics collection skipped."
            )
            return {"cpu_usage": 0.0, "memory_usage": 0.0}

    @api.model
    def _get_database_size(self):
        """Query the total size of the current database in bytes."""
        try:
            self.env.cr.execute(
                "SELECT pg_database_size(current_database())"
            )
            result = self.env.cr.fetchone()
            return result[0] if result else 0
        except Exception:
            _logger.warning("Could not determine database size.", exc_info=True)
            return 0

    @api.model
    def _send_report(self):
        """Build payload, send to the partner endpoint, and log the result."""
        ICP = self.env["ir.config_parameter"].sudo()
        endpoint_url = ICP.get_param("lidoo_analytics.endpoint_url", default="")
        api_key = ICP.get_param("lidoo_analytics.api_key", default="")
        collect_hw = ICP.get_param("lidoo_analytics.collect_hw", default="False")

        if not endpoint_url or not api_key:
            _logger.warning(
                "Analytics not sent: endpoint URL or API key not configured."
            )
            return False

        # Collect data
        data = self._collect_data()

        # Optionally collect hardware data
        if collect_hw and collect_hw.lower() not in ("false", "0", ""):
            hw_data = self._collect_hardware_data()
            data.update(hw_data)

        # Add the API key to the payload
        data["api_key"] = api_key

        # Build JSON payload
        payload_json = json.dumps(data, default=str, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        # Send
        Log = self.env["lidoo.analytics.log"].sudo()
        try:
            response = requests.post(
                endpoint_url,
                data=payload_json,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            if response.status_code == 200:
                Log.create(
                    {
                        "status": "success",
                        "payload_hash": payload_hash,
                    }
                )
                _logger.info("Analytics report sent successfully.")
                return True
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                Log.create(
                    {
                        "status": "error",
                        "payload_hash": payload_hash,
                        "error_message": error_msg,
                    }
                )
                _logger.error("Analytics report failed: %s", error_msg)
                return False

        except Exception as e:
            Log.create(
                {
                    "status": "error",
                    "payload_hash": payload_hash,
                    "error_message": str(e),
                }
            )
            _logger.exception("Error sending analytics report.")
            return False

    @api.model
    def _cron_send_report(self):
        """Entry point for the scheduled action. Checks if enabled before sending."""
        ICP = self.env["ir.config_parameter"].sudo()
        enabled = ICP.get_param("lidoo_analytics.enabled", default="False")
        if enabled and enabled.lower() not in ("false", "0", ""):
            self._send_report()
        else:
            _logger.debug("Analytics reporting is disabled — skipping.")
