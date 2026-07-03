import base64
import logging
import os
import subprocess

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FONT_DIR = "/usr/share/fonts/truetype/custom_fonts"


class ResFont(models.Model):
    _name = "res.font"
    _description = "System Font"
    _order = "name"

    name = fields.Char(string="Font Name", required=True)
    filename = fields.Char(string="File Name", required=True)
    font_file = fields.Binary(
        string="Font File",
        attachment=False,
        required=True,
        help="Upload a TrueType or OpenType font file (.ttf, .otf).",
    )
    active = fields.Boolean(string="Active", default=True)
    installed = fields.Boolean(
        string="Installed on Filesystem",
        compute="_compute_installed",
        store=False,
    )

    _sql_constraints = [
        (
            "filename_unique",
            "UNIQUE(filename)",
            "The file name must be unique.",
        ),
    ]

    @api.depends("filename", "active")
    def _compute_installed(self):
        for record in self:
            if not record.filename or not record.active:
                record.installed = False
                continue
            filepath = os.path.join(FONT_DIR, record.filename)
            record.installed = os.path.isfile(filepath)

    @api.onchange("font_file", "filename")
    def _onchange_font_file(self):
        if self.font_file and self.filename:
            ext = os.path.splitext(self.filename)[1].lower()
            if ext not in (".ttf", ".otf"):
                return {
                    "warning": {
                        "title": _("Invalid font file"),
                        "message": _(
                            "Only TrueType (.ttf) and OpenType (.otf) files are supported."
                        ),
                    }
                }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._validate_font_file(vals)
        records = super().create(vals_list)
        for record in records:
            if record.active:
                record._install_font()
        return records

    def write(self, vals):
        if "filename" in vals:
            for record in self:
                if record.filename and record.filename != vals.get("filename"):
                    record._uninstall_font(record.filename)
        if "font_file" in vals:
            for vals_item in (vals if isinstance(vals, list) else [vals]):
                self._validate_font_file(vals_item)
        res = super().write(vals)
        needs_sync = any(k in vals for k in ("font_file", "filename", "active"))
        if needs_sync:
            for record in self:
                if record.active:
                    record._install_font()
                else:
                    record._uninstall_font()
        return res

    def unlink(self):
        for record in self:
            record._uninstall_font()
        return super().unlink()

    def action_install_font(self):
        for record in self:
            record._install_font()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_uninstall_font(self):
        for record in self:
            record._uninstall_font()
        return {"type": "ir.actions.client", "tag": "reload"}

    def _install_font(self):
        self.ensure_one()
        if not self.font_file or not self.filename:
            return
        self._ensure_font_dir()
        filepath = os.path.join(FONT_DIR, self.filename)
        try:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(self.font_file))
            self._refresh_font_cache()
            _logger.info("Font installed: %s", filepath)
        except PermissionError as exc:
            raise UserError(
                _(
                    "Permission denied writing to %(path)s. "
                    "Make sure the Odoo user can write to the fonts volume."
                )
                % {"path": FONT_DIR}
            ) from exc
        except OSError as exc:
            raise UserError(
                _(
                    "Could not install font %(filename)s: %(error)s"
                )
                % {"filename": self.filename, "error": exc}
            ) from exc

    def _uninstall_font(self, filename=None):
        self.ensure_one()
        fname = filename or self.filename
        if not fname:
            return
        filepath = os.path.join(FONT_DIR, fname)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
                self._refresh_font_cache()
                _logger.info("Font removed: %s", filepath)
            except OSError as exc:
                _logger.warning("Could not remove font %s: %s", filepath, exc)

    def _refresh_font_cache(self):
        try:
            subprocess.run(
                ["fc-cache", "-f", FONT_DIR],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            _logger.warning("fc-cache command not found. Font cache not refreshed.")

    @api.model
    def _ensure_font_dir(self):
        if not os.path.isdir(FONT_DIR):
            try:
                os.makedirs(FONT_DIR, exist_ok=True)
            except OSError as exc:
                raise UserError(
                    _(
                        "Could not create fonts directory %(path)s: %(error)s"
                    )
                    % {"path": FONT_DIR, "error": exc}
                ) from exc

    @api.model
    def _validate_font_file(self, vals):
        filename = vals.get("filename")
        if not filename:
            return
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".ttf", ".otf"):
            raise UserError(
                _(
                    "Unsupported font extension '%(ext)s'. "
                    "Only .ttf and .otf files are allowed."
                )
                % {"ext": ext}
            )
