"""
Generate Additional Test Audio Samples
Creates 2 more realistic interview audio samples
"""

from gtts import gTTS
import os

# Additional test speeches
additional_speeches = {
    "behavioral": {
        "text": "Describe a time when you faced a difficult challenge at work. I once had to resolve a critical production bug during a live deployment. The system was experiencing high latency due to inefficient database queries. I quickly identified the bottleneck, optimized the queries, and reduced response time by seventy percent.",
        "filename": "test_behavioral.mp3"
    },
    "leadership": {
        "text": "Tell me about your leadership experience. I led a team of five engineers to develop a microservices architecture using Docker and Kubernetes. We implemented continuous integration and continuous deployment pipelines, which improved our deployment frequency by three hundred percent. I mentored junior developers and conducted code reviews to maintain high quality standards.",
        "filename": "test_leadership.mp3"
    }
}

print("="*60)
print("Generating Additional Test Audio Samples")
print("="*60)
print()

for name, config in additional_speeches.items():
    print(f"[{name.upper()}]")
    print(f"  Text: {config['text'][:80]}...")
    print(f"  Generating audio: {config['filename']}")
    
    # Generate speech
    tts = gTTS(text=config['text'], lang='en', slow=False)
    tts.save(config['filename'])
    
    file_size = os.path.getsize(config['filename'])
    print(f"  ✓ Created: {file_size} bytes")
    print()

print("="*60)
print("✓ Additional audio samples generated successfully!")
print("="*60)
print()
print("New files created:")
for name, config in additional_speeches.items():
    print(f"  - {config['filename']}")
print()
print("Now run: .\\test_stt_additional.ps1")
print()
