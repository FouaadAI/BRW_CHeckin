/**
 * Public frontend configuration for the BRW Check-in app.
 *
 * This file is safe to commit to Git because it only contains the public
 * Cloudflare Worker URL. All secrets live server-side in the Worker or in
 * GitHub Repository Secrets and never appear here.
 */

window.PROXY_URL = 'https://brw-checkin-proxy.brainerpro66.workers.dev';
