# 🎯 AI Question Generator - Usage Guide

## Overview
The AI Question Generator creates intelligent interview questions based on:
- Candidate's resume (skills, experience, projects)
- Job description (requirements, responsibilities)
- Previous interview performance (adaptive questioning)

---

## 📊 Question Configuration

### **Default Configuration**
```python
Technical Questions:    5 questions
Behavioral Questions:   3 questions
Scenario Questions:     2 questions
-------------------------------------------
Total Default:          10 questions
```

### **Customizable Counts**
You can specify exactly how many questions you want in each category!

---

## 🚀 API Usage

### **Endpoint**
```
POST /api/questions/generate
```

### **Request Body**

#### **Option 1: Use Default Counts (10 total)**
```json
{
  "candidate_id": "candidate_123",
  "job_id": "job_456",
  "interview_id": "interview_789",
  "resume_data": {
    "name": "John Doe",
    "skills": ["Python", "Machine Learning", "TensorFlow"],
    "experience": [
      {
        "title": "ML Engineer",
        "company": "Tech Corp",
        "duration": "3 years"
      }
    ]
  },
  "job_description": {
    "title": "Senior Machine Learning Engineer",
    "requirements": [
      "5+ years Python experience",
      "Deep Learning expertise",
      "MLOps knowledge"
    ],
    "responsibilities": [
      "Build ML models",
      "Deploy to production",
      "Mentor junior engineers"
    ]
  },
  "threshold_percentage": 70.0
}
```

#### **Option 2: Custom Question Counts**
```json
{
  "candidate_id": "candidate_123",
  "job_id": "job_456",
  "interview_id": "interview_789",
  "resume_data": { ... },
  "job_description": { ... },
  "threshold_percentage": 70.0,
  
  // 🎯 CUSTOM COUNTS
  "technical_count": 10,      // Generate 10 technical questions
  "behavioral_count": 5,      // Generate 5 behavioral questions
  "scenario_count": 3         // Generate 3 scenario questions
  // Total: 18 questions
}
```

#### **Option 3: Different Configurations for Different Roles**

**Junior Role (Easy Interview - 8 questions)**
```json
{
  "technical_count": 5,
  "behavioral_count": 2,
  "scenario_count": 1
}
```

**Mid-Level Role (Standard - 10 questions)**
```json
{
  "technical_count": 5,
  "behavioral_count": 3,
  "scenario_count": 2
}
```

**Senior Role (Comprehensive - 15 questions)**
```json
{
  "technical_count": 8,
  "behavioral_count": 4,
  "scenario_count": 3
}
```

**Leadership Role (Behavioral Focus - 12 questions)**
```json
{
  "technical_count": 3,
  "behavioral_count": 7,
  "scenario_count": 2
}
```

---

## 📋 Response Format

```json
{
  "success": true,
  "data": {
    "questions": [
      {
        "question_id": "uuid-1234",
        "question": "Explain the difference between supervised and unsupervised learning",
        "category": "technical",
        "difficulty": "medium",
        "topic": "machine-learning-fundamentals",
        "expected_answer_points": [
          "Supervised learning uses labeled data",
          "Unsupervised learning finds patterns in unlabeled data",
          "Examples: classification vs clustering"
        ],
        "created_at": "2025-10-22T10:30:00Z",
        "interview_id": "interview_789"
      },
      // ... more questions
    ],
    "total_questions": 10,
    "categories": {
      "technical": 5,
      "behavioral": 3,
      "scenario": 2
    },
    "question_set_id": "68f8109f33726b2c4550c585",
    "interview_id": "interview_789"
  },
  "logs": [
    "[2025-10-22T10:30:00] Resume analysis complete",
    "[2025-10-22T10:30:05] Technical questions generated",
    // ... more logs
  ]
}
```

---

## 🎨 Question Types

### **1. Technical Questions**
- Test core technical knowledge
- Assess problem-solving ability
- Evaluate best practices understanding
- Difficulty adjusted based on experience level

**Example:**
```
"Describe how you would implement a recommendation system 
for an e-commerce platform. What algorithms would you consider?"
```

### **2. Behavioral Questions**
- Assess leadership and teamwork
- Evaluate problem-solving approach
- Test conflict resolution skills
- Measure adaptability

**Example:**
```
"Tell me about a time when you had to deliver a project 
under tight deadlines. How did you manage the situation?"
```

### **3. Scenario Questions**
- Present realistic work situations
- Test decision-making under pressure
- Evaluate stakeholder management
- Assess resource optimization

**Example:**
```
"Your ML model performs well in testing but poorly in production. 
The launch is scheduled for next week. What steps would you take?"
```

---

## 🔄 Adaptive Questioning

If the candidate has **previous answers**, the system will:

1. **Analyze Performance**
   - High performance (>80%) → Increase difficulty
   - Medium performance (50-80%) → Maintain level
   - Low performance (<50%) → Simplify or clarify

2. **Generate Follow-ups**
   - Deep-dive into weak areas
   - Advanced questions for strong areas
   - Related concepts for breadth

3. **Adjust Difficulty**
   - Progressive difficulty curve
   - Personalized to candidate's level

**Example with Previous Answers:**
```json
{
  "previous_answers": [
    {
      "question_id": "q1",
      "answer": "Detailed explanation of neural networks...",
      "is_correct": true,
      "score": 0.9
    },
    {
      "question_id": "q2",
      "answer": "Brief answer about optimization...",
      "is_correct": false,
      "score": 0.4
    }
  ]
}
```

**System Response:**
- ✅ Neural networks: Strong → Generate advanced DL question
- ❌ Optimization: Weak → Generate clarifying question

---

## 💡 Best Practices

### **1. Match Question Count to Role Level**
```python
Junior:      5 tech + 2 behavioral + 1 scenario = 8 questions
Mid-Level:   5 tech + 3 behavioral + 2 scenario = 10 questions
Senior:      8 tech + 4 behavioral + 3 scenario = 15 questions
```

### **2. Adjust for Interview Stage**
```python
Phone Screen:    3 tech + 2 behavioral + 0 scenario = 5 questions
Technical Round: 8 tech + 0 behavioral + 2 scenario = 10 questions
Final Round:     2 tech + 5 behavioral + 3 scenario = 10 questions
```

### **3. Balance Question Types**
- **Technical-heavy** (70%): For IC roles
- **Behavioral-heavy** (50%): For management roles
- **Balanced** (50-30-20): For senior IC roles

### **4. Consider Interview Duration**
- **30 min interview**: 5-8 questions
- **45 min interview**: 8-12 questions
- **60 min interview**: 12-15 questions
- **90 min interview**: 15-20 questions

---

## 🧪 Example Usage Scenarios

### **Scenario 1: Quick Phone Screen**
```json
{
  "technical_count": 3,
  "behavioral_count": 2,
  "scenario_count": 0,
  "threshold_percentage": 60.0
}
// Total: 5 questions, 30 minutes
```

### **Scenario 2: Deep Technical Interview**
```json
{
  "technical_count": 12,
  "behavioral_count": 2,
  "scenario_count": 4,
  "threshold_percentage": 75.0
}
// Total: 18 questions, 90 minutes
```

### **Scenario 3: Leadership Assessment**
```json
{
  "technical_count": 2,
  "behavioral_count": 8,
  "scenario_count": 5,
  "threshold_percentage": 70.0
}
// Total: 15 questions, 60 minutes
```

---

## 📈 Question Analytics

After the interview, get analytics:

```
GET /api/questions/analytics/{interview_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_questions": 10,
    "answered_questions": 8,
    "completion_percentage": 80.0,
    "average_score": 0.75,
    "category_breakdown": {
      "technical": {
        "total": 5,
        "answered": 4,
        "avg_score": 0.72
      },
      "behavioral": {
        "total": 3,
        "answered": 3,
        "avg_score": 0.85
      },
      "scenario": {
        "total": 2,
        "answered": 1,
        "avg_score": 0.65
      }
    }
  }
}
```

---

## 🔧 Configuration Tips

### **For HR/Recruiters:**
- Use **default counts** for consistency
- Adjust based on role seniority
- Monitor completion rates

### **For Technical Interviewers:**
- Increase **technical_count** for deep dives
- Add **scenario_count** for practical assessment
- Use adaptive questioning for progressive difficulty

### **For Managers:**
- Increase **behavioral_count** for culture fit
- Use scenarios for decision-making assessment
- Balance technical depth with leadership evaluation

---

## 📞 Support

For questions or issues:
- Check logs in response
- Verify resume_data and job_description format
- Ensure valid candidate_id, job_id, interview_id
- All errors return 200 status with error details

---

## 🎉 Summary

✅ **Flexible**: Configure exactly how many questions you need  
✅ **Adaptive**: Questions adjust based on previous performance  
✅ **Intelligent**: AI generates relevant, role-specific questions  
✅ **Scalable**: Works for junior to executive roles  
✅ **Customizable**: Tailor to your interview process  

**Default: 10 questions (5 + 3 + 2)**  
**Range: 3-50 questions per interview**  
**Recommended: 8-15 questions for 45-60 min interviews**
