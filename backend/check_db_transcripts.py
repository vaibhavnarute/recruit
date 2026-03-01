"""
Check MongoDB to see what's actually being stored
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
mongo_db_name = os.getenv('MONGO_DB_NAME', 'resumate')
client = MongoClient(mongo_uri)
db = client[mongo_db_name]
collection = db['meet_transcripts']

print("=" * 80)
print("CHECKING LATEST TRANSCRIPTS FROM MONGODB")
print("=" * 80)
print()

# Get the last 5 transcripts
transcripts = collection.find().sort("_id", -1).limit(5)

for i, transcript in enumerate(transcripts, 1):
    print(f"\n{'=' * 80}")
    print(f"TRANSCRIPT #{i}")
    print(f"{'=' * 80}")
    print(f"Session ID: {transcript.get('session_id', 'N/A')}")
    print(f"Chunk ID: {transcript.get('chunk_id', 'N/A')}")
    print(f"Timestamp: {transcript.get('transcribed_at', 'N/A')}")
    print()
    print(f"RAW TRANSCRIPTION:")
    print(f"  {transcript.get('raw_transcription', 'N/A')[:200]}...")
    print()
    print(f"CLEANED TRANSCRIPTION:")
    print(f"  {transcript.get('cleaned_transcription', 'N/A')[:200]}...")
    print()
    print(f"ANALYSIS:")
    print(f"  Confidence Score: {transcript.get('confidence_score', 'N/A')}")
    print(f"  Sentiment: {transcript.get('sentiment', 'N/A')}")
    print(f"  Language: {transcript.get('language_detected', 'N/A')}")
    print(f"  Speaker: {transcript.get('speaker_detected', 'N/A')}")
    print()
    print(f"KEY POINTS:")
    key_points = transcript.get('key_points', [])
    if key_points:
        for point in key_points:
            print(f"  - {point}")
    else:
        print(f"  None")
    print()
    print(f"TECHNICAL TERMS:")
    tech_terms = transcript.get('technical_terms', [])
    if tech_terms:
        for term in tech_terms:
            print(f"  - {term}")
    else:
        print(f"  None")
    print()
    print(f"PROCESSING:")
    print(f"  Model: {transcript.get('model', 'N/A')}")
    print(f"  Workflow: {transcript.get('workflow', 'N/A')}")
    print(f"  MCP Optimized: {transcript.get('mcp_optimized', 'N/A')}")
    print(f"  Processing Time: {transcript.get('processing_time_ms', 'N/A')}ms")
    print()

print("=" * 80)
print(f"Total transcripts in database: {collection.count_documents({})}")
print("=" * 80)
