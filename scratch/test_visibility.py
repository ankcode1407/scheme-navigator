import os
import json
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

# Make sure offline flags are set so it behaves deterministically
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"
os.environ["ADMIN_TOKEN"] = "test-token-123"

from app.api.routes import app

def test_visibility_and_metrics():
    client = TestClient(app)
    
    # 1. Clean up existing files if any, to start fresh
    metrics_path = Path("data/metrics.jsonl")
    feedback_path = Path("data/feedback.jsonl")
    sessions_path = Path("data/sessions.json")
    
    for p in [metrics_path, feedback_path, sessions_path]:
        if p.exists():
            p.unlink()
            
    session_id = str(uuid.uuid4())
    print(f"Created session: {session_id}")
    
    # 2. Trigger first chat message (Empty User Profile / Onboarding)
    # The message text does not matter here since context is empty
    print("\n--- 1. Testing Onboarding Initiation ---")
    resp = client.post("/chat", json={"message": "hello", "session_id": session_id})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    resp_data = resp.json()
    
    # Verify response matches onboarding format
    assert "type" in resp_data["response"], "Response content should contain onboarding metadata"
    onboarding_payload = json.loads(resp_data["response"])
    assert onboarding_payload["type"] == "onboarding"
    assert "Farming or crop support" in onboarding_payload["quick_options"]
    print("Success: Onboarding message and options returned on first message.")
    
    # Check that it didn't call LangGraph (response is onboarding json, schemes_found is 0)
    assert resp_data["schemes_found"] == 0
    assert resp_data["reranker_mode"] == "retrieval_only"
    
    # 3. Trigger second chat message selection (Pre-seeding category)
    print("\n--- 2. Testing Onboarding Quick Selection ---\n")
    resp = client.post("/chat", json={"message": "Farming or crop support", "session_id": session_id})
    assert resp.status_code == 200
    resp_data = resp.json()
    
    # Check that problem_category is pre-seeded as "agriculture"
    assert resp_data["problem_category"] == "agriculture", f"Expected problem_category='agriculture', got {resp_data['problem_category']}"
    print(f"Success: Pre-seeded problem_category: {resp_data['problem_category']}")
    print(f"Reranker Mode returned: {resp_data['reranker_mode']}")
    
    # 4. Invoke `/chat` with a query that matches a scheme to check metrics logging
    print("\n--- 3. Testing Scheme Search Query and Mode Logging ---\n")
    session_id_2 = str(uuid.uuid4())
    resp = client.post("/chat", json={"message": "Bihar Rajya Fasal Sahayata Yojna", "session_id": session_id_2})
    assert resp.status_code == 200
    resp_data = resp.json()
    
    # Wait, the first request in a new session always gets onboarding!
    # So let's reply with the query in the second message, or use a pre-existing session.
    resp = client.post("/chat", json={"message": "Bihar Rajya Fasal Sahayata Yojna", "session_id": session_id_2})
    assert resp.status_code == 200
    resp_data = resp.json()
    print(f"Schemes found: {resp_data['schemes_found']}")
    print(f"Reranker Mode returned: {resp_data['reranker_mode']}")
    
    # 5. Check if metrics are logged to metrics.jsonl
    print("\n--- 4. Checking metrics.jsonl records ---")
    assert metrics_path.exists(), "metrics.jsonl was not created!"
    metrics_lines = metrics_path.read_text(encoding="utf-8").strip().split("\n")
    print(f"Logged {len(metrics_lines)} metrics entries.")
    for idx, line in enumerate(metrics_lines):
        entry = json.loads(line)
        print(f"  Entry {idx}: mode={entry.get('reranker_mode')}, response_type={entry.get('response_type')}, top_scheme={entry.get('top_scheme_id')}")
        
    # 6. Test admin stats endpoint
    print("\n--- 5. Testing GET /api/admin/stats ---")
    # Unauthorized request (no token)
    resp = client.get("/api/admin/stats")
    assert resp.status_code == 401
    print("Success: Unauthorized request returned 401.")
    
    # Unauthorized request (wrong token)
    resp = client.get("/api/admin/stats", headers={"X-Admin-Token": "wrong-token"})
    assert resp.status_code == 401
    print("Success: Incorrect token returned 401.")
    
    # Authorized request
    resp = client.get("/api/admin/stats", headers={"X-Admin-Token": "test-token-123"})
    assert resp.status_code == 200
    stats = resp.json()
    print("Success: Authorized request returned 200.")
    print(json.dumps(stats, indent=2))
    
    # 7. Post feedback
    print("\n--- 6. Testing feedback endpoint ---")
    feedback_req = {
        "scheme_id": "brfsy",
        "interaction_type": "click"
    }
    resp = client.post(f"/api/sessions/{session_id_2}/feedback", json=feedback_req)
    assert resp.status_code == 200
    assert feedback_path.exists(), "feedback.jsonl was not created!"
    print("Success: Logged feedback event successfully.")
    
    # 8. Run analyze_feedback.py
    print("\n--- 7. Running scripts/analyze_feedback.py ---")
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.analyze_feedback import main as run_feedback_analysis
    
    try:
        run_feedback_analysis()
        print("Success: scripts/analyze_feedback.py completed without raising exceptions.")
    except Exception as e:
        print(f"Failed to run analyze_feedback: {e}")
        raise

if __name__ == "__main__":
    test_visibility_and_metrics()
