import sys
from app.agent.constants import get_language_gate_prompt, get_localized_string
from app.agent.graph import agent

def test_locale_fallback():
    print("--- 1. Testing Locale Fallback Logic ---")
    
    # 1. Exact match test
    exact_match = get_language_gate_prompt("bn-IN")
    assert exact_match == "অনুগ্রহ করে আগে আপনার ভাষা নির্বাচন করুন।", f"Exact match failed. Got: {exact_match}"
    print("✅ Exact match ('bn-IN') passed.")

    # 2. Short-code fallback test (The bug fix)
    short_match = get_language_gate_prompt("bn")
    assert short_match == "অনুগ্রহ করে আগে আপনার ভাষা নির্বাচন করুন।", f"Short-code match failed. Got: {short_match}"
    print("✅ Short-code fallback ('bn') passed.")

    # 3. Default fallback test (Unknown locale)
    default_match = get_language_gate_prompt("xyz")
    assert default_match == "Please choose your language first.", f"Default fallback failed. Got: {default_match}"
    print("✅ Unknown locale fallback ('xyz' -> 'en-IN') passed.\n")


def test_graph_and_tts_state():
    print("--- 2. Testing LangGraph Flow & TTS State ---")
    
    # Simulating a user entering a short language code
    initial_state = {
        "session_id": "test_session_001",
        "user_input": "bangla", 
    }
    
    try:
        # Run the graph
        final_state = agent.invoke(initial_state)
        
        # Extract the relevant fields that Sarvam AI will need
        pref_lang = final_state.get("preferred_language")
        resp_lang = final_state.get("response_language")
        tts_text = final_state.get("response_tts_text")
        should_play = final_state.get("should_play_tts")

        print(f"User Input: '{initial_state['user_input']}'")
        print(f"Preferred Language Resolved To: {pref_lang}")
        print(f"Response Language (TTS Locale): {resp_lang}")
        print(f"Generated TTS Text: {tts_text}")
        print(f"Should Play TTS: {should_play}")

        # Assertions to ensure the graph routed correctly and set state
        assert pref_lang == "bn-IN", f"Graph failed to resolve 'bangla' to 'bn-IN'. Got {pref_lang}"
        assert resp_lang == "bn-IN", f"Final response language mismatch. Got {resp_lang}"
        assert tts_text is not None, "TTS text was not generated."
        
        print("✅ Graph routed correctly through finalize_response.")
        print("✅ TTS payload state variables are correctly formatted.\n")

    except Exception as e:
        print(f"❌ Graph execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting Pre-Push Verification...\n")
    try:
        test_locale_fallback()
        test_graph_and_tts_state()
        print("🎉 All checks passed! You are clear to push to GitHub.")
    except AssertionError as ae:
        print(f"❌ Verification Failed: {ae}")
        sys.exit(1)