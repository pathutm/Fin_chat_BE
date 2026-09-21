#!/usr/bin/env python3
"""Focused greeting tests for the updated Input Guardrail."""
import asyncio, sys
sys.path.insert(0, "/Users/user/Desktop/Rish´/Finance/Fin_chat_BE")
from dotenv import load_dotenv
load_dotenv("/Users/user/Desktop/Rish´/Finance/Fin_chat_BE/.env")
from guardrails.actions import check_input_guardrail

TESTS = [
    # (label, message, expected_allowed)
    # ── Standalone greetings → MUST be ALLOWED ──────────────────────────────
    ("Hi",                       "hi",              True),
    ("Hello",                    "hello",           True),
    ("Hey",                      "hey",             True),
    ("Hii",                      "hii",             True),
    ("Heyy",                     "heyy",            True),
    ("Good morning",             "good morning",    True),
    ("Good afternoon",           "good afternoon",  True),
    ("Good evening",             "good evening",    True),
    ("How are you?",             "how are you?",    True),
    ("How are u",                "how are u",       True),
    # ── Greeting + finance → MUST be ALLOWED ────────────────────────────────
    ("Hello + PO query",
     "Hello, what is the status of purchase order PO-000001?", True),
    # ── Greeting + non-finance → MUST be BLOCKED ────────────────────────────
    ("Hello + weather",          "Hello, what is the weather?",         False),
    ("Hi + joke",                "Hi, tell me a joke",                  False),
    ("Hey + coding",             "Hey, write Python code",              False),
]

async def run():
    print("=" * 72)
    print("FOCUSED GREETING TESTS — Input Guardrail")
    print("=" * 72)
    results = []
    for label, msg, exp in TESTS:
        res = await check_input_guardrail(msg)
        allowed = res.is_allowed or ("Hello!" in res.response_text)
        ok = (allowed == exp)
        results.append((label, msg, "ALLOWED" if allowed else "BLOCKED",
                        "ALLOWED" if exp else "BLOCKED", "PASS ✅" if ok else "FAIL ❌"))

    print(f"\n{'Label':<26} | {'Decision':<8} | {'Expected':<8} | Result")
    print("-" * 62)
    all_ok = True
    for label, msg, dec, exp, verdict in results:
        all_ok = all_ok and verdict.startswith("PASS")
        print(f"{label:<26} | {dec:<8} | {exp:<8} | {verdict}")
    print("=" * 62)
    print(f"OVERALL: {'ALL PASSED ✅' if all_ok else 'SOME FAILED ❌'}")

asyncio.run(run())
