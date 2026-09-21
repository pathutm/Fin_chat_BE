#!/usr/bin/env python3
"""Verification test for negative confirmation flow and all 4 requested test cases."""
import asyncio
import sys
import os

sys.path.insert(0, "/Users/user/Desktop/Rish´/Finance/Fin_chat_BE")
from dotenv import load_dotenv
load_dotenv("/Users/user/Desktop/Rish´/Finance/Fin_chat_BE/.env")

from guardrails.actions import check_input_guardrail, pending_confirmations

async def run_tests():
    print("=" * 80)
    print("TESTING NEGATIVE CONFIRMATION FLOW & ALL 4 REQUIRED CASES")
    print("=" * 80)

    # CASE 1: Mixed message with PII + finance question
    conv_id_1 = "test-conv-flow-1"
    msg_1 = "What is working capital and my phone number is 23445435"
    res_1 = await check_input_guardrail(msg_1, conversation_id=conv_id_1)

    print("\n--- CASE 1 ---")
    print(f"User: {msg_1}")
    print(f"is_allowed: {res_1.is_allowed}")
    print(f"requires_confirmation: {res_1.requires_confirmation}")
    print(f"safe_finance_query: {res_1.safe_finance_query}")
    print(f"response_text: {res_1.response_text[:120]}...")
    pass_1 = (not res_1.is_allowed) and res_1.requires_confirmation and (res_1.safe_finance_query == "What is working capital?") and ("Would you like me to process this finance-related question?" in res_1.response_text)
    print(f"RESULT CASE 1: {'PASS ✅' if pass_1 else 'FAIL ❌'}")

    # CASE 2: Reply "Yes" to confirmation
    msg_2 = "Yes"
    res_2 = await check_input_guardrail(msg_2, conversation_id=conv_id_1)

    print("\n--- CASE 2 ---")
    print(f"User: {msg_2}")
    print(f"is_allowed: {res_2.is_allowed}")
    print(f"safe_finance_query: {res_2.safe_finance_query}")
    pass_2 = res_2.is_allowed and (res_2.safe_finance_query == "What is working capital?")
    print(f"RESULT CASE 2: {'PASS ✅' if pass_2 else 'FAIL ❌'}")

    # CASE 3: Mixed message then "No"
    conv_id_3 = "test-conv-flow-3"
    msg_3a = "What is working capital and my phone number is 23445435"
    res_3a = await check_input_guardrail(msg_3a, conversation_id=conv_id_3)

    msg_3b = "No"
    res_3b = await check_input_guardrail(msg_3b, conversation_id=conv_id_3)

    print("\n--- CASE 3 ---")
    print(f"User step 1: {msg_3a}")
    print(f"User step 2: {msg_3b}")
    print(f"is_allowed: {res_3b.is_allowed}")
    print(f"response_text: {res_3b.response_text}")
    print(f"pending_confirmations for conv_id_3: {pending_confirmations.get(conv_id_3)}")
    pass_3 = (not res_3b.is_allowed) and (res_3b.response_text == "Okay, no problem. I won’t process the finance question. If you need anything else, feel free to ask.") and (conv_id_3 not in pending_confirmations)
    print(f"RESULT CASE 3: {'PASS ✅' if pass_3 else 'FAIL ❌'}")

    # CASE 4: After saying "No", send "What is working capital?"
    msg_4 = "What is working capital?"
    res_4 = await check_input_guardrail(msg_4, conversation_id=conv_id_3)

    print("\n--- CASE 4 ---")
    print(f"User: {msg_4}")
    print(f"is_allowed: {res_4.is_allowed}")
    print(f"response_text: {res_4.response_text}")
    pass_4 = res_4.is_allowed
    print(f"RESULT CASE 4: {'PASS ✅' if pass_4 else 'FAIL ❌'}")

    # ALSO TEST VARIATIONS OF NEGATIVE CONFIRMATION (nope, nah, no thanks, etc.)
    variations = ["no", "Nope", "nah", "No thanks", "No, thank you", "Not now"]
    var_all_pass = True
    print("\n--- TESTING NEGATIVE CONFIRMATION VARIATIONS ---")
    for var in variations:
        cid = f"test-var-{var}"
        await check_input_guardrail("What is working capital and my phone number is 23445435", conversation_id=cid)
        r = await check_input_guardrail(var, conversation_id=cid)
        v_ok = (not r.is_allowed) and ("I won’t process the finance question" in r.response_text) and (cid not in pending_confirmations)
        print(f"Variation '{var}': {'PASS ✅' if v_ok else 'FAIL ❌'}")
        if not v_ok:
            var_all_pass = False

    print("\n" + "=" * 80)
    all_ok = pass_1 and pass_2 and pass_3 and pass_4 and var_all_pass
    print(f"OVERALL VERIFICATION RESULT: {'ALL 4 CASES PASSED ✅' if all_ok else 'SOME CASES FAILED ❌'}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_tests())
