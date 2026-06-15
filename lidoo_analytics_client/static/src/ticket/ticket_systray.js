/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

async function captureScreenshot() {
    // Intenta con preferCurrentTab (Chrome 96+) para evitar el selector de pestañas.
    // Si falla, reintenta sin él.
    let stream;
    try {
        stream = await navigator.mediaDevices.getDisplayMedia({
            video: true,
            preferCurrentTab: true,
        });
    } catch (firstErr) {
        // OverconstrainedError o NotAllowedError → reintentar sin preferCurrentTab
        try {
            stream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
            });
        } catch (secondErr) {
            throw new Error(`Screen capture denied: ${secondErr.message}`);
        }
    }

    const track = stream.getVideoTracks()[0];
    try {
        let bitmap;
        if (typeof ImageCapture !== "undefined") {
            // Ruta principal: ImageCapture.grabFrame()
            const imageCapture = new ImageCapture(track);
            bitmap = await imageCapture.grabFrame();
        } else {
            // Fallback: dibujar un frame del video a canvas
            bitmap = await new Promise((resolve, reject) => {
                const video = document.createElement("video");
                video.srcObject = stream;
                video.playsInline = true;
                video.muted = true;
                video.onloadedmetadata = async () => {
                    try {
                        await video.play();
                        const canvas = document.createElement("canvas");
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        const ctx = canvas.getContext("2d");
                        ctx.drawImage(video, 0, 0);
                        resolve(canvas);
                    } catch (e) {
                        reject(e);
                    }
                };
                video.onerror = reject;
            });
        }

        const canvas = document.createElement("canvas");
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(bitmap, 0, 0);
        const dataUrl = canvas.toDataURL("image/png");
        const base64 = dataUrl.split(",")[1];
        return {
            base64,
            filename: "screenshot.png",
            bytes: Math.round(base64.length * 3 / 4),
        };
    } finally {
        track.stop();
    }
}

export class TicketSystray extends Component {
    static template = "lidoo_analytics_client.TicketSystray";

    setup() {
        this.actionService = useService("action");
    }

    async openTicket() {
        const context = {};

        // 1. Capturar screenshot
        try {
            const shot = await captureScreenshot();
            context.default_screenshot = shot.base64;
            context.default_screenshot_filename = shot.filename;
            console.log("Screenshot captured:", shot.bytes, "bytes");
        } catch (e) {
            console.warn("Screenshot capture skipped:", e.message);
        }

        // 2. Ruta actual
        context.default_current_route = window.location.hash || window.location.pathname;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Report an Issue",
            res_model: "lidoo.analytics.ticket.wizard",
            views: [[false, "form"]],
            target: "new",
            context: context,
        });
    }
}

registry.category("systray").add("lidoo_analytics_client.TicketSystray", {
    Component: TicketSystray,
});
