/**
 * Configuration template for the BRW Check-in frontend.
 *
 * IMPORTANT: Copy this file to `config.js` in the repository root and
 * set the public `PROXY_URL` value. The real `config.js` is listed in
 * `.gitignore` and must NEVER be committed to Git.
 *
 * All secrets (PIN, GitHub PAT, Google credentials, Telegram tokens) are
 * stored server-side in the Cloudflare Worker environment and GitHub
 * Repository Secrets. They MUST NOT appear in this file.
 */

// eslint-disable-next-line no-unused-vars
window.PROXY_URL = 'https://brw-checkin-proxy.brainerpro66.workers.dev'; // Replace with your Cloudflare Worker URL
