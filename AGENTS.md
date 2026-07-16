# AGENTS.md

## Repository purpose

This repository stores project code, reusable technical documents, and explicit decisions produced in conversations with ChatGPT/Codex.

## Default behavior

1. Put each independent project under `projects/<project-name>/`.
2. Put cross-project documentation under `docs/`.
3. Record important conversation decisions under `docs/conversations/`.
4. Do not treat work in progress as final output.
5. Never claim that code was built, tested, committed, or deployed unless that action actually succeeded.
6. Prefer a small runnable implementation over a large promotional design document.
7. Keep secrets, credentials, private exports, and local configuration out of Git.

## Current priority

The active project is `projects/sleep-sense`, an Android application that detects a phone posture consistent with a user lying down and exposes state changes for automation.
