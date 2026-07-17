from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from portable_assistant.config import ProfileConfig, ProviderConfig, load_config
from portable_assistant.memory import MemoryStore
from portable_assistant.providers import ChatMessage, ProviderError, ProviderResult
from portable_assistant.router import ProviderRouter
from portable_assistant.skills import discover_skills, load_skills


class ConfigTests(unittest.TestCase):
    def test_expands_environment_model_and_resolves_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "default_profile": "main",
                        "identity_file": "identity.md",
                        "memory_path": "data/memory.jsonl",
                        "skills_path": "skills",
                        "profiles": {
                            "main": {
                                "providers": [
                                    {
                                        "name": "openai",
                                        "type": "openai",
                                        "model": "${TEST_MODEL}",
                                        "api_key_env": "TEST_KEY",
                                        "base_url": "https://example.test/v1",
                                    }
                                ]
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"TEST_MODEL": "model-a"}, clear=False):
                config = load_config(config_path)

            self.assertEqual(config.profile().providers[0].model, "model-a")
            self.assertEqual(config.memory_path, root / "data/memory.jsonl")


class MemoryTests(unittest.TestCase):
    def test_draft_memory_is_not_in_confirmed_context_until_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.jsonl")
            item = store.add("A process draft", title="Draft")
            self.assertEqual(store.recent_confirmed(10), [])

            confirmed = store.set_status(item.id, "confirmed")
            self.assertEqual(confirmed.status, "confirmed")
            self.assertEqual(store.recent_confirmed(10)[0].content, "A process draft")

    def test_export_contains_no_hidden_reasoning_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.jsonl")
            store.add("Confirmed note", title="Note", status="confirmed")
            exported = store.export_markdown("confirmed")
            self.assertIn("Confirmed note", exported)
            self.assertIn("not hidden model reasoning", exported)


class RouterTests(unittest.TestCase):
    def test_falls_back_after_provider_error(self) -> None:
        first = ProviderConfig(
            name="first",
            type="openai",
            model="model-1",
            api_key_env="FIRST_KEY",
            base_url="https://first.test",
            priority=10,
        )
        second = ProviderConfig(
            name="second",
            type="anthropic",
            model="model-2",
            api_key_env="SECOND_KEY",
            base_url="https://second.test",
            priority=20,
        )
        profile = ProfileConfig(name="test", providers=(first, second))

        class FakeProvider:
            def __init__(self, config: ProviderConfig) -> None:
                self.config = config

            def generate(self, messages, timeout_seconds):
                if self.config.name == "first":
                    raise ProviderError("simulated outage")
                return ProviderResult(
                    provider=self.config.name,
                    model=self.config.model,
                    text="ok",
                    latency_ms=1,
                )

        with patch.dict(
            os.environ,
            {"FIRST_KEY": "secret", "SECOND_KEY": "secret"},
            clear=False,
        ):
            result, failures = ProviderRouter(
                profile, provider_factory=FakeProvider
            ).generate([ChatMessage(role="user", content="hello")])

        self.assertEqual(result.provider, "second")
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].provider, "first")


class SkillTests(unittest.TestCase):
    def test_discovers_and_loads_named_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_dir = root / "review"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "# Review skill\n\nCheck evidence.", encoding="utf-8"
            )
            discovered = discover_skills(root)
            self.assertEqual(discovered[0].name, "review")
            self.assertEqual(load_skills(root, ["review"])[0].title, "Review skill")


if __name__ == "__main__":
    unittest.main()
