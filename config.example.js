/**
 * Configuration template for the BRW Check-in frontend.
 *
 * IMPORTANT: Copy this file to `config.js` in the repository root and
 * replace the placeholder values with the real secrets. The real `config.js`
 * must be created locally and is listed in `.gitignore`. It must NEVER be
 * committed to Git.
 *
 * Required global variables:
 * - window.APP_PIN: Numeric PIN employees enter to unlock the form.
 * - window.GH_PAT:  GitHub Personal Access Token used to trigger
 *                   repository_dispatch events via the GitHub API. Prefer a
 *                   fine-grained token with the smallest possible permission
 *                   on this repository (e.g. Actions: write) and rotate it if
 *                   exposed.
 */

// eslint-disable-next-line no-unused-vars
window.APP_PIN = '000000'; // Replace with the real PIN (must match GitHub Secret APP_PIN)

// eslint-disable-next-line no-unused-vars
window.GH_PAT = 'ghp_xxxxxxxxxxxxxxxxxxxx'; // Replace with the real GitHub PAT (must match GitHub Secret GH_PAT)
