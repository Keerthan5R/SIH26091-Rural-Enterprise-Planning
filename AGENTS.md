PROJECT: Karnataka adaptation of SetuBiz (academic major project)
GOAL: Adapt it to Karnataka and add Kannada (UI, report text, fonts, and voice input where possible).
The LLM explains; it never decides money. Financial logic stays deterministic.

RULES
1. Record every change in CHANGES.md (date, what, why).
2. Smallest change that works. Do not rewrite or delete working modules without asking me first.
3. The numeric-grounding validator must keep passing.
4. Every figure keeps its source, year and confidence. Mark Karnataka data as SAMPLE or REAL.
5. Windows PowerShell. No secrets in git; keys only in .env.
6. Small conventional commits. Run the tests before each commit, and stop and report any failure.
7. Never run git push. I push manually when I decide to.
8. Data downloads: never guess URLs; show me the official page and licence first; validate size and columns; cache responses; stop and tell me if a source needs registration or a manual step.

SAFETY RULES (highest priority)
1. Work ONLY inside C:\Users\Keerthan R\KEERTHAN\Projects\setubiz-karnataka-work. Never read from, write to or run commands in any other
   project folder, especially setubiz-karnataka and rural.
2. Never run: git reset --hard, git clean, git rebase, git push, or any command that deletes files or history. Ask me first.
3. Never delete a file or folder without asking me.
4. Never edit or delete an existing test to make it pass, and never lower the coverage requirement. If a test fails, report why.
5. Before each task, run `git status`. After each task, run the backend tests and the frontend build and show me the results.
   Only commit if everything passes.
6. Do not change finance, eligibility or documents logic unless I explicitly ask for it.
7. Never run npm in the repo root. Run npm only inside the frontend folder.
8. Never run opencode upgrade or install or update OpenCode itself.
