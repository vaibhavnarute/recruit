from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import spacy
import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import csv
import os
from groq import Groq
from dotenv import load_dotenv
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import uuid

# LangGraph Integration
from langgraph_integration import get_langgraph_service, initialize_langgraph_service

# MongoDB Integration
from db.mongo_client import get_mongo_client, ping_db
from db.models import Collections

# Repository Layer - Data Access
from repositories import (
    UserRepository,
    ResumeRepository,
    JobRepository,
    CandidateRepository,
    AnalysisRepository,
    InterviewRepository,
    EmailRepository,
    QARepository
)

# Service Layer - Business Logic
from services.resume_service import ResumeService

# API Routes
from api.auth_routes import auth_bp

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Accept", "Authorization", "Access-Control-Allow-Origin"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})
app.secret_key = "7743cafca8fe3397f2ae774d70e436c2"

# Register blueprints
app.register_blueprint(auth_bp)

# Initialize Groq client
try:
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        print("Warning: GROQ_API_KEY not found in environment variables")
        groq_api_key = "your_groq_api_key_here"  # Fallback for development
    groq_client = Groq(api_key=groq_api_key)
except Exception as e:
    print(f"Warning: Failed to initialize Groq client: {str(e)}")
    groq_client = None

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Initialize LangGraph service
print("🚀 Initializing LangGraph + MCP service...")
groq_api_key = os.getenv('GROQ_API_KEY')
if groq_api_key:
    initialize_langgraph_service(groq_api_key=groq_api_key)
    print("✅ LangGraph service initialized successfully!")
else:
    print("⚠️ GROQ_API_KEY not found, LangGraph service may not work properly")

# Initialize MongoDB connection
print("🔄 Connecting to MongoDB...")
if ping_db():
    print("✅ MongoDB connected successfully!")
    client = get_mongo_client()
    stats = client.get_stats()
    print(f"📊 Database: {stats.get('database')}")
    print(f"📁 Collections: {stats.get('collections')}")
else:
    print("⚠️ MongoDB connection failed! Application will run without database persistence.")

# Initialize Repositories
user_repo = UserRepository()
resume_repo = ResumeRepository()
job_repo = JobRepository()
candidate_repo = CandidateRepository()
analysis_repo = AnalysisRepository()
interview_repo = InterviewRepository()
email_repo = EmailRepository()
qa_repo = QARepository()

# Initialize Services
resume_service = ResumeService()

print("✅ All repositories and services initialized!")

# Global variable to store processed results (for backward compatibility)
results = []

# Store current job description ID for linking
current_job_id = None

# Add these variables at the top with other configurations
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        # Clean the extracted text
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            print(f"Warning: No text extracted from PDF: {pdf_file.filename}")
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_file.filename}: {str(e)}")
        return ""

def extract_entities(text):
    try:
        # Improved email regex
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        # Improved name regex to catch more variations
        names = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
        if not names:
            # Try to find names in the first few lines
            first_lines = text.split('\n')[:5]
            for line in first_lines:
                names = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', line)
                if names:
                    break
        return emails, names
    except Exception as e:
        print(f"Error extracting entities: {str(e)}")
        return [], []

def anonymize_text(text):
    """Basic anonymization of personal identifiers"""
    # Replace common gender pronouns
    text = re.sub(r'\b(he|him|his|she|her|hers)\b', 'they/them', text, flags=re.IGNORECASE)
    
    # Replace names with "Candidate" (basic implementation)
    names = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    for name in names:
        text = text.replace(name, 'Candidate')
    
    return text

def analyze_resumes(job_description, resumes, threshold=0.8):
    global results, current_job_id
    try:
        print(f"Processing {len(resumes)} resumes with threshold {threshold}")
        print(f"Job description: {job_description[:100]}...")  # Log first 100 chars
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        processed_resumes = []
        resume_ids = []  # Track MongoDB resume IDs
        
        for resume_file in resumes:
            try:
                print(f"Processing resume: {resume_file.filename}")
                resume_path = os.path.join("uploads", resume_file.filename)
                resume_file.save(resume_path)
                
                # Extract text from PDF
                resume_text = extract_text_from_pdf(resume_path)
                if not resume_text:
                    print(f"Warning: No text extracted from {resume_file.filename}")
                    continue
                    
                print(f"Extracted text length: {len(resume_text)} characters")
                
                # Extract entities
                emails, names = extract_entities(resume_text)
                print(f"Extracted entities - Emails: {emails}, Names: {names}")
                
                # 🔥 Save resume to MongoDB using repository
                try:
                    resume_id = resume_repo.save_resume(
                        filename=resume_file.filename,
                        file_path=resume_path,
                        extracted_text=resume_text,
                        candidate_email=emails[0] if emails else None,
                        candidate_name=names[0] if names else "Unknown",
                        job_id=current_job_id
                    )
                    resume_ids.append(resume_id)
                    print(f"✅ Resume saved to MongoDB: {resume_id}")
                except Exception as e:
                    print(f"⚠️ Failed to save resume to MongoDB: {str(e)}")
                    resume_ids.append(None)
                
                processed_resumes.append((names, emails, resume_text, resume_file.filename))
                print(f"Successfully processed resume: {resume_file.filename}")
                
            except Exception as e:
                print(f"Error processing resume {resume_file.filename}: {str(e)}")
                continue

        if not processed_resumes:
            print("No valid resumes processed")
            return {"success": False, "error": "No valid resumes processed"}

        print(f"Successfully processed {len(processed_resumes)} resumes")
        
        # Update job statistics
        if current_job_id:
            job_repo.update_job_statistics(
                job_id=current_job_id,
                total_applications=len(processed_resumes)
            )

        # Create TF-IDF vectors with improved parameters
        tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words='english'
        )
        
        # Transform job description
        try:
            job_desc_vector = tfidf_vectorizer.fit_transform([job_description])
            print("Successfully transformed job description")
        except Exception as e:
            print(f"Error transforming job description: {str(e)}")
            return {"success": False, "error": "Error processing job description"}

        # Process results
        results = []
        selected_count = 0
        rejected_count = 0
        
        for i, (names, emails, resume_text, filename) in enumerate(processed_resumes):
            try:
                # Anonymize the resume text before analysis
                anonymized_text = anonymize_text(resume_text)
                
                # Use structured scoring system (basic implementation)
                structured_score = calculate_structured_score(anonymized_text, job_description)
                
                # Transform resume text
                resume_vector = tfidf_vectorizer.transform([anonymized_text])
                
                # Calculate similarity and convert to float
                similarity = float(cosine_similarity(job_desc_vector, resume_vector)[0][0] * 100)
                print(f"Resume {i+1} similarity: {similarity:.2f}% (threshold: {threshold}%)")
                
                # Combine with existing similarity score for final evaluation
                final_score = (similarity + structured_score) / 2  # Equal weight to both scores
                
                is_selected = bool(final_score >= threshold)
                
                result = {
                    "names": ["Candidate " + str(i+1)],  # Anonymized name
                    "emails": emails,  # Keep email for communication
                    "similarity": round(final_score, 2),
                    "selected": is_selected,
                    "text": anonymized_text,  # Use anonymized text
                    "resume_id": resume_ids[i] if i < len(resume_ids) else None
                }
                results.append(result)
                print(f"Added result for resume {i+1}")
                
                # 🔥 Save analysis result to MongoDB using repository
                try:
                    analysis_id = analysis_repo.save_analysis(
                        resume_id=resume_ids[i] if i < len(resume_ids) else None,
                        job_id=current_job_id,
                        similarity_score=round(similarity, 2),
                        final_score=round(final_score, 2),
                        decision="selected" if is_selected else "rejected",
                        analysis_details={
                            "similarity_score": round(similarity, 2),
                            "structured_score": round(structured_score, 2),
                            "threshold": threshold,
                            "anonymized": True
                        }
                    )
                    print(f"✅ Analysis result saved to MongoDB: {analysis_id}")
                    
                    # 🔥 Add to selected or rejected candidates using repository
                    if is_selected:
                        candidate_id = candidate_repo.add_selected_candidate(
                            resume_id=resume_ids[i] if i < len(resume_ids) else None,
                            job_id=current_job_id,
                            candidate_name=names[0] if names else "Unknown",
                            candidate_email=emails[0] if emails else None,
                            score=round(final_score, 2),
                            notes=f"ATS Score: {final_score:.2f}%"
                        )
                        selected_count += 1
                        print(f"✅ Added to selected candidates: {candidate_id}")
                    else:
                        candidate_id = candidate_repo.add_rejected_candidate(
                            resume_id=resume_ids[i] if i < len(resume_ids) else None,
                            job_id=current_job_id,
                            candidate_name=names[0] if names else "Unknown",
                            candidate_email=emails[0] if emails else None,
                            score=round(final_score, 2),
                            reason=f"ATS score ({final_score:.2f}%) below threshold ({threshold}%)"
                        )
                        rejected_count += 1
                        print(f"✅ Added to rejected candidates: {candidate_id}")
                        
                except Exception as e:
                    print(f"⚠️ Failed to save analysis result to MongoDB: {str(e)}")
                
            except Exception as e:
                print(f"Error processing result for resume {i+1}: {str(e)}")
                continue

        # Update job statistics with final counts
        if current_job_id:
            job_repo.update_job_statistics(
                job_id=current_job_id,
                selected_count=selected_count,
                rejected_count=rejected_count
            )

        # Sort results by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        print(f"Total results found: {len(results)}")
        print(f"✅ Saved {len(results)} analysis results to MongoDB (Selected: {selected_count}, Rejected: {rejected_count})")
        
        if not results:
            print("No results found after processing")
            return {"success": False, "error": "No matching results found"}
            
        return {"success": True, "results": results}
        
    except Exception as e:
        print(f"Error in analyze_resumes: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}

# Add this new function for structured scoring
def calculate_structured_score(resume_text, job_description):
    """
    Basic structured scoring system to reduce bias
    Returns a score between 0-100
    """
    score = 0
    
    # Technical Skills (40 points)
    if re.search(r'python|java|javascript|react|node|sql', resume_text, re.I):
        score += 40
    
    # Experience (30 points)
    years = len(re.findall(r'\d+\s*years?', resume_text, re.I))
    score += min(years * 5, 30)  # Cap at 30 points
    
    # Education (30 points)
    if re.search(r'bachelor|master|phd|degree', resume_text, re.I):
        score += 30
    
    return score

@app.route('/api/analyze', methods=['POST'])
def analyze():
    global current_job_id
    try:
        if 'job_description' not in request.form or 'resume_files' not in request.files:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        job_description = request.form['job_description'].strip()
        if not job_description:
            return jsonify({"success": False, "error": "Job description cannot be empty"}), 400

        resumes = request.files.getlist('resume_files')
        if not resumes:
            return jsonify({"success": False, "error": "No resume files uploaded"}), 400

        threshold = float(request.form.get('threshold', 50))  # Keep as percentage
        if threshold < 0 or threshold > 100:
            return jsonify({"success": False, "error": "Threshold must be between 0 and 100"}), 400

        # 🔥 Save job description to MongoDB
        print("💾 Saving job description to MongoDB...")
        current_job_id = job_repo.create_job(
            title=f"Job Posting - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description=job_description,
            requirements=[],
            skills_required=[],
            experience_min=0,
            experience_max=10,
            threshold=threshold / 100.0  # Convert percentage to decimal
        )
        print(f"✅ Job saved with ID: {current_job_id}")

        result = analyze_resumes(job_description, resumes, threshold)
        return jsonify(result)
    except Exception as e:
        print(f"Error in /api/analyze: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate-message', methods=['POST'])
def generate_message():
    try:
        action = request.form.get('action')
        job_description = request.form.get('job_description')
        candidates = json.loads(request.form.get('candidates', '[]'))
        
        if not action or not job_description:
            return jsonify({'success': False, 'error': 'Missing required parameters'})

        # Prepare the prompt based on action and candidates
        if action == 'accept':
            prompt = f"""Generate a professional acceptance email for the following candidates:
Job Description: {job_description}

Selected Candidates:
{chr(10).join([f"- {c['name']} (Email: {c['email']}, ATS Score: {c['similarity']:.2f}%)" for c in candidates])}

Generate a professional acceptance email that:
1. Congratulates the candidates
2. Mentions their strong qualifications
3. Includes interview details:
   - Interview Link: https://ac05-150-107-16-112.ngrok-free.app/room/swarup
   - Interview Timing: [Please select a suitable time slot]
4. Maintains a professional tone
5. Is personalized but not overly specific
6. IMPORTANT: Only include the interview link once in the message

Email:"""
        else:  # reject
            prompt = f"""Generate a professional rejection email for candidates who did not meet the requirements:
Job Description: {job_description}

Generate a professional rejection email that:
1. Thanks the candidates for their interest
2. Is polite and constructive
3. Encourages future applications
4. Maintains a professional tone
5. Is generic enough to be used for multiple candidates

Email:"""

        # Call Groq API directly
        response = groq_client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[
                {"role": "system", "content": "You are a professional HR assistant. Generate clear, concise, and professional emails. Make sure to include the interview link only once in the message."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        generated_message = response.choices[0].message.content.strip()
        
        return jsonify({
            'success': True,
            'generated_message': generated_message
        })

    except Exception as e:
        print(f"Error generating message: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/process-action', methods=['POST'])
def process_action():
    global results
    try:
        action = request.form.get('action')
        custom_message = request.form.get('custom_message', '')
        indices_str = request.form.getlist('selected_resume')
        
        # Validate required parameters
        if not action:
            return jsonify({"success": False, "error": "Action parameter is required"}), 400
            
        # Convert indices to integers safely
        selected_indices = []
        for idx in indices_str:
            try:
                selected_indices.append(int(idx))
            except ValueError:
                return jsonify({"success": False, "error": f"Invalid index value: {idx}"}), 400
        
        # Validate indices are within bounds
        if results and any(idx >= len(results) for idx in selected_indices):
            return jsonify({"success": False, "error": "One or more selected indices are out of range"}), 400
        
        if action == 'reject':
            all_indices = list(range(len(results)))
            target_indices = [idx for idx in all_indices if idx not in selected_indices]
        else:
            target_indices = selected_indices

        if not target_indices:
            return jsonify({"success": False, "error": f"No resumes targeted for {action} action"}), 400
        
        final_msg = ""
        if action == 'accept':
            final_msg += "Acceptance Message:\n"
        else:
            final_msg += "Rejection Message:\n"
        final_msg += custom_message + "\n"
        
        for idx in target_indices:
            if idx < len(results):
                resume = results[idx]
                name = resume["names"][0] if resume["names"] else "N/A"
                email = resume["emails"][0] if resume["emails"] else "N/A"
                final_msg += f"\nCandidate: {name}, Email: {email}"
        
        return jsonify({"success": True, "msg": final_msg})
    except Exception as e:
        print(f"Error in /api/process-action: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download-csv')
def download_csv():
    global results
    try:
        csv_content = "Rank,Name,Email,Similarity\n"
        for rank, resume in enumerate(results, start=1):
            name = resume["names"][0] if resume["names"] else "N/A"
            email = resume["emails"][0] if resume["emails"] else "N/A"
            similarity = resume["similarity"]
            csv_content += f"{rank},{name},{email},{similarity}\n"
        
        csv_filename = "ranked_resumes.csv"
        with open(csv_filename, "w") as csv_file:
            csv_file.write(csv_content)
        
        return send_file(csv_filename, as_attachment=True, download_name="ranked_resumes.csv")
    except Exception as e:
        print(f"Error in /api/download-csv: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/test-extraction', methods=['POST'])
def test_extraction():
    try:
        if 'resume_file' not in request.files:
            return jsonify({"success": False, "error": "No resume file uploaded"}), 400

        resume = request.files['resume_file']
        text = extract_text_from_pdf(resume)
        emails, names = extract_entities(text)

        return jsonify({
            "success": True,
            "data": {
                "text_length": len(text),
                "text_preview": text[:500] + "..." if len(text) > 500 else text,
                "emails": emails,
                "names": names
            }
        })
    except Exception as e:
        print(f"Error in test-extraction: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/test-similarity', methods=['POST'])
def test_similarity():
    try:
        if 'text1' not in request.form or 'text2' not in request.form:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        text1 = request.form['text1']
        text2 = request.form['text2']

        vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words='english'
        )
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0][0]

        return jsonify({
            "success": True,
            "data": {
                "similarity": float(similarity),
                "similarity_percentage": round(similarity * 100, 2)
            }
        })
    except Exception as e:
        print(f"Error in test-similarity: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

def send_email(to_email: str, subject: str, body: str, attachment_path: str = None):
    try:
        print(f"Setting up email to: {to_email}")
        print(f"Using SMTP settings:")
        print(f"Server: {SMTP_SERVER}")
        print(f"Port: {SMTP_PORT}")
        print(f"Username: {SMTP_USERNAME}")
        print(f"Sender: {SENDER_EMAIL}")
        
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(attachment)

        print("Connecting to SMTP server...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            print("Logging in to SMTP server...")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print("Sending email...")
            server.send_message(msg)
            print("Email sent successfully!")

        return True, "Email sent successfully"
    except Exception as e:
        print(f"Error in send_email: {str(e)}")
        return False, str(e)

@app.route('/api/send-emails', methods=['POST'])
def send_emails():
    try:
        data = request.get_json()
        action = data.get('action')
        message = data.get('message')
        selected_emails = data.get('selected_emails', [])
        rejected_emails = data.get('rejected_emails', [])
        subject = data.get('subject', "Application Status Update")
        
        print(f"Received email request:")
        print(f"Action: {action}")
        print(f"Subject: {subject}")
        print(f"Selected emails: {selected_emails}")
        print(f"Rejected emails: {rejected_emails}")
        
        if not action or not message:
            return jsonify({'success': False, 'error': 'Missing required parameters'})

        results = []
        
        # Send emails to selected candidates
        for email in selected_emails:
            print(f"Attempting to send email to: {email}")
            success, msg = send_email(
                email,
                subject,
                message
            )
            print(f"Email send result for {email}: Success={success}, Message={msg}")
            results.append({
                'email': email,
                'success': success,
                'message': msg
            })
            
            # 🔥 Log email to MongoDB using repository
            try:
                email_repo.log_email(
                    recipient_email=email,
                    recipient_name="Candidate",
                    subject=subject,
                    body=message,
                    email_type="selection",
                    job_id=current_job_id,
                    status="sent" if success else "failed"
                )
                print(f"✅ Email logged to MongoDB for {email}")
            except Exception as e:
                print(f"⚠️ Failed to log email to MongoDB: {str(e)}")

        # Send emails to rejected candidates
        for email in rejected_emails:
            print(f"Attempting to send email to: {email}")
            success, msg = send_email(
                email,
                subject,
                message
            )
            print(f"Email send result for {email}: Success={success}, Message={msg}")
            results.append({
                'email': email,
                'success': success,
                'message': msg
            })
            
            # Log email to MongoDB
            try:
                log_email(
                    job_id=current_job_id,
                    recipient_email=email,
                    subject=subject,
                    body=message,
                    status="sent" if success else "failed",
                    email_type="rejection",
                    error_message=None if success else msg
                )
                print(f"✅ Email logged to MongoDB for {email}")
            except Exception as e:
                print(f"⚠️ Failed to log email to MongoDB: {str(e)}")

        print(f"✅ Sent and logged {len(results)} emails to MongoDB")

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        print(f"Error sending emails: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/qa', methods=['POST'])
def qa():
    """
    Answer questions about a resume using LangGraph Q&A workflow.
    
    NEW: Uses LangGraph + MCP for:
    - Question classification (skills/experience/education/general)
    - Selective retrieval (only relevant sections, 75%+ token savings)
    - Intelligent caching (repeated questions answered instantly)
    - Conversation history management
    """
    try:
        data = request.get_json()
        if not data or 'question' not in data or 'resume_text' not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        question = data['question']
        resume_text = data['resume_text']
        session_id = data.get('session_id')  # Optional session ID for tracking
        
        print(f"❓ Received Q&A request: {question[:50]}...")
        print(f"✅ Resume text length: {len(resume_text)} characters")

        # Use LangGraph service for Q&A
        service = get_langgraph_service()
        result = service.answer_question(
            resume_text=resume_text,
            question=question
        )
        
        # Extract the answer from the result
        answer = result.get('answer', '')
        
        print(f"✅ Question answered successfully")
        print(f"📊 Performance: Cache hit rate: {result.get('metadata', {}).get('cache_hit_rate', 'N/A')}")
        print(f"💰 Tokens saved: {result.get('metadata', {}).get('tokens_saved', 0)}")

        # Clean up the response
        if answer.lower().startswith('answer:'):
            answer = answer[7:].strip()
        
        # Save Q&A session to MongoDB
        try:
            # Create or get session
            if not session_id:
                session_id = create_qa_session(
                    room_id="web_qa_" + str(uuid.uuid4())[:8],
                    candidate_name="Web User",
                    job_role="Resume Review"
                )
                print(f"✅ Created new Q&A session: {session_id}")
            
            # Add question and answer to session
            add_qa_question(
                session_id=session_id,
                question=question,
                answer=answer,
                question_type="resume_analysis",
                metadata=result.get('metadata', {})
            )
            print(f"✅ Q&A logged to MongoDB session: {session_id}")
        except Exception as e:
            print(f"⚠️ Failed to log Q&A to MongoDB: {str(e)}")
            session_id = None
        
        return jsonify({
            'success': True,
            'answer': answer,
            'session_id': session_id
        })

    except Exception as e:
        print(f"❌ Error in qa endpoint: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/predict-salary', methods=['POST'])
def predict_salary():
    """
    Predict salary using ML model + LangGraph workflow.
    
    Uses trained XGBoost models for accurate salary predictions.
    """
    try:
        data = request.form
        
        # Get and validate required fields
        years_experience_str = data.get('years_experience')
        education_level = data.get('education_level')
        job_level = data.get('job_level')
        industry = data.get('industry')
        location = data.get('location')
        
        if not all([years_experience_str, education_level, job_level, industry, location]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        years_experience = float(years_experience_str)
        
        print(f"💰 Received salary prediction request")
        print(f"📊 Params: {years_experience}y exp, {education_level}, {job_level}, {industry}, {location}")
        
        # Validate inputs
        if years_experience < 0:
            return jsonify({'error': 'Years of experience cannot be negative'}), 400
        
        valid_education = ['High School', 'Associate', 'Bachelor', 'Master', 'PhD']
        if education_level not in valid_education:
            return jsonify({'error': f'Invalid education level. Must be one of: {", ".join(valid_education)}'}), 400
        
        valid_job_levels = ['Entry-level', 'Mid-level', 'Senior', 'Executive']
        if job_level not in valid_job_levels:
            return jsonify({'error': f'Invalid job level. Must be one of: {", ".join(valid_job_levels)}'}), 400
        
        valid_locations = ['Urban', 'Suburban', 'Rural']
        if location not in valid_locations:
            return jsonify({'error': f'Invalid location. Must be one of: {", ".join(valid_locations)}'}), 400
        
        # Use LangGraph service for ML prediction
        service = get_langgraph_service()
        result = service.predict_salary(
            years_experience=years_experience,
            education_level=education_level,
            job_level=job_level,
            industry=industry,
            location=location
        )
        
        print(f"✅ Salary prediction complete: ${result['predicted_salary']:,.2f}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in salary prediction: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/predict-job-possibility', methods=['POST'])
def predict_job_possibility():
    """
    Predict job possibility using ML model + LangGraph workflow.
    
    Uses trained XGBoost models to predict job acquisition probability.
    """
    try:
        data = request.form
        
        # Get and validate required fields
        years_experience_str = data.get('years_experience')
        education_level_str = data.get('education_level')
        job_level_str = data.get('job_level')
        industry_str = data.get('industry')
        skill_match_score_str = data.get('skill_match_score')
        
        if not all([years_experience_str, education_level_str, job_level_str, industry_str, skill_match_score_str]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        years_experience = float(years_experience_str)
        education_level = str(education_level_str)
        job_level = str(job_level_str)
        industry = str(industry_str)
        skill_match_score = float(skill_match_score_str)
        
        print(f"🎯 Received job possibility prediction request")
        print(f"📊 Params: {years_experience}y exp, {education_level}, {job_level}, {industry}, skill_match={skill_match_score:.2f}")
        
        # Validate inputs
        if years_experience < 0:
            return jsonify({'error': 'Years of experience cannot be negative'}), 400
        
        if not (0 <= skill_match_score <= 1):
            return jsonify({'error': 'Skill match score must be between 0 and 1'}), 400
        
        valid_education = ['High School', 'Associate', 'Bachelor', 'Master', 'PhD']
        if education_level not in valid_education:
            return jsonify({'error': f'Invalid education level. Must be one of: {", ".join(valid_education)}'}), 400
        
        valid_job_levels = ['Entry-level', 'Mid-level', 'Senior', 'Executive']
        if job_level not in valid_job_levels:
            return jsonify({'error': f'Invalid job level. Must be one of: {", ".join(valid_job_levels)}'}), 400
        
        # Use LangGraph service for ML prediction
        service = get_langgraph_service()
        result = service.predict_job_possibility(
            years_experience=years_experience,
            education_level=education_level,
            job_level=job_level,
            industry=industry,
            skill_match_score=skill_match_score
        )
        
        print(f"✅ Job possibility prediction complete: {result['probability']:.2%}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in job possibility prediction: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/interview/<roomid>')
def interview_room(roomid):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Interview</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://unpkg.com/@zegocloud/zego-uikit-prebuilt@1.0.0/zego-uikit-prebuilt.js"></script>
        <style>
            #root {
                width: 100vw;
                height: 100vh;
            }
            body {
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
        </style>
    </head>
    <body>
        <div id="root"></div>
        <script>
            const roomID = window.location.pathname.split('/').pop();
            const zp = ZegoUIKitPrebuilt.create({
                appID: 2128937685,
                serverSecret: "cdbd6af0aaa52e5a222272f8553195c5",
                roomID: roomID,
                userID: 'user_' + Math.floor(Math.random() * 10000),
                userName: 'User_' + Math.floor(Math.random() * 10000),
                container: document.querySelector("#root"),
                scenario: {
                    mode: ZegoUIKitPrebuilt.OneONoneCall,
                },
            });
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5000) 