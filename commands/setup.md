---
description: Guided setup for Confluence credentials. Creates a .env file with ATLASSIAN_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_TOKEN, then tests the connection.
argument-hint: (no arguments)
allowed-tools: Read, Write, Bash
---

Guide the user through setting up Confluence credentials step by step.

## Steps

1. Check if a `.env` file already exists in the current directory.
   - If it exists, read it and show which keys are present (mask the token value).
   - Ask: "Update existing credentials or keep them?"

2. If creating new or updating, collect the following interactively:

   **ATLASSIAN_URL**
   - Ask: "What is your Atlassian site URL? (e.g. https://your-org.atlassian.net)"
   - Validate: must start with `https://` and end with `.atlassian.net`

   **ATLASSIAN_EMAIL**
   - Ask: "What email address do you use to log in to Confluence?"

   **ATLASSIAN_API_TOKEN**
   - Ask: "Paste your Atlassian API token. Don't have one? Generate one at https://id.atlassian.com/manage-profile/security/api-tokens"
   - Do not display the token back to the user after they paste it.

3. Write the `.env` file:
   ```
   ATLASSIAN_URL=https://your-org.atlassian.net
   ATLASSIAN_EMAIL=you@example.com
   ATLASSIAN_API_TOKEN=your-token-here
   ```

4. Remind the user to add `.env` to their `.gitignore`:
   ```
   echo ".env" >> .gitignore
   ```
   Offer to do this automatically.

5. Test the connection by calling the Confluence spaces API:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --test-auth
   ```

6. Report result:
   - Success: "Connected! Found X spaces. You're ready to publish."
   - Failure: Show the error (401 = bad token, 403 = wrong permissions, network error = check URL) and guide the user to fix it.
