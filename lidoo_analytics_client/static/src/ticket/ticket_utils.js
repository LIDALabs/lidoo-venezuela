/** @odoo-module **/

/**
 * Capture the current screen and return a PNG as base64.
 * Throws "SCREENSHOT_CANCELLED" if the user denies/dismisses the picker.
 */
export async function captureScreenshot() {
    // Intenta con preferCurrentTab (Chrome 96+) para evitar el selector de pestañas.
    // Si el usuario cancela, no reintentamos.
    let stream;
    try {
        stream = await navigator.mediaDevices.getDisplayMedia({
            video: true,
            preferCurrentTab: true,
        });
    } catch (firstErr) {
        // El usuario canceló el diálogo de compartir pantalla
        if (firstErr.name === "NotAllowedError" || firstErr.name === "AbortError") {
            throw new Error("SCREENSHOT_CANCELLED");
        }
        // Otros errores: reintentar sin preferCurrentTab
        try {
            stream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
            });
        } catch (secondErr) {
            if (secondErr.name === "NotAllowedError" || secondErr.name === "AbortError") {
                throw new Error("SCREENSHOT_CANCELLED");
            }
            throw new Error(`Screen capture failed: ${secondErr.message}`);
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

/**
 * Build the context used by the ticket wizard.
 */
export async function buildTicketContext() {
    const context = {};
    try {
        const shot = await captureScreenshot();
        context.default_screenshot = shot.base64;
        context.default_screenshot_filename = shot.filename;
        console.log("Screenshot captured:", shot.bytes, "bytes");
    } catch (e) {
        if (e.message === "SCREENSHOT_CANCELLED") {
            throw e;
        }
        console.warn("Screenshot capture failed:", e.message);
        throw e;
    }
    context.default_current_route = window.location.hash || window.location.pathname;
    return context;
}

/**
 * Open the ticket wizard with the given action service.
 */
export async function openTicketWizard(actionService) {
    let context;
    try {
        context = await buildTicketContext();
    } catch (e) {
        if (e.message === "SCREENSHOT_CANCELLED") {
            console.log("User cancelled screenshot capture; wizard will not open.");
            return;
        }
        console.warn("Could not open ticket wizard:", e.message);
        return;
    }

    actionService.doAction({
        type: "ir.actions.act_window",
        name: "Reportar incidencia",
        res_model: "lidoo.analytics.ticket.wizard",
        views: [[false, "form"]],
        target: "new",
        context: context,
    });
}
