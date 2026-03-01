"""
Debug script to test sentiment analysis and confidence scoring
"""
import os
import sys
from dotenv import load_dotenv
from groq import Groq
import json

# Load environment variables
load_dotenv()

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Test transcriptions from your audio tests
test_transcriptions = [
    {
        "name": "Introduction",
        "text": "Hello, my name is John Smith. I am a software engineer with 5 years of experience in Python and Machine Learning.",
        "context": "Introduction question"
    },
    {
        "name": "Technical Skills",
        "text": "I have extensive experience with Langraph, FastAPI, MongoDB, and Natural Language Processing. I've built scalable microservices in RESTful APIS.",
        "context": "Technical skills discussion"
    },
    {
        "name": "Behavioral",
        "text": "Describe a time when you faced a difficult challenge at work. I once had to resolve a critical production bug during a live deployment. The system was experiencing high latency due to inefficient database queries. I quickly identified the bottleneck, optimized the queries, and reduced response time by 70%.",
        "context": "Behavioral question"
    },
    {
        "name": "Leadership",
        "text": "Tell me about your leadership experience. I led a team of five engineers to develop a microservices architecture using Docker and Kubernetes. We implemented continuous integration and continuous deployment pipelines, which improved our deployment frequency by 300%. I mentored junior developers and conducted code reviews to maintain high-quality standards.",
        "context": "Leadership experience"
    }
]

print("=" * 80)
print("TESTING GROQ LLM ANALYSIS")
print("=" * 80)
print()

for test in test_transcriptions:
    print(f"\n{'=' * 80}")
    print(f"TEST: {test['name']}")
    print(f"{'=' * 80}")
    print(f"Text: {test['text']}")
    print(f"Context: {test['context']}")
    print()
    
    # Test 1: Clean Transcription
    print("[1] Testing Clean Transcription...")
    clean_prompt = f"""You are a transcription cleaning expert. Clean and improve this transcription.

Transcription: "{test['text']}"

Provide a JSON response with:
1. "cleaned_text": The cleaned transcription
2. "confidence": Your confidence in the cleaning (0.0-1.0)
3. "notable_changes": List of significant corrections made
4. "speaker_indicators": Any detected speaker changes or emotions

Response:"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": clean_prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        
        cleaning_result = response.choices[0].message.content.strip()
        print(f"Raw Response:\n{cleaning_result}\n")
        
        # Parse JSON
        try:
            if "```json" in cleaning_result:
                cleaning_result = cleaning_result.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaning_result:
                cleaning_result = cleaning_result.split("```")[1].split("```")[0].strip()
            
            cleaned_data = json.loads(cleaning_result)
            print(f"✅ Parsed Successfully!")
            print(f"   Cleaned Text: {cleaned_data.get('cleaned_text', 'N/A')[:100]}...")
            print(f"   Confidence: {cleaned_data.get('confidence', 'N/A')}")
            print(f"   Notable Changes: {cleaned_data.get('notable_changes', [])}")
            print()
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {str(e)}")
            print()
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        print()
    
    # Test 2: Content Analysis
    print("[2] Testing Content Analysis...")
    analysis_prompt = f"""Analyze this interview transcription segment and extract insights.

Context:
Transcription: {test['text']}
Interview ID: test_001
Question context: {test['context']}

Provide a JSON response with:
1. "sentiment": Overall sentiment (positive, neutral, negative, mixed)
2. "key_points": List of 3-5 main points or ideas expressed
3. "technical_terms": Technical terms or jargon used
4. "clarity_score": How clear and coherent the response is (0.0-1.0)
5. "completeness": Is this a complete thought or partial response
6. "follow_up_needed": Does this require follow-up questions (true/false)

Response:"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        
        analysis_result = response.choices[0].message.content.strip()
        print(f"Raw Response:\n{analysis_result}\n")
        
        # Parse JSON
        try:
            if "```json" in analysis_result:
                analysis_result = analysis_result.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_result:
                analysis_result = analysis_result.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(analysis_result)
            print(f"✅ Parsed Successfully!")
            print(f"   Sentiment: {analysis.get('sentiment', 'N/A')}")
            print(f"   Key Points: {analysis.get('key_points', [])}")
            print(f"   Technical Terms: {analysis.get('technical_terms', [])}")
            print(f"   Clarity Score: {analysis.get('clarity_score', 'N/A')}")
            print(f"   Completeness: {analysis.get('completeness', 'N/A')}")
            print()
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {str(e)}")
            print()
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        print()

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
