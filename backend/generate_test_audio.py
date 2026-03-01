"""
Generate Real Speech Audio for STT Testing
Uses gTTS (Google Text-to-Speech) to create realistic audio samples
"""

try:
    from gtts import gTTS
    import os
    
    # Test speech samples
    test_speeches = {
        "introduction": {
            "text": "Hello, my name is John Smith. I am a software engineer with five years of experience in Python and machine learning.",
            "filename": "test_intro.mp3"
        },
        "technical": {
            "text": "I have extensive experience with LangGraph, FastAPI, MongoDB, and natural language processing. I've built scalable microservices and RESTful APIs.",
            "filename": "test_technical.mp3"
        },
        "question_answer": {
            "text": "Tell me about a challenging project you worked on. Well, I recently developed an AI-powered recruitment system that uses speech-to-text transcription and sentiment analysis.",
            "filename": "test_qa.mp3"
        }
    }
    
    print("="*60)
    print("Generating Real Speech Audio Samples")
    print("="*60)
    print()
    
    for name, config in test_speeches.items():
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
    print("✓ All audio samples generated successfully!")
    print("="*60)
    print()
    print("Files created:")
    for name, config in test_speeches.items():
        print(f"  - {config['filename']}")
    print()
    
except ImportError:
    print("="*60)
    print("gTTS not installed. Installing...")
    print("="*60)
    print()
    import subprocess
    subprocess.run(["pip", "install", "gtts"], check=True)
    print()
    print("✓ gTTS installed. Please run this script again.")
    print()
