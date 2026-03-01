"""Tests for the multi-provider LLM abstraction layer.

All tests use unittest.mock to avoid real API calls.
Run with:  python -m pytest backend/tests/test_llm_abstraction.py -v
"""

import json
import sys
import os
import unittest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock, patch

# Allow imports from the backend root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.llm_types import TokenUsage, LLMResponse
from shared.models import TokenUsageRecord, MatchResult


# ── TokenUsage & LLMResponse ──────────────────────────────────────────────────

class TestTokenUsage(unittest.TestCase):
    def test_basic_construction(self):
        u = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        self.assertEqual(u.prompt_tokens, 100)
        self.assertEqual(u.completion_tokens, 50)
        self.assertEqual(u.total_tokens, 150)
        self.assertIsNone(u.remaining_tokens)

    def test_with_remaining(self):
        u = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150,
                       remaining_tokens=127_850)
        self.assertEqual(u.remaining_tokens, 127_850)

    def test_to_dict(self):
        u = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        d = u.to_dict()
        self.assertEqual(d["total_tokens"], 15)
        self.assertIsNone(d["remaining_tokens"])


class TestLLMResponse(unittest.TestCase):
    def test_to_dict(self):
        u = TokenUsage(prompt_tokens=50, completion_tokens=20, total_tokens=70)
        r = LLMResponse(text='{"foo": "bar"}', usage=u, provider="openai",
                        model="gpt-4o-mini", request_id="req-abc")
        d = r.to_dict()
        self.assertEqual(d["provider"], "openai")
        self.assertEqual(d["model"], "gpt-4o-mini")
        self.assertEqual(d["request_id"], "req-abc")
        self.assertEqual(d["usage"]["total_tokens"], 70)


# ── TokenUsageRecord ──────────────────────────────────────────────────────────

class TestTokenUsageRecord(unittest.TestCase):
    def test_defaults(self):
        rec = TokenUsageRecord(provider="gemini", model="gemini-2.0-flash",
                               operation="summarize_resume", total_tokens=200)
        self.assertTrue(len(rec.record_id) > 0)
        self.assertTrue(len(rec.timestamp) > 0)
        self.assertIsNone(rec.remaining_tokens)

    def test_to_dict(self):
        rec = TokenUsageRecord(provider="openai", model="gpt-4o-mini",
                               operation="score_resume_vs_jd",
                               prompt_tokens=100, completion_tokens=50, total_tokens=150,
                               remaining_tokens=127_850)
        d = rec.to_dict()
        self.assertEqual(d["provider"], "openai")
        self.assertEqual(d["total_tokens"], 150)
        self.assertEqual(d["remaining_tokens"], 127_850)


# ── GeminiProvider ────────────────────────────────────────────────────────────

class TestGeminiProvider(unittest.TestCase):
    def _make_provider_with_mock_client(self):
        """Create a GeminiProvider instance without calling __init__."""
        # Insert a minimal google.generativeai stub so the module can be imported
        if "google.generativeai" not in sys.modules:
            stub = MagicMock()
            sys.modules.setdefault("google", MagicMock())
            sys.modules["google.generativeai"] = stub

        from shared.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model_name = "gemini-2.0-flash"
        mock_client = MagicMock()
        provider._client = mock_client
        return provider, mock_client

    def _make_mock_response(self, text: str, prompt_tokens: int = 80,
                             completion_tokens: int = 40):
        resp = MagicMock()
        resp.text = text
        meta = MagicMock()
        # Assign concrete integer values so getattr() returns ints, not Mocks
        type(meta).prompt_token_count = property(lambda self: prompt_tokens)
        type(meta).candidates_token_count = property(lambda self: completion_tokens)
        type(meta).total_token_count = property(
            lambda self: prompt_tokens + completion_tokens
        )
        resp.usage_metadata = meta
        return resp

    def test_generate_returns_llm_response(self):
        provider, mock_client = self._make_provider_with_mock_client()
        mock_client.generate_content.return_value = self._make_mock_response(
            '{"ok": true}', prompt_tokens=80, completion_tokens=40
        )

        result = provider.generate("test prompt")

        self.assertIsInstance(result, LLMResponse)
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.model, "gemini-2.0-flash")
        self.assertEqual(result.usage.prompt_tokens, 80)
        self.assertEqual(result.usage.completion_tokens, 40)
        self.assertEqual(result.usage.total_tokens, 120)
        self.assertIsNone(result.usage.remaining_tokens)

    def test_usage_metadata_missing(self):
        provider, mock_client = self._make_provider_with_mock_client()
        resp = MagicMock()
        resp.text = "hello"
        resp.usage_metadata = None
        mock_client.generate_content.return_value = resp

        result = provider.generate("p")
        self.assertIsInstance(result, LLMResponse)
        self.assertIsNone(result.usage.remaining_tokens)


# ── OpenAIProvider ────────────────────────────────────────────────────────────

class TestOpenAIProvider(unittest.TestCase):
    def _mock_openai_response(self, text: str, prompt_tokens=100, completion_tokens=60):
        resp = MagicMock()
        resp.id = "chatcmpl-abc"
        choice = MagicMock()
        choice.message.content = text
        resp.choices = [choice]
        resp.usage.prompt_tokens = prompt_tokens
        resp.usage.completion_tokens = completion_tokens
        resp.usage.total_tokens = prompt_tokens + completion_tokens
        return resp

    @patch("shared.providers.openai_provider.OpenAIProvider.__init__", lambda self, **kwargs: None)
    def test_generate_returns_llm_response(self):
        from shared.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider.__new__(OpenAIProvider)
        provider._model_name = "gpt-4o-mini"
        provider._client = MagicMock()
        provider._client.chat.completions.create.return_value = self._mock_openai_response(
            '{"score": 85}', prompt_tokens=100, completion_tokens=60
        )

        result = provider.generate("test prompt")

        self.assertIsInstance(result, LLMResponse)
        self.assertEqual(result.provider, "openai")
        self.assertEqual(result.model, "gpt-4o-mini")
        self.assertEqual(result.usage.prompt_tokens, 100)
        self.assertEqual(result.usage.completion_tokens, 60)
        self.assertEqual(result.usage.total_tokens, 160)
        # gpt-4o-mini has 128k context → remaining = 128000 - 160
        self.assertEqual(result.usage.remaining_tokens, 128_000 - 160)
        self.assertEqual(result.request_id, "chatcmpl-abc")


# ── HuggingFaceProvider ───────────────────────────────────────────────────────

class TestHuggingFaceProvider(unittest.TestCase):
    @patch("shared.providers.huggingface_provider.HuggingFaceProvider.__init__",
           lambda self, **kwargs: None)
    def test_generate_chat_completion(self):
        from shared.providers.huggingface_provider import HuggingFaceProvider
        provider = HuggingFaceProvider.__new__(HuggingFaceProvider)
        provider._model_name = "mistralai/Mistral-7B-Instruct-v0.3"

        mock_result = MagicMock()
        mock_result.choices[0].message.content = '{"headline": "Engineer"}'
        mock_result.usage = None  # HF doesn't return usage

        provider._client = MagicMock()
        provider._client.chat_completion.return_value = mock_result

        result = provider.generate("Summarize this resume")

        self.assertIsInstance(result, LLMResponse)
        self.assertEqual(result.provider, "huggingface")
        self.assertIsNone(result.usage.remaining_tokens)
        # Token counts should be estimated (> 0)
        self.assertGreater(result.usage.prompt_tokens, 0)


# ── Provider Factory via get_provider() ───────────────────────────────────────

class TestGetProvider(unittest.TestCase):
    def tearDown(self):
        # Reset singleton between tests
        import shared.llm_client as llm_client
        llm_client._provider = None

    @patch("shared.llm_client.app_config")
    @patch("shared.llm_client._build_provider")
    def test_singleton_returned_on_second_call(self, mock_build, mock_cfg):
        mock_build.return_value = MagicMock()
        from shared.llm_client import get_provider
        import shared.llm_client as llm_client
        llm_client._provider = None

        p1 = get_provider()
        p2 = get_provider()
        self.assertIs(p1, p2)
        mock_build.assert_called_once()

    def test_build_provider_gemini(self):
        """_build_provider should return a GeminiProvider when provider='gemini'."""
        # Stub out google.generativeai so the import in GeminiProvider.__init__ succeeds
        mock_genai = MagicMock()
        mock_genai.GenerativeModel.return_value = MagicMock()
        sys.modules.setdefault("google", MagicMock())
        sys.modules["google.generativeai"] = mock_genai

        import shared.llm_client as llm_client
        llm_client._provider = None

        with patch.object(llm_client.app_config, "get_llm_provider", return_value="gemini"), \
             patch.object(llm_client.app_config, "get_gemini_api_key", return_value="fake"), \
             patch.object(llm_client.app_config, "get_llm_model", return_value="gemini-2.0-flash"):
            from shared.providers.gemini_provider import GeminiProvider
            from shared.llm_client import _build_provider
            provider = _build_provider()
            self.assertIsInstance(provider, GeminiProvider)

        # Cleanup
        sys.modules.pop("google", None)
        sys.modules.pop("google.generativeai", None)
        sys.modules.pop("shared.providers.gemini_provider", None)
        llm_client._provider = None


# ── llm_client end-to-end (mocked provider) ──────────────────────────────────

class TestLLMClientFacade(unittest.TestCase):
    def setUp(self):
        import shared.llm_client as llm_client
        self.mock_provider = MagicMock()
        llm_client._provider = self.mock_provider

    def tearDown(self):
        import shared.llm_client as llm_client
        llm_client._provider = None

    def _set_response(self, text: str):
        usage = TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80)
        self.mock_provider.generate.return_value = LLMResponse(
            text=text, usage=usage, provider="gemini", model="gemini-2.0-flash"
        )
        self.mock_provider.provider_name = "gemini"

    @patch("shared.llm_client._record_usage")
    def test_summarize_resume(self, mock_record):
        payload = {
            "headline": "Senior Engineer",
            "total_experience_years": 8,
            "skills": ["Python", "AWS"],
            "key_strengths": ["Leadership"],
            "education": "B.Tech Computer Science",
            "summary_text": "Experienced engineer.",
        }
        self._set_response(json.dumps(payload))

        from shared.llm_client import summarize_resume
        result = summarize_resume("resume.pdf", "Full resume text here")

        self.assertEqual(result["headline"], "Senior Engineer")
        self.assertEqual(result["resume_name"], "resume.pdf")
        self.assertEqual(result["skills"], ["Python", "AWS"])
        mock_record.assert_called_once()

    @patch("shared.llm_client._record_usage")
    def test_score_resume_vs_jd(self, mock_record):
        payload = {
            "overall_score": 82,
            "keyword_score": 75,
            "semantic_score": 88,
            "matched_skills": ["Python", "Django"],
            "missing_skills": ["Kubernetes"],
            "recommendation": "Add cloud experience.",
        }
        self._set_response(json.dumps(payload))

        from shared.llm_client import score_resume_vs_jd
        result = score_resume_vs_jd("resume text", "jd text",
                                    {"job_title": "Engineer", "company": "Acme",
                                     "location": "Remote"})

        self.assertIsInstance(result, MatchResult)
        self.assertEqual(result.overall_score, 82.0)
        self.assertEqual(result.matched_skills, ["Python", "Django"])

    @patch("shared.llm_client._record_usage")
    def test_fence_stripping(self, mock_record):
        """Ensure markdown code fences are stripped before JSON parsing."""
        payload = {"headline": "Dev", "total_experience_years": 3,
                   "skills": [], "key_strengths": [], "education": "",
                   "summary_text": ""}
        fenced = f"```json\n{json.dumps(payload)}\n```"
        self._set_response(fenced)

        from shared.llm_client import summarize_resume
        result = summarize_resume("r.pdf", "text")
        self.assertEqual(result["headline"], "Dev")

    @patch("shared.llm_client._record_usage")
    def test_summarize_resume_error_returns_fallback(self, mock_record):
        """On JSON parse failure the function returns a fallback dict, not raises."""
        usage = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        self.mock_provider.generate.return_value = LLMResponse(
            text="NOT JSON AT ALL", usage=usage,
            provider="gemini", model="gemini-2.0-flash"
        )

        from shared.llm_client import summarize_resume
        result = summarize_resume("bad.pdf", "text")
        self.assertEqual(result["resume_name"], "bad.pdf")
        self.assertEqual(result["headline"], "Summary generation failed")

    @patch("shared.llm_client._record_usage")
    def test_match_jd_against_summaries_empty(self, mock_record):
        from shared.llm_client import match_jd_against_summaries
        result = match_jd_against_summaries("jd text", [])
        self.assertEqual(result, [])
        self.mock_provider.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
