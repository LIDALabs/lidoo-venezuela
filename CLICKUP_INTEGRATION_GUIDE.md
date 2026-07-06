# Guía de Integración: ClickUp para Tickets de Incidencias

## 1. Objetivo
Reemplazar (o complementar) el envío a Discord por la creación de tareas en ClickUp con toda la información del ticket.

---

## 2. Conceptos de ClickUp API

### 2.1 Autenticación
ClickUp usa **Personal API Token** (más simple para server-to-server que OAuth2).

- Ir a ClickUp → Settings → Apps → Generate API Token
- El token se manda en header: `Authorization: pk_SU_TOKEN_AQUI`

### 2.2 Estructura de ClickUp
```
Team (Workspace)
└── Space
    └── Folder (optional)
        └── List
            └── Task  ← Aquí creamos los tickets
```

**IDs necesarios:**
- `team_id`: ID del workspace (se obtiene de `GET /v2/team`)
- `list_id`: ID de la lista donde caen los tickets (se obtiene navegando spaces/folders/lists)

### 2.3 Endpoint para crear tarea
```
POST https://api.clickup.com/api/v2/list/{list_id}/task
```

**Headers:**
```
Authorization: pk_SU_TOKEN
Content-Type: application/json
```

**Payload mínimo:**
```json
{
  "name": "Incidencia #42 - DB: mi_empresa",
  "description": "**Usuario:** Admin\n**Ruta:** /web#action=...\n**DB:** mi_empresa\n\n**Descripción:**...",
  "status": "open",
  "priority": 3,
  "tags": ["odoo-ticket", "bug"],
  "custom_fields": [
    {
      "id": "custom_field_id",
      "value": "valor"
    }
  ]
}
```

**Priority levels:**
- 1 = Urgent (red)
- 2 = High (yellow)
- 3 = Normal (blue)
- 4 = Low (grey)

### 2.4 Adjuntar screenshot
ClickUp NO acepta base64 en el POST de tarea. El attachment va por **endpoint separado**:

```
POST https://api.clickup.com/api/v2/task/{task_id}/attachment
```

**Headers:**
```
Authorization: pk_SU_TOKEN
Content-Type: multipart/form-data
```

**Body (multipart):**
- `attachment`: archivo binario (la imagen)

**Flujo completo:**
1. Crear tarea (POST /list/{id}/task)
2. Obtener `task_id` de la respuesta
3. Subir screenshot (POST /task/{task_id}/attachment)

### 2.5 Custom Fields útiles para tickets
Se pueden crear en ClickUp y mapear desde Odoo:

| ClickUp Custom Field | Tipo | Valor desde Odoo |
|---|---|---|
| Base de Datos | Text | `db_name` |
| Usuario | Text | `user_id.name` |
| Ruta | Text | `current_route` |
| Odoo Ticket ID | Number | `id` del ticket |
| Tiene Screenshot | Checkbox | `has_screenshot` |

**Para usar custom fields necesitás:**
1. Crear los custom fields en ClickUp (en la lista destino)
2. Obtener sus IDs con `GET /v2/list/{list_id}/field`
3. Incluirlos en el payload de creación de tarea

---

## 3. Implementación en Odoo

### 3.1 Configuración (res.config.settings)
Agregar campos en Ajustes → General Settings → Analytics:

```python
clickup_api_token = fields.Char(string="ClickUp API Token")
clickup_list_id = fields.Char(string="ClickUp List ID")
clickup_team_id = fields.Char(string="ClickUp Team ID")
```

Vista XML para mostrar en Ajustes.

### 3.2 Nuevos campos en lidoo.analytics.ticket
```python
clickup_task_id = fields.Char(string="ClickUp Task ID", readonly=True)
clickup_task_url = fields.Char(string="ClickUp URL", readonly=True)
```

### 3.3 Método action_send_clickup()
En `analytics_ticket.py`, crear nuevo método:

```python
def action_send_clickup(self):
    self.ensure_one()
    icp = self.env["ir.config_parameter"].sudo()
    token = icp.get_param("lidoo_analytics.clickup_api_token", "")
    list_id = icp.get_param("lidoo_analytics.clickup_list_id", "")
    
    if not token or not list_id:
        _logger.info("No ClickUp config, ticket %s saved as draft", self.id)
        self.write({"state": "draft"})
        return
    
    # 1. Crear tarea
    task_id = self._clickup_create_task(token, list_id)
    if not task_id:
        return
    
    # 2. Subir screenshot si existe
    if self.screenshot:
        self._clickup_upload_attachment(token, task_id)
    
    # 3. Guardar referencia
    self.write({
        "state": "sent",
        "clickup_task_id": task_id,
        "clickup_task_url": f"https://app.clickup.com/t/{task_id}",
    })
```

### 3.4 Crear tarea (urllib)
```python
def _clickup_create_task(self, token, list_id):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    
    payload = {
        "name": f"Incidencia #{self.id} - DB: {self.db_name or 'N/A'}",
        "description": self._build_clickup_description(),
        "status": "open",
        "priority": 3,
        "tags": ["odoo-ticket"],
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (OdooBot/1.0)",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("id")
    except urllib.error.HTTPError as e:
        _logger.error("ClickUp create task error: %s %s", e.code, e.read().decode()[:500])
        self.write({"state": "failed", "error_message": f"ClickUp HTTP {e.code}"})
        return None
```

### 3.5 Subir attachment (multipart)
```python
def _clickup_upload_attachment(self, token, task_id):
    url = f"https://api.clickup.com/api/v2/task/{task_id}/attachment"
    
    raw = self.screenshot or ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    
    if not raw:
        return
    
    image_bytes = base64.b64decode(raw)
    filename = self.screenshot_filename or f"ticket_{self.id}.png"
    
    # Multipart
    boundary = "----ClickUpBoundary"
    body_lines = []
    body_lines.append(f"--{boundary}".encode())
    body_lines.append(f'Content-Disposition: form-data; name="attachment"; filename="{filename}"'.encode())
    body_lines.append(b"Content-Type: image/png")
    body_lines.append(b"")
    body_lines.append(image_bytes)
    body_lines.append(f"--{boundary}--".encode())
    data = b"\r\n".join(body_lines)
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": token,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0 (OdooBot/1.0)",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            _logger.info("ClickUp attachment uploaded for task %s", task_id)
    except urllib.error.HTTPError as e:
        _logger.warning("ClickUp attachment error: %s", e.code)
```

### 3.6 Construir descripción
```python
def _build_clickup_description(self):
    lines = [
        f"**Usuario:** {self.user_id.name or 'N/A'}",
        f"**Base de Datos/Empresa:** {self.db_name or 'N/A'}",
        f"**Ruta:** {self.current_route or 'N/A'}",
        "",
        "**Descripción:**",
        self.description or "Sin descripción",
    ]
    
    if self.server_logs:
        lines.extend(["", "**Logs del servidor:**", "```", self.server_logs[:2000], "```"])
    
    return "\n".join(lines)
```

---

## 4. Webhooks de ClickUp (opcional)

ClickUp puede avisar a Odoo cuando alguien comenta o cierra la tarea.

### 4.1 Crear webhook en ClickUp
```
POST https://api.clickup.com/api/v2/team/{team_id}/webhook
```

**Payload:**
```json
{
  "endpoint": "https://tu-odoo.com/lidoo_analytics/webhook/clickup",
  "events": ["taskCommentPosted", "taskStatusUpdated"],
  "space_id": "space_id_aqui"
}
```

### 4.2 Recibir webhook en Odoo
Crear controller en `controllers/`:

```python
from odoo import http

class ClickUpWebhook(http.Controller):
    @http.route("/lidoo_analytics/webhook/clickup", type="json", auth="public", csrf=False)
    def clickup_webhook(self, **kw):
        # Verificar firma del webhook (opcional)
        # Actualizar estado del ticket en Odoo
        # task_id = kw.get("task_id")
        # ticket = env["lidoo.analytics.ticket"].search([("clickup_task_id", "=", task_id)])
        return {"status": "ok"}
```

---

## 5. Manejo de errores

| Error | Causa | Solución |
|---|---|---|
| 401 | Token inválido | Notificar: "Configurá el token de ClickUp en Ajustes" |
| 404 | List ID inválido | Notificar: "Verificá el List ID de ClickUp" |
| 429 | Rate limit | Reintentar con backoff (esperar 60s) |
| Timeout | Red lenta | Guardar como draft, reintentar después |

---

## 6. Plan de migración desde Discord

### Opción A: Reemplazar Discord (simple)
1. Cambiar `action_send()` para que llame a `action_send_clickup()`
2. Eliminar código de Discord
3. Agregar settings de ClickUp

### Opción B: Mantener ambos (flexible)
1. En `action_submit()` del wizard, preguntar o enviar a ambos
2. O enviar a Discord como backup si ClickUp falla
3. Settings separados para cada uno

---

## 7. Datos que necesitás para arrancar

Para implementar esto necesitás:

1. **API Token de ClickUp** → Generar en Settings → Apps
2. **List ID** → ID de la lista donde caen los tickets (se ve en la URL de ClickUp)
3. **Team ID** → Opcional, para webhooks (se obtiene de `GET /v2/team`)

### Cómo obtener el List ID:
1. Ir a ClickUp → Abrir la lista destino
2. Ver la URL: `https://app.clickup.com/123456/v/li/987654321`
3. El List ID es el número después de `/li/` → `987654321`

---

## 8. Resumen de archivos a tocar

| Archivo | Cambio |
|---|---|
| `models/analytics_ticket.py` | Nuevo método `action_send_clickup()` + helpers |
| `models/ticket_wizard.py` | Llamar a `action_send_clickup()` en vez de Discord |
| `models/res_config_settings.py` | Campos `clickup_api_token`, `clickup_list_id` |
| `views/res_config_settings_views.xml` | UI para configurar ClickUp |
| `views/analytics_ticket_views.xml` | Mostrar `clickup_task_url` |
| `__manifest__.py` | Agregar `python: ["requests"]` o seguir con urllib |

---

## Próximo paso

¿Querés que implemente esto en código? Necesito que me pases:
- **API Token** de ClickUp
- **List ID** donde querés que caigan los tickets
- ¿Reemplazamos Discord o mantenemos ambos?

Con eso armo el código y lo commiteamos.
