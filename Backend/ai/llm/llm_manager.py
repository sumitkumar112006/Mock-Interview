import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Ensure Backend/.env is loaded
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Log directory
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LLM_LOG_FILE = LOG_DIR / "llm_interactions.log"


class LLMManager:
    """
    Centralized LLM execution & logging engine with millisecond-precision timing,
    strict timeout enforcement, fast error handling, and automated fallback chains.
    """

    MODEL_NAME = "qwen/qwen3.8-27b"
    FALLBACK_MODEL = "llama-3.3-70b-versatile"
    DEFAULT_TIMEOUT_SECONDS = 6.0
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            api_key = os.getenv("GROQ_API_KEY", "").strip()
            if not api_key:
                return None
            try:
                from groq import Groq
                # Strict timeout and single retry to guarantee millisecond fail-fast responsiveness
                cls._client = Groq(api_key=api_key, timeout=cls.DEFAULT_TIMEOUT_SECONDS, max_retries=1)
            except Exception as e:
                print(f"[LLMManager] Groq initialization warning: {e}")
                cls._client = None
        return cls._client

    @classmethod
    def call_llm(
        cls,
        prompt: str,
        system_instruction: str = "You are an elite, objective technical interviewer and talent assessor.",
        temperature: float = 0.3,
        max_tokens: int = 1200,
        context_name: str = "General",
        response_format: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """
        Executes an LLM chat completion with millisecond latency logging and robust error handling.
        """
        effective_timeout = timeout or cls.DEFAULT_TIMEOUT_SECONDS
        client = cls.get_client()
        timestamp_req = datetime.now(timezone.utc).isoformat()
        req_id = f"req_{int(time.time() * 1000)}"

        # -------------------------------------------------------------
        # 1. LOG REQUEST
        # -------------------------------------------------------------
        req_log_entry = {
            "event": "LLM_REQUEST",
            "request_id": req_id,
            "context": context_name,
            "timestamp": timestamp_req,
            "model": cls.MODEL_NAME,
            "timeout_seconds": effective_timeout,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        print("\n" + "=" * 70)
        print(f"🤖 [LLM REQUEST] Context: {context_name} | ID: {req_id} | Timeout: {effective_timeout}s")
        print(f"🕒 Timestamp: {timestamp_req}")
        print(f"🧠 Primary Model: {cls.MODEL_NAME}")
        print("-" * 70)
        print("📋 System Instruction:")
        print(system_instruction[:250] + ("..." if len(system_instruction) > 250 else ""))
        print("-" * 70)
        print("💬 Prompt Snippet:")
        print(prompt[:400] + ("..." if len(prompt) > 400 else ""))
        print("=" * 70 + "\n")

        cls._append_to_log(req_log_entry)

        if not client:
            print(f"[LLMManager] Groq client unavailable. Fast-failing in 0ms to rule-based fallback.")
            return None

        # -------------------------------------------------------------
        # 2. EXECUTE LLM CALL WITH MILLISECOND TIMER
        # -------------------------------------------------------------
        start_time = time.perf_counter()
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]

        kwargs: Dict[str, Any] = {
            "model": cls.MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": effective_timeout,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            chat_completion = client.chat.completions.create(**kwargs)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            timestamp_res = datetime.now(timezone.utc).isoformat()

            raw_response = chat_completion.choices[0].message.content or ""
            usage = getattr(chat_completion, "usage", None)
            tokens_info = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
                "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
                "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
            }

            res_log_entry = {
                "event": "LLM_RESPONSE",
                "request_id": req_id,
                "context": context_name,
                "timestamp": timestamp_res,
                "latency_ms": latency_ms,
                "model": cls.MODEL_NAME,
                "tokens": tokens_info,
                "response_length": len(raw_response)
            }

            print("\n" + "#" * 70)
            print(f"✨ [LLM RESPONSE SUCCESS] Context: {context_name} | ID: {req_id} | ⚡ Latency: {latency_ms}ms")
            print(f"🕒 Timestamp: {timestamp_res}")
            print(f"📊 Tokens: Prompt={tokens_info.get('prompt_tokens')} | Completion={tokens_info.get('completion_tokens')} | Total={tokens_info.get('total_tokens')}")
            print("-" * 70)
            print("📝 Content Preview:")
            print(raw_response[:500] + ("..." if len(raw_response) > 500 else ""))
            print("#" * 70 + "\n")

            cls._append_to_log(res_log_entry)
            return raw_response

        except Exception as primary_err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            print(f"\n⚠️ [LLM PRIMARY FAIL] ID: {req_id} | Model: {cls.MODEL_NAME} failed after {latency_ms}ms: {primary_err}")

            # Fast attempt with fallback model (timeout 3.5s)
            fallback_start = time.perf_counter()
            try:
                print(f"🔄 [LLM FALLBACK ATTEMPT] Dispatching to {cls.FALLBACK_MODEL}...")
                fallback_kwargs = {**kwargs, "model": cls.FALLBACK_MODEL, "timeout": 3.5}
                fb_completion = client.chat.completions.create(**fallback_kwargs)
                fb_latency_ms = round((time.perf_counter() - fallback_start) * 1000, 2)
                total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                raw_fb_response = fb_completion.choices[0].message.content or ""
                print(f"✨ [LLM FALLBACK SUCCESS] Model: {cls.FALLBACK_MODEL} succeeded in {fb_latency_ms}ms (Total: {total_latency_ms}ms)")
                return raw_fb_response
            except Exception as fb_err:
                total_fail_ms = round((time.perf_counter() - start_time) * 1000, 2)
                err_log_entry = {
                    "event": "LLM_FAST_FAIL",
                    "request_id": req_id,
                    "context": context_name,
                    "latency_ms": total_fail_ms,
                    "primary_error": str(primary_err),
                    "fallback_error": str(fb_err)
                }
                print(f"❌ [LLM ALL MODELS FAILED] ID: {req_id} | Elapsed: {total_fail_ms}ms -> Switching to instant 1ms heuristic engine.\n")
                cls._append_to_log(err_log_entry)
                return None

    @classmethod
    def _append_to_log(cls, entry: Dict[str, Any]):
        try:
            with open(LLM_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[LLMManager] Warning: failed to write to log file: {e}")
