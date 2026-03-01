"""
Test Auto-Conductor with Different Scenarios
Tests multiple interview runs with different expected outcomes
"""
import requests
import time
import json
from typing import Dict, List

BASE_URL = "http://localhost:8000"

# Different interview IDs for different test scenarios
TEST_SCENARIOS = {
    "excellent_candidate": {
        "interview_id": "8981e204-605b-4693-bbcf-34d7bbb61db3",
        "description": "Excellent candidate - should get mostly 7-10/10 scores",
        "expected_avg_score": 7.5
    },
    "good_candidate": {
        "interview_id": "8981e204-605b-4693-bbcf-34d7bbb61db3",
        "description": "Good candidate - should get mostly 5-8/10 scores", 
        "expected_avg_score": 6.5
    },
    "average_candidate": {
        "interview_id": "8981e204-605b-4693-bbcf-34d7bbb61db3",
        "description": "Average candidate - should get mostly 4-6/10 scores",
        "expected_avg_score": 5.0
    }
}


def reset_interview(interview_id: str) -> bool:
    """Reset interview to scheduled state"""
    print(f"\n🔄 Resetting interview {interview_id}...")
    
    # Try to get interview first
    response = requests.get(f"{BASE_URL}/api/interviews/{interview_id}")
    if response.status_code != 200:
        print(f"❌ Interview not found: {response.status_code}")
        return False
    
    # Update to reset state
    reset_data = {
        "status": "scheduled",
        "current_question_index": 0,
        "questions": [],
        "answers": []
    }
    
    response = requests.put(
        f"{BASE_URL}/api/interviews/{interview_id}",
        json=reset_data
    )
    
    if response.status_code == 200:
        print("✅ Interview reset successfully")
        return True
    else:
        print(f"❌ Failed to reset: {response.text}")
        return False


def run_auto_conduct(interview_id: str, scenario_name: str) -> Dict:
    """Run auto-conduct for an interview"""
    print(f"\n{'='*70}")
    print(f"🎯 SCENARIO: {scenario_name}")
    print(f"📝 Interview ID: {interview_id}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    # Start auto-conduct
    response = requests.post(
        f"{BASE_URL}/api/interviews/{interview_id}/auto-conduct",
        json={"max_questions": 10}
    )
    
    if response.status_code != 200:
        print(f"❌ Auto-conduct failed: {response.status_code}")
        print(response.text)
        return {}
    
    result = response.json()
    elapsed = time.time() - start_time
    
    print(f"\n✅ Auto-conduct completed in {elapsed:.1f}s")
    return result


def analyze_results(result: Dict, scenario: Dict):
    """Analyze and display interview results"""
    if not result.get('success'):
        print(f"❌ Interview failed: {result.get('message')}")
        return
    
    data = result.get('data', {})
    
    print(f"\n{'='*70}")
    print(f"📊 RESULTS ANALYSIS - {scenario['description']}")
    print(f"{'='*70}\n")
    
    # Overall stats
    print(f"📝 Questions Asked: {data.get('questions_asked', 0)}")
    print(f"🔄 Follow-ups Generated: {data.get('followups_generated', 0)}")
    print(f"⏱️  Total Time: {data.get('total_time', 0):.1f}s")
    print(f"📋 Final Status: {data.get('final_status', 'N/A')}")
    
    # Score breakdown
    answers = data.get('answers', [])
    if answers:
        scores = [a.get('score', 0) for a in answers if a.get('score') is not None]
        
        if scores:
            avg_score = sum(scores) / len(scores)
            expected_avg = scenario.get('expected_avg_score', 0)
            
            print(f"\n📈 SCORING BREAKDOWN:")
            print(f"   Average Score: {avg_score:.1f}/10")
            print(f"   Expected Avg: {expected_avg:.1f}/10")
            print(f"   Total Answers: {len(scores)}")
            print(f"   Score Range: {min(scores)}-{max(scores)}/10")
            
            # Score distribution
            score_buckets = {
                "Excellent (8-10)": sum(1 for s in scores if s >= 8),
                "Good (6-7)": sum(1 for s in scores if 6 <= s < 8),
                "Average (4-5)": sum(1 for s in scores if 4 <= s < 6),
                "Poor (0-3)": sum(1 for s in scores if s < 4)
            }
            
            print(f"\n   Score Distribution:")
            for label, count in score_buckets.items():
                if count > 0:
                    percentage = (count / len(scores)) * 100
                    bar = "█" * int(percentage / 5)
                    print(f"   {label:20s}: {count:2d} ({percentage:5.1f}%) {bar}")
            
            # Question-by-question breakdown
            print(f"\n📋 QUESTION-BY-QUESTION:")
            for i, answer in enumerate(answers, 1):
                score = answer.get('score', 0)
                question = answer.get('question', 'N/A')[:60]
                ans_text = answer.get('answer', 'N/A')[:60]
                
                emoji = "🟢" if score >= 8 else "🟡" if score >= 6 else "🟠" if score >= 4 else "🔴"
                print(f"\n   Q{i}. {emoji} Score: {score}/10")
                print(f"       Q: {question}...")
                print(f"       A: {ans_text}...")
    else:
        print("\n⚠️  No answers recorded")
    
    print(f"\n{'='*70}\n")


def run_scenario(scenario_name: str, scenario: Dict):
    """Run a complete test scenario"""
    interview_id = scenario['interview_id']
    
    # Reset interview
    if not reset_interview(interview_id):
        print(f"❌ Skipping scenario {scenario_name} - reset failed")
        return
    
    # Wait a bit for reset to complete
    time.sleep(2)
    
    # Run auto-conduct
    result = run_auto_conduct(interview_id, scenario_name)
    
    # Analyze results
    if result:
        analyze_results(result, scenario)


def main():
    """Run all test scenarios"""
    print("\n" + "="*70)
    print("🧪 AUTOMATED INTERVIEW TESTING - MULTIPLE SCENARIOS")
    print("="*70)
    
    print(f"\n📋 Testing {len(TEST_SCENARIOS)} scenarios:")
    for name, scenario in TEST_SCENARIOS.items():
        print(f"   • {name}: {scenario['description']}")
    
    input("\n⏸️  Press Enter to start testing...")
    
    # Run each scenario
    for scenario_name, scenario in TEST_SCENARIOS.items():
        run_scenario(scenario_name, scenario)
        
        # Pause between scenarios
        if scenario_name != list(TEST_SCENARIOS.keys())[-1]:
            print("\n⏸️  Pausing 5 seconds before next scenario...")
            time.sleep(5)
    
    print("\n" + "="*70)
    print("✅ ALL SCENARIOS COMPLETED")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
