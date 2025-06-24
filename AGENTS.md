# AGENTS.md — Coding Agent Guidelines for Gaja

This document outlines the required practices, constraints, and expectations for all agents or tools responsible for generating, modifying, or refactoring code within the Gaja project. This applies to integrations such as GitHub Copilot, Cursor, Codex, or any future coding-capable AI.

> ⚠️ All contributions must respect the architectural philosophy of Gaja: **modularity**, **asynchronicity**, and **testability**.

---

## 🔍 Before You Start

Check if there are any files to commit. Commit them, then proceed.

### 🔎 Research First

Before modifying or generating any code:

- **Understand the full architecture** of Gaja (both client and server).
- Review how existing agents, APIs, and modules interact.
- Study naming conventions, folder structure, and key async workflows.
- Avoid duplicating existing logic — reuse or extend existing utilities where possible.

---

## ✅ Code Requirements

### 1. **Asynchronous Code Only**

- All code must use `async/await`. Blocking operations (`time.sleep`, `requests`, synchronous file I/O) are **strictly forbidden**.
- Use `aiohttp`, `asyncio`, `asyncpg`, or similar async-compatible libraries only.
- If wrapping sync logic is absolutely necessary, use `run_in_executor` and document it clearly.

### 2. **Test Coverage Required**

- Every new feature or behavior must include one or more **pytest unit tests**.
- Place all tests in the appropriate `tests/` directory and use clear, descriptive names.
- If your agent performs external I/O (e.g. generates files, calls external tools), mock them.
- Test both expected behavior and edge cases (e.g. missing config, invalid input).

### 3. **End-to-End Verification**

Before submitting a PR or finishing your task:

- Run **`pytest`** on the full project.
- Start both the **server** and **client** of Gaja locally.
- Interact with your feature and verify it behaves correctly from user entrypoint to output.

---

## 🧼 Code Quality Guidelines

- Use clear and expressive naming (`get_user_preferences`, not `getprefs`).
- Constants must be **named** (e.g. `MAX_ATTEMPTS = 3`) — no magic numbers.
- All functions must have **docstrings** describing purpose, arguments, and return types.
- If something is not fully implemented, use `TODO` or `FIXME` with an explanation of why and what is missing.
- Use **type hints** consistently across all functions.

---

## 🚫 Forbidden Practices

- ❌ `time.sleep()` or any blocking I/O
- ❌ Use of global state or side effects outside the agent’s own scope
- ❌ Direct mutation of shared memory/state without proper logging and interface
- ❌ Internet API calls unless explicitly permitted
- ❌ Commits without explanation (see Commit section below)

---

## 🗃️ Memory & State Modifications

If your agent changes Gaja’s internal memory (e.g., user profile, intent history, conversation state):

- Always use the **defined memory interface** – never write directly to `.json`, `.sqlite`, or `.txt` unless approved.
- Log all changes explicitly if your function is long-running or affects user experience significantly.
- Keep in mind **Gaja must remain explainable** – if the agent performs autonomous actions, log why.

---

## 🧪 Testing Philosophy

Write your code assuming someone else will have to debug it in 6 months:

- Break functionality into small, pure, testable functions.
- Use mocking for anything external or unpredictable.
- If the feature is too complex to test via unit tests, provide a `feature_name_test_manual.md` file with step-by-step test instructions.

---

## 🔧 Optional but Recommended

- Use `black`, `ruff`, or `isort` to keep formatting consistent.
- Structure async workflows as state machines or clearly defined flows when possible.
- Document non-obvious logic inline — Gaja prioritizes maintainability over cleverness.

---

## 📝 Commit & PR Guidelines

- Write clear and actionable commit messages (e.g., `feat(weather): add async forecast fetch`, `fix(core): handle null input in intent parser`).
- Every PR must include:
  - Summary of the change
  - What was tested
  - Any known limitations
- If your PR affects UX or assistant behavior, please include a short demo or log trace.

---

## 🧠 Final Notes

Your agent is part of a system designed for **trust**, **speed**, and **local autonomy**. Code that breaks this trust—even subtly—will be flagged and removed.

Thank you for keeping Gaja robust, elegant, and fun to work with. 🚀
