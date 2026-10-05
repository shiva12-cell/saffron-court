# Agent Standing Rules — Saffron Court Management App

1. **Read Documents First:** Read documents before any task and follow them exactly.
2. **Local Data Only:** Only use data which is present in the folder. Never assume or provide any data from the internet.
3. **Read-Only Data & Docs:** Never edit, move, or delete anything inside `data` or `docs`. Read only.
4. **Streamlit Platform Development:**
   - Build a Streamlit platform inside the `app` folder from the given data.
   - **App Name:** `Saffron Court Management App`
   - **Modules:** Menu and Orders, Kitchen, Inventory, Reservation, and Staff.
   - **Data Source:** Pull data directly from the dataset files in `data/` with zero edits or modifications to dataset files.
   - **User-Facing Error Handling:** No screen should show JSON code, stack trace, or technical errors. Errors must be displayed as one plain sentence or a suggestion.
   - **Footer:** Every page must end with `Saffron Court Internal Management App`.
   - **Extension & Plan Approval:** When later prompts extend the platform, never remove or break what an earlier prompt built. Extend it, present the plan, wait for approval, then create the file.
