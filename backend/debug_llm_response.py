"""
Quick debug script to see what the LLM is actually returning
"""
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Load .env file
load_dotenv()

# Setup
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key:
    print("❌ GROQ_API_KEY not set")
    exit(1)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=groq_api_key,
    temperature=0,
    max_tokens=1000
)

# Test prompt
prompt = """Extract key information from this resume. Return ONLY a valid JSON object, no markdown, no explanation.

Resume:
John Doe
Senior Software Engineer
5 years experience
Skills: Python, JavaScript, React, Node.js
Education: BS Computer Science
Certifications: AWS Certified Developer

Extract and return this EXACT JSON structure:
{
  "skills": ["skill1", "skill2"],
  "years_experience": 5,
  "education_level": "Bachelor's",
  "certifications": ["cert1"]
}

IMPORTANT:
- Return ONLY the JSON object
- NO markdown code blocks
- NO additional text
- Skills should be specific technical skills
- Years of experience as a number"""

messages = [
    SystemMessage(content="You are a resume parser. Extract information accurately. Return ONLY valid JSON, no markdown."),
    HumanMessage(content=prompt)
]

print("🔍 Calling LLM...")
response = llm.invoke(messages)

print("\n" + "="*80)
print("RAW RESPONSE:")
print("="*80)
print(f"Type: {type(response)}")
print(f"Has content: {hasattr(response, 'content')}")

if hasattr(response, 'content'):
    content = response.content
    print(f"Content type: {type(content)}")
    print(f"Content length: {len(str(content))} chars")
    print("\nContent:")
    print(content)
else:
    print(f"Response: {response}")

print("\n" + "="*80)
