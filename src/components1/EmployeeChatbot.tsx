import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { extractTextFromPdf } from './ResumeAnalysis';
import { API_ENDPOINTS } from '@/config/api';
import { ResumeQA } from './ResumeQA';
import { InterviewQuestions } from './InterviewQuestions';
import ResumeImprovement from './ResumeImprovement';
import JobPrediction from './JobPrediction';
import SkillGapAnalysis from './SkillGapAnalysis';
import CareerPath from './CareerPath';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import Spinner from "@/components/ui/spinner";
import StartAnimation from '@/components/ui/StartAnimation';
import ParticleBackground from '@/components/ui/ParticleBackground';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { detectIntent } from '@/services/intentDetection';

interface Message {
  type: 'user' | 'ai';
  content: string;
}

interface EmployeeChatbotProps {
  onSelectFunction: (functionName: string) => void;
}

interface Question {
  type: string;
  difficulty: string;
  question: string;
}

const IT_ROLES = [
  'AI/ML Engineer',
  'Frontend Engineer',
  'Backend Engineer',
  'Full Stack Engineer',
  'DevOps Engineer',
  'Data Engineer',
  'Data Scientist',
  'Product Manager',
  'UX Designer',
  'UI Developer'
];

const ROLE_REQUIREMENTS: { [key: string]: string[] } = {
  'AI/ML Engineer': [
    'Python',
    'Machine Learning',
    'Deep Learning',
    'TensorFlow/PyTorch',
    'Data Analysis',
    'Statistics',
    'MLOps',
    'Big Data'
  ],
  'Frontend Engineer': [
    'React',
    'JavaScript',
    'HTML/CSS',
    'TypeScript',
    'State Management',
    'Responsive Design',
    'Web Performance',
    'UI/UX Principles'
  ],
  'Backend Engineer': [
    'Node.js',
    'Python',
    'Java',
    'SQL',
    'REST APIs',
    'Microservices',
    'Database Design',
    'System Architecture'
  ],
  'Full Stack Engineer': [
    'Frontend Development',
    'Backend Development',
    'Database Management',
    'API Design',
    'System Architecture',
    'DevOps Practices',
    'Testing',
    'Security'
  ],
  'DevOps Engineer': [
    'CI/CD',
    'Docker',
    'Kubernetes',
    'AWS/Azure/GCP',
    'Infrastructure as Code',
    'Monitoring',
    'Logging',
    'Security'
  ],
  'Data Engineer': [
    'Python',
    'SQL',
    'ETL',
    'Data Warehousing',
    'Big Data',
    'Data Modeling',
    'Data Pipeline',
    'Data Quality'
  ],
  'Data Scientist': [
    'Python',
    'Machine Learning',
    'Statistics',
    'Data Analysis',
    'SQL',
    'Data Visualization',
    'Deep Learning',
    'Big Data'
  ],
  'Product Manager': [
    'Product Strategy',
    'Market Research',
    'User Stories',
    'Agile',
    'Analytics',
    'Stakeholder Management',
    'Roadmap Planning',
    'Product Metrics'
  ],
  'UX Designer': [
    'User Research',
    'Wireframing',
    'Prototyping',
    'Visual Design',
    'Interaction Design',
    'Design Systems',
    'Accessibility',
    'User Testing'
  ],
  'UI Developer': [
    'HTML/CSS',
    'JavaScript',
    'React',
    'UI Components',
    'Responsive Design',
    'Cross-browser',
    'Performance',
    'Accessibility'
  ]
};

const API_ENDPOINTS_WITH_CAREERPATH = {
  ...API_ENDPOINTS,
  careerpath: '/api/careerpath'
};

const EmployeeChatbot: React.FC<EmployeeChatbotProps> = ({ onSelectFunction }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedFunction, setSelectedFunction] = useState<string | null>(null);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState<string>(''); // Store extracted text
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [experience, setExperience] = useState('');
  const [skills, setSkills] = useState('');
  const [currentRole, setCurrentRole] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [difficulty, setDifficulty] = useState('easy');
  const [numQuestions, setNumQuestions] = useState('5');
  const [questionTypes, setQuestionTypes] = useState(['technical', 'behavioral']);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [improvedResume, setImprovedResume] = useState<string | null>(null);
  const [education, setEducation] = useState('');
  const [jobLevel, setJobLevel] = useState('');
  const [industry, setIndustry] = useState('');
  const [location, setLocation] = useState('');
  const [showChatbot, setShowChatbot] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (showChatbot) {
      setMessages([{
        type: 'ai',
        content: 'Hello! I can help you with various resume-related tasks. Please select a function:'
      }]);
    }
  }, [showChatbot]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }
    if (!inputMessage.trim() || isProcessing) return;

    // Add user message to chat
    setMessages(prev => [...prev, { type: 'user', content: inputMessage }]);
    setInputMessage('');
    setIsProcessing(true);

    try {
      // Detect intent from user input
      const { intent, response } = await detectIntent(inputMessage);
      
      // Add AI response to chat
      setMessages(prev => [...prev, { type: 'ai', content: response }]);

      // If intent is detected with high confidence, automatically select the feature
      if (intent) {
        // Map intent to function name
        const functionMap: { [key: string]: string } = {
          'resume_analysis': 'analysis',
          'resume_qa': 'qa',
          'interview_questions': 'questions',
          'resume_improvement': 'improved-resume',
          'salary_prediction': 'skillgap'
        };

        const functionName = functionMap[intent];
        if (functionName) {
          handleFunctionSelect(functionName);
        }
      }
    } catch (error) {
      console.error('Error processing message:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: "I'm having trouble understanding your request. Please try again or select a feature from the buttons above."
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFunctionSelect = (functionName: string) => {
    if (selectedFunction === functionName) return; // Prevent duplicate selections
    
    setSelectedFunction(functionName);
    onSelectFunction(functionName);
    
    // If switching to improvement or improved-resume, copy job description from analysis
    if ((functionName === 'improvement' || functionName === 'improved-resume') && jobDescription) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Using job description from Resume Analysis.'
      }]);
    }
    
    // Add function selection message to chat
    setMessages(prev => [...prev, {
      type: 'user',
      content: `Selected function: ${functionName === 'skillgap' ? 'salary' : functionName}`
    }]);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setResumeFile(file);
      setResumeText(''); // Clear stored text when new file is uploaded
      const url = URL.createObjectURL(file);
      setPdfUrl(url);
    }
  };

  React.useEffect(() => {
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const handleAnalyzeResume = async () => {
    if (!resumeFile || !jobTitle || !jobDescription) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please provide all required information: resume file, job title, and job description.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'user',
      content: `Analyzing resume for ${jobTitle} position`
    }]);

    try {
      // Extract text from PDF once and store it for Q&A (non-blocking)
      if (!resumeText) {
        try {
          const extractedText = await extractTextFromPdf(resumeFile);
          setResumeText(extractedText);
          console.log('✅ Resume text extracted and stored for Q&A:', extractedText.length, 'characters');
        } catch (extractError) {
          console.warn('⚠️ Frontend PDF extraction failed (will extract on backend):', extractError);
          // Don't throw error - backend will extract the PDF for analysis
          // We'll try to extract again when Q&A is used
        }
      }

      const formData = new FormData();
      formData.append('resume', resumeFile);
      formData.append('job_description', jobDescription);
      formData.append('job_title', jobTitle);

      const response = await fetch(API_ENDPOINTS.analyze, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.[0]?.msg || errorData.error || `Server responded with status ${response.status}`);
      }

      const data = await response.json();
      
      const analysisResult = `
Resume Analysis Results:
------------------------
Match Score: ${data.match_score}%

Matching Skills:
${data.matching_skills.map((skill: string) => `- ${skill}`).join('\n')}

Missing Skills:
${data.missing_skills.map((skill: string) => `- ${skill}`).join('\n')}

Strengths:
${data.strengths.map((strength: string) => `- ${strength}`).join('\n')}

Areas for Improvement:
${data.areas_for_improvement.map((area: string) => `- ${area}`).join('\n')}
      `;

      setMessages(prev => [...prev, {
        type: 'ai',
        content: analysisResult
      }]);
    } catch (error) {
      console.error('Analysis error:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error analyzing resume: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleQASubmit = async () => {
    if (!resumeFile || !question) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please provide both resume and question.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'user',
      content: `Question: ${question}`
    }]);

    try {
      // Use stored resume text or extract if not available
      let textToUse = resumeText;
      let sendFile = false;
      
      if (!textToUse) {
        console.log('⚠️ Resume text not found in state, attempting to extract from PDF...');
        try {
          textToUse = await extractTextFromPdf(resumeFile);
          setResumeText(textToUse);
          console.log('✅ Resume text extracted successfully:', textToUse.length, 'characters');
        } catch (extractError) {
          console.warn('⚠️ Frontend extraction failed, will send PDF to backend:', extractError);
          // Instead of throwing error, we'll send the file to backend
          sendFile = true;
        }
      } else {
        console.log('✅ Using stored resume text:', textToUse.length, 'characters');
      }

      const formData = new FormData();
      
      if (sendFile) {
        // Backend will extract the PDF
        formData.append('resume_file', resumeFile);
        console.log('📤 Sending PDF file to backend for extraction');
      } else {
        // Use the extracted text
        formData.append('resume_text', textToUse);
      }
      
      formData.append('question', question);

      const response = await fetch(API_ENDPOINTS.qa, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.[0]?.msg || errorData.error || `Server responded with status ${response.status}`);
      }

      const data = await response.json();
      
      // Format the answer if it's an array of bullet points
      const formattedAnswer = Array.isArray(data.answer) 
        ? data.answer.join('\n')
        : data.answer || 'I apologize, but I could not generate an answer for your question. Please try rephrasing your question.';

      setMessages(prev => [...prev, {
        type: 'ai',
        content: formattedAnswer
      }]);
    } catch (error) {
      console.error('Q&A error:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error processing question: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
      setQuestion(''); // Clear the question input after submission
    }
  };

  const handleInterviewQuestions = async () => {
    if (!resumeFile) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please upload a resume first.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'user',
      content: `Generating ${numQuestions} ${difficulty} interview questions (${questionTypes.join(', ')})`
    }]);

    try {
      const formData = new FormData();
      formData.append('resume', resumeFile);
      formData.append('difficulty', difficulty);
      formData.append('num_questions', numQuestions);
      formData.append('question_types', JSON.stringify(questionTypes));

      const response = await fetch(API_ENDPOINTS.questions, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.[0]?.msg || errorData.error || `Server responded with status ${response.status}`);
      }

      const data = await response.json();
      
      // Format the questions for display
      const formattedQuestions = data.questions.map((q: Question, index: number) => `
Question ${index + 1} (${q.type}, ${q.difficulty}):
${q.question}
      `).join('\n');

      setMessages(prev => [...prev, {
        type: 'ai',
        content: formattedQuestions
      }]);
    } catch (error) {
      console.error('Questions generation error:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error generating questions: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleImprovement = async () => {
    if (!resumeFile || !targetRole) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please provide both a resume and select a target role to get improvement suggestions.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'ai',
      content: 'Analyzing your resume and generating improvement suggestions...'
    }]);

    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('target_role', targetRole);

    try {
      console.log('=== Improvement Request Debug ===');
      console.log('1. Request Details:');
      console.log('   - Resume File:', resumeFile.name, 'Size:', resumeFile.size);
      console.log('   - Target Role:', targetRole);
      console.log('   - API Endpoint:', API_ENDPOINTS.improve);
      
      console.log('\n2. FormData Contents:');
      for (const pair of formData.entries()) {
        console.log('   -', pair[0] + ':', pair[1]);
      }

      console.log('\n3. Sending Request...');
      const response = await fetch(API_ENDPOINTS.improve, {
        method: 'POST',
        body: formData
      });

      console.log('\n4. Response Details:');
      console.log('   - Status:', response.status);
      console.log('   - Status Text:', response.statusText);
      console.log('   - Headers:', Object.fromEntries(response.headers.entries()));
      
      const responseText = await response.text();
      console.log('\n5. Raw Response Text:', responseText);

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      // Handle empty response
      if (!responseText.trim()) {
        throw new Error('Server returned an empty response');
      }

      let data;
      try {
        data = JSON.parse(responseText);
        console.log('\n6. Parsed Response Data:', data);
      } catch (e) {
        console.error('\n6. JSON Parse Error:', e);
        throw new Error('Invalid response format from server');
      }

      if (data.suggestions && Array.isArray(data.suggestions)) {
        const formattedMessage = `Resume Improvement Analysis for ${targetRole}:\n\n` +
          data.suggestions.map(suggestion => {
            // Ensure example is always a string and doesn't contain JSON syntax
            let exampleText = '';
            if (suggestion.example) {
              if (typeof suggestion.example === 'string') {
                exampleText = suggestion.example;
                
                // Note: Removed JSON syntax detection to allow natural language with commas
                // Examples can now include commas naturally without being flagged as JSON
              } else if (typeof suggestion.example === 'object') {
                // If it's an object, try to extract meaningful content
                console.warn('Warning: example is an object, converting to string:', suggestion.example);
                if (suggestion.example.description) {
                  exampleText = suggestion.example.description;
                } else if (suggestion.example.text) {
                  exampleText = suggestion.example.text;
                } else {
                  // Generate a fallback instead of stringifying JSON
                  exampleText = `As a ${targetRole}, I gained expertise in ${suggestion.area} through practical application and professional development.`;
                }
              } else {
                // Convert any other type to string
                exampleText = String(suggestion.example);
              }
            }
            
            return `${suggestion.area}:\n` +
              `Suggestions:\n` +
              suggestion.suggestions.map(s => `• ${s}`).join('\n') +
              (exampleText ? `\n\nExample:\n${exampleText}` : '') +
              '\n';
          }).join('\n');

        setMessages(prev => [...prev, {
          type: 'ai',
          content: formattedMessage
        }]);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        console.error('\n7. Unexpected Response Structure:', data);
        throw new Error('Received data in unexpected format');
      }
    } catch (error) {
      console.error('\n8. Error Details:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error generating improvement suggestions: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleResumeImprovement = async () => {
    if (!resumeFile || !targetRole || !jobDescription) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please provide both a resume and select a target role to get improvement suggestions.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'ai',
      content: 'Analyzing your resume and generating improvement suggestions...'
    }]);

    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('target_role', targetRole);
    formData.append('highlight_skills', JSON.stringify(selectedSkills));

    if (jobDescription) {
      formData.append('job_description', jobDescription);
    }

    try {
      console.log('Sending improved resume request with:', {
        hasResumeFile: !!resumeFile,
        targetRole: targetRole,
        selectedSkills,
        hasJobDescription: !!jobDescription
      });

      const response = await fetch(API_ENDPOINTS.improvedResume, {
        method: 'POST',
        body: formData
      });

      console.log('Response status:', response.status);
      const responseText = await response.text();
      console.log('Raw response:', responseText);

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      let data;
      try {
        data = JSON.parse(responseText);
      } catch (e) {
        console.error('Failed to parse JSON:', e);
        throw new Error('Invalid response format from server');
      }

      console.log("Parsed improved resume data:", data);
      
      if (data.improved_resume) {
        setImprovedResume(data.improved_resume);
        const formattedMessage = `
Improved Resume Generated:
------------------------
Your resume has been improved to better target the ${targetRole} position.

${selectedSkills.length > 0 ? `Selected skills to highlight: ${selectedSkills.join(', ')}` : ''}
${jobDescription ? `Based on job description: ${jobDescription}` : ''}

Improved Resume Content:
----------------------
${data.improved_resume}

You can now download the improved resume content.
        `;

        setMessages(prev => [...prev, {
          type: 'ai',
          content: formattedMessage
        }]);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        console.error("Unexpected response structure:", data);
        throw new Error('Received data in unexpected format');
      }
    } catch (error) {
      console.error('Improved resume error:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error generating improved resume: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownloadImprovedResume = () => {
    if (!improvedResume) return;

    const blob = new Blob([improvedResume], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `improved_resume_${targetRole.toLowerCase().replace(/\s+/g, '_')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleJobPrediction = async () => {
    if (!experience || !skills || !education || !jobLevel || !industry) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please provide all required information: years of experience, skill match score, education level, job level, and industry.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'user',
      content: 'Predicting job possibility based on provided information'
    }]);

    try {
      // Convert string values to numbers for validation
      const years_experience = parseFloat(experience);
      const skill_match_score = parseFloat(skills);
      
      if (isNaN(years_experience) || isNaN(skill_match_score)) {
        throw new Error('Please enter valid numeric values');
      }
      
      if (skill_match_score < 0 || skill_match_score > 1) {
        throw new Error('Skill match score must be between 0 and 1');
      }

      // Call backend ML prediction API
      const formData = new FormData();
      formData.append('years_experience', years_experience.toString());
      formData.append('education_level', education);
      formData.append('job_level', jobLevel);
      formData.append('industry', industry);
      formData.append('skill_match_score', skill_match_score.toString());

      const response = await fetch(API_ENDPOINTS.predictJobPossibility, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.error) {
        throw new Error(result.error);
      }

      // Extract results from ML model prediction
      const { probability, recommended, confidence, feature_importance } = result;
      
      const recommendation = recommended 
        ? "Candidate is recommended for the position" 
        : "Candidate is not recommended for the position";

      // Format feature importance for display
      const featureImportanceText = Object.entries(feature_importance)
        .map(([feature, importance]) => `  ${feature}: ${importance}%`)
        .join('\n');

      const formattedMessage = `
Job Possibility Prediction Results:
--------------------------------
${recommendation}

Probability: ${(probability * 100).toFixed(2)}%
Model Confidence: ${(confidence * 100).toFixed(2)}%

Candidate Details:
----------------
Years of Experience: ${years_experience}
Skill Match Score: ${skill_match_score}
Education Level: ${education}
Job Level: ${jobLevel}
Industry: ${industry}

Feature Importance:
------------------
${featureImportanceText}

✨ Prediction powered by XGBoost ML model
      `;

      setMessages(prev => [...prev, {
        type: 'ai',
        content: formattedMessage
      }]);
    } catch (error) {
      console.error('Prediction error:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error predicting job possibility: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSkillGapAnalysis = async () => {
    if (!experience || !education || !jobLevel || !industry || !location) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please provide all required information: years of experience, education level, job level, industry, and location.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'user',
      content: 'Predicting salary based on provided information'
    }]);

    try {
      // Convert string values to numbers for validation
      const years_experience = parseFloat(experience);
      
      if (isNaN(years_experience) || years_experience < 0) {
        throw new Error('Please enter a valid positive number for years of experience');
      }

      // Call backend ML prediction API
      const formData = new FormData();
      formData.append('years_experience', years_experience.toString());
      formData.append('education_level', education);
      formData.append('job_level', jobLevel);
      formData.append('industry', industry);
      formData.append('location', location);

      const response = await fetch(API_ENDPOINTS.predictSalary, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.error) {
        throw new Error(result.error);
      }

      // Extract results from ML model prediction
      const { predicted_salary, confidence, feature_importance } = result;
      
      // Format salary for display
      const formatted_salary = `$${predicted_salary.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      // Format feature importance for display
      const featureImportanceText = Object.entries(feature_importance)
        .map(([feature, importance]) => `  ${feature}: ${importance}%`)
        .join('\n');

      const formattedMessage = `
Salary Prediction Results:
------------------------
Predicted Annual Salary: ${formatted_salary}
Model Confidence: ${(confidence * 100).toFixed(2)}%

Candidate Details:
----------------
Years of Experience: ${years_experience}
Education Level: ${education}
Job Level: ${jobLevel}
Industry: ${industry}
Location: ${location}

Feature Importance:
------------------
${featureImportanceText}

✨ Prediction powered by XGBoost ML model
      `;

      setMessages(prev => [...prev, {
        type: 'ai',
        content: formattedMessage
      }]);
    } catch (error) {
      console.error('Salary prediction error:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error predicting salary: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCareerPath = async () => {
    if (!currentRole || !targetRole) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please provide both current and target roles.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'user',
      content: `Generating career path from ${currentRole} to ${targetRole}`
    }]);

    try {
      const response = await fetch(API_ENDPOINTS_WITH_CAREERPATH.careerpath, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_role: currentRole,
          target_role: targetRole
        }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      const data = await response.json();
      setMessages(prev => [...prev, {
        type: 'ai',
        content: data.path
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error generating career path: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderResumeUpload = () => {
    return (
      <div className="space-y-4">
        <div>
          <label className="text-white mb-2 block">Upload Resume</label>
          <Input 
            type="file" 
            accept=".pdf" 
            className="text-white"
            onChange={handleFileChange}
          />
        </div>
        {resumeFile && (
          <div>
            <p className="text-white mb-2">Current Resume:</p>
            <p className="text-white text-sm bg-primary/20 p-2 rounded">
              {resumeFile.name}
            </p>
          </div>
        )}
      </div>
    );
  };

  const renderInputSection = () => {
    switch (selectedFunction) {
      case 'analysis':
        return (
          <div className="space-y-4">
            {renderResumeUpload()}
            <div>
              <label className="text-white mb-2 block">Job Title</label>
              <Input 
                placeholder="Enter job title" 
                className="text-white"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="text-white mb-2 block">Job Description</label>
              <Input 
                placeholder="Enter job description" 
                className="text-white"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
              />
            </div>
            <Button 
              className="w-full"
              onClick={handleAnalyzeResume}
              disabled={isAnalyzing || !resumeFile}
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze Resume'}
            </Button>
          </div>
        );

      case 'qa':
        return (
          <div className="space-y-4">
            {renderResumeUpload()}
            <div>
              <label className="text-white mb-2 block">Your Question</label>
              <Input 
                placeholder="Ask a question about the resume" 
                className="text-white"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleQASubmit()}
              />
            </div>
            <Button 
              className="w-full"
              onClick={handleQASubmit}
              disabled={isAnalyzing || !resumeFile || !question.trim()}
            >
              {isAnalyzing ? 'Processing...' : 'Ask Question'}
            </Button>
          </div>
        );

      case 'questions':
        return (
          <div className="space-y-4">
            {renderResumeUpload()}
            <div>
              <label className="text-white mb-2 block">Difficulty Level</label>
              <Select value={difficulty} onValueChange={setDifficulty}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select difficulty" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="easy">Easy</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="hard">Hard</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Number of Questions</label>
              <Input 
                type="number"
                min="1"
                max="10"
                value={numQuestions}
                onChange={(e) => setNumQuestions(e.target.value)}
                className="text-white"
              />
            </div>
            <div>
              <label className="text-white mb-2 block">Question Types</label>
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="technical"
                    checked={questionTypes.includes('technical')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes([...questionTypes, 'technical']);
                      } else {
                        setQuestionTypes(questionTypes.filter(t => t !== 'technical'));
                      }
                    }}
                  />
                  <label htmlFor="technical" className="text-white">Technical</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="behavioral"
                    checked={questionTypes.includes('behavioral')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes([...questionTypes, 'behavioral']);
                      } else {
                        setQuestionTypes(questionTypes.filter(t => t !== 'behavioral'));
                      }
                    }}
                  />
                  <label htmlFor="behavioral" className="text-white">Behavioral</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="experience"
                    checked={questionTypes.includes('experience')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes([...questionTypes, 'experience']);
                      } else {
                        setQuestionTypes(questionTypes.filter(t => t !== 'experience'));
                      }
                    }}
                  />
                  <label htmlFor="experience" className="text-white">Experience-based</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="situational"
                    checked={questionTypes.includes('situational')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes([...questionTypes, 'situational']);
                      } else {
                        setQuestionTypes(questionTypes.filter(t => t !== 'situational'));
                      }
                    }}
                  />
                  <label htmlFor="situational" className="text-white">Situational</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="problem-solving"
                    checked={questionTypes.includes('problem-solving')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes([...questionTypes, 'problem-solving']);
                      } else {
                        setQuestionTypes(questionTypes.filter(t => t !== 'problem-solving'));
                      }
                    }}
                  />
                  <label htmlFor="problem-solving" className="text-white">Problem-solving</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="system-design"
                    checked={questionTypes.includes('system-design')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes([...questionTypes, 'system-design']);
                      } else {
                        setQuestionTypes(questionTypes.filter(t => t !== 'system-design'));
                      }
                    }}
                  />
                  <label htmlFor="system-design" className="text-white">System Design</label>
                </div>
              </div>
            </div>
            <Button 
              className="w-full"
              onClick={handleInterviewQuestions}
              disabled={isAnalyzing || !resumeFile}
            >
              {isAnalyzing ? 'Generating...' : 'Generate Questions'}
            </Button>
          </div>
        );

      case 'improvement':
        return (
          <div className="space-y-4">
            <div>
              <label className="text-white mb-2 block">Resume Upload</label>
              <Input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="text-white"
              />
              {resumeFile && (
                <p className="text-sm text-gray-400 mt-1">
                  Selected file: {resumeFile.name}
                </p>
              )}
            </div>

            <div>
              <label className="text-white mb-2 block">Target Role</label>
              <Select value={targetRole} onValueChange={setTargetRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {IT_ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleImprovement}
              disabled={isAnalyzing || !resumeFile || !targetRole}
              className="w-full"
            >
              {isAnalyzing ? (
                <>
                  <Spinner className="mr-2 h-4 w-4" />
                  Analyzing...
                </>
              ) : (
                'Generate Improved Resume'
              )}
            </Button>
          </div>
        );

      case 'prediction':
        return (
          <div className="space-y-4">
            <div>
              <label className="text-white mb-2 block">Years of Experience</label>
              <Input 
                type="number"
                placeholder="Enter years of experience" 
                className="text-white"
                value={experience}
                onChange={(e) => setExperience(e.target.value)}
              />
            </div>
            <div>
              <label className="text-white mb-2 block">Skill Match Score (0-1)</label>
              <Input 
                type="number"
                min="0"
                max="1"
                step="0.01"
                placeholder="Enter skill match score" 
                className="text-white"
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
              />
              <p className="text-sm text-gray-400 mt-1">1 = perfect skill match</p>
            </div>
            <div>
              <label className="text-white mb-2 block">Education Level</label>
              <Select value={education} onValueChange={setEducation}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select education level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="High School">High School</SelectItem>
                  <SelectItem value="Associate">Associate</SelectItem>
                  <SelectItem value="Bachelor">Bachelor</SelectItem>
                  <SelectItem value="Master">Master</SelectItem>
                  <SelectItem value="PhD">PhD</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Job Level</label>
              <Select value={jobLevel} onValueChange={setJobLevel}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select job level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Entry-level">Entry-level</SelectItem>
                  <SelectItem value="Mid-level">Mid-level</SelectItem>
                  <SelectItem value="Senior">Senior</SelectItem>
                  <SelectItem value="Executive">Executive</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Industry</label>
              <Select value={industry} onValueChange={setIndustry}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select industry" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Technology">Technology</SelectItem>
                  <SelectItem value="Finance">Finance</SelectItem>
                  <SelectItem value="Healthcare">Healthcare</SelectItem>
                  <SelectItem value="Education">Education</SelectItem>
                  <SelectItem value="Manufacturing">Manufacturing</SelectItem>
                  <SelectItem value="Retail">Retail</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button 
              className="w-full"
              onClick={handleJobPrediction}
              disabled={isAnalyzing || !experience || !skills || !education || !jobLevel || !industry}
            >
              {isAnalyzing ? 'Predicting...' : 'Predict Job Possibility'}
            </Button>
          </div>
        );

      case 'skillgap':
        return (
          <div className="space-y-4">
            <div>
              <label className="text-white mb-2 block">Years of Experience</label>
              <Input 
                type="number"
                placeholder="Enter years of experience" 
                className="text-white"
                value={experience}
                onChange={(e) => setExperience(e.target.value)}
              />
            </div>
            <div>
              <label className="text-white mb-2 block">Education Level</label>
              <Select value={education} onValueChange={setEducation}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select education level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="High School">High School</SelectItem>
                  <SelectItem value="Associate">Associate</SelectItem>
                  <SelectItem value="Bachelor">Bachelor</SelectItem>
                  <SelectItem value="Master">Master</SelectItem>
                  <SelectItem value="PhD">PhD</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Job Level</label>
              <Select value={jobLevel} onValueChange={setJobLevel}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select job level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Entry-level">Entry-level</SelectItem>
                  <SelectItem value="Mid-level">Mid-level</SelectItem>
                  <SelectItem value="Senior">Senior</SelectItem>
                  <SelectItem value="Executive">Executive</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Industry</label>
              <Select value={industry} onValueChange={setIndustry}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select industry" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Technology">Technology</SelectItem>
                  <SelectItem value="Finance">Finance</SelectItem>
                  <SelectItem value="Healthcare">Healthcare</SelectItem>
                  <SelectItem value="Education">Education</SelectItem>
                  <SelectItem value="Manufacturing">Manufacturing</SelectItem>
                  <SelectItem value="Retail">Retail</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Location</label>
              <Select value={location} onValueChange={setLocation}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select location" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Urban">Urban</SelectItem>
                  <SelectItem value="Suburban">Suburban</SelectItem>
                  <SelectItem value="Rural">Rural</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button 
              className="w-full"
              onClick={handleSkillGapAnalysis}
              disabled={isAnalyzing || !experience || !education || !jobLevel || !industry || !location}
            >
              {isAnalyzing ? 'Predicting...' : 'Predict Salary'}
            </Button>
          </div>
        );

      case 'careerpath':
        return (
          <div className="space-y-4">
            {renderResumeUpload()}
            <div>
              <label className="text-white mb-2 block">Current Role</label>
              <Select value={currentRole} onValueChange={setCurrentRole}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select current role" />
                </SelectTrigger>
                <SelectContent>
                  {IT_ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Target Role</label>
              <Select value={targetRole} onValueChange={setTargetRole}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select target role" />
                </SelectTrigger>
                <SelectContent>
                  {IT_ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button 
              className="w-full"
              onClick={handleCareerPath}
              disabled={isAnalyzing || !resumeFile || !currentRole || !targetRole}
            >
              {isAnalyzing ? 'Generating...' : 'Generate Career Path'}
            </Button>
          </div>
        );

      case 'improved-resume':
        return (
          <div className="space-y-4">
            {renderResumeUpload()}
            <div>
              <label className="text-white mb-2 block">Target Role</label>
              <Select value={targetRole} onValueChange={setTargetRole}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {IT_ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {targetRole && ROLE_REQUIREMENTS[targetRole] && (
              <div className="space-y-2">
                <label className="text-white mb-2 block">Skills to Highlight</label>
                <div className="grid grid-cols-2 gap-2">
                  {ROLE_REQUIREMENTS[targetRole].map((skill) => (
                    <div key={skill} className="flex items-center space-x-2">
                      <Checkbox
                        id={skill}
                        checked={selectedSkills.includes(skill)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedSkills([...selectedSkills, skill]);
                          } else {
                            setSelectedSkills(selectedSkills.filter(s => s !== skill));
                          }
                        }}
                      />
                      <label htmlFor={skill} className="text-white">{skill}</label>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div>
              <label className="text-white mb-2 block">Job Description</label>
              <Input 
                placeholder="Enter job description" 
                className="text-white"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                disabled={false}
              />
              <p className="text-sm text-gray-400 mt-1">
                {jobDescription ? 
                  "Job description from Resume Analysis is being used." : 
                  "Please enter the job description for the target role."}
              </p>
            </div>
            <Button 
              className="w-full"
              onClick={handleResumeImprovement}
              disabled={isAnalyzing || !resumeFile || !targetRole || !jobDescription}
            >
              {isAnalyzing ? (
                <>
                  <Spinner className="mr-2 h-4 w-4" />
                  Analyzing...
                </>
              ) : (
                'Generate Improved Resume'
              )}
            </Button>
            {improvedResume && (
              <Button 
                className="w-full text-white hover:text-white border-white"
                onClick={handleDownloadImprovedResume}
                variant="outline"
              >
                Download Improved Resume
              </Button>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  // Add handler for animation start/end
  const handleAnimationStart = () => {
    setIsAnimating(true);
  };

  const handleAnimationComplete = () => {
    setIsAnimating(false);
    setShowChatbot(true);
  };

  return (
    <div className="flex h-screen bg-background relative">
      {/* Chat Section */}
      <div className={`flex flex-col ${selectedFunction ? 'w-[70%]' : 'w-full'} relative`}>
        <ParticleBackground isVisible={!isAnimating} />
        {/* Fixed Function Buttons */}
        <div className="sticky top-0 z-20 bg-background border-b">
          <div className="flex justify-between items-center p-4">
            <div className="flex flex-wrap gap-2">
              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('analysis')}
                      className={`${selectedFunction === 'analysis' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Resume Analysis
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Analyze your resume against a job description to get match score, matching skills, and areas for improvement.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('qa')}
                      className={`${selectedFunction === 'qa' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Q&A
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Ask questions about your resume and get AI-powered answers based on your resume content.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('questions')}
                      className={`${selectedFunction === 'questions' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Interview Questions
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Get customized interview questions based on your resume, job role, and difficulty level to prepare for interviews.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('improvement')}
                      className={`${selectedFunction === 'improvement' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Resume Improvement
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Get suggestions to improve your resume based on job requirements and industry standards.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('prediction')}
                      className={`${selectedFunction === 'prediction' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Job Possibility
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Predict your chances of getting a job based on your experience, skills, education, and other factors.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('skillgap')}
                      className={`${selectedFunction === 'skillgap' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Salary Prediction
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Get a salary prediction based on your experience, education, job level, industry, and location.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('improved-resume')}
                      className={`${selectedFunction === 'improved-resume' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Improved Resume
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Get an AI-generated improved version of your resume tailored to a specific job role.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            {!selectedFunction && (
              <StartAnimation 
                onAnimationStart={handleAnimationStart}
                onAnimationComplete={handleAnimationComplete} 
              />
            )}
          </div>
        </div>

        {/* Chat Messages with Scroll */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-0">
              <div className="space-y-4">
                {isAnalyzing && (
                  <div className="flex items-center space-x-2 text-white px-4">
                    <Spinner className="h-4 w-4" />
                    <span>AI is thinking...</span>
                  </div>
                )}
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${
                      message.type === 'user' ? 'justify-end' : 'justify-start'
                    } px-2.5 ${message.type === 'user' ? 'mb-5' : ''}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-3 ${
                        message.type === 'user'
                          ? 'bg-blue-600 text-white ml-2.5'
                          : 'bg-gray-700 text-white mr-2.5'
                      }`}
                    >
                      {message.type === 'ai' ? (
                        <div className="space-y-3 text-white">
                          {message.content.split('\n').map((line, lineIndex) => {
                            // Check for "Resume Improvement Analysis" header
                            if (line.startsWith('Resume Improvement Analysis')) {
                              return (
                                <div key={lineIndex} className="font-bold text-xl text-blue-400 border-b-2 border-blue-400/50 pb-3 mb-4">
                                  {line}
                                </div>
                              );
                            }
                            
                            // Check for "Suggestions:" label
                            if (line.trim() === 'Suggestions:') {
                              return (
                                <div key={lineIndex} className="font-semibold text-base text-blue-300 mt-2 mb-1">
                                  {line}
                                </div>
                              );
                            }
                            
                            // Check for "Example:" label
                            if (line.trim() === 'Example:') {
                              return (
                                <div key={lineIndex} className="font-semibold text-base text-green-400 mt-3 mb-1">
                                  {line}
                                </div>
                              );
                            }
                            
                            // Check for bullet points with • (from our Resume Improvement)
                            if (line.startsWith('•')) {
                              return (
                                <div key={lineIndex} className="flex items-start space-x-2 ml-2 my-1">
                                  <span className="text-blue-400 font-bold text-lg mt-0.5">•</span>
                                  <span className="text-gray-100 leading-relaxed">{line.substring(1).trim()}</span>
                                </div>
                              );
                            }
                            
                            // Check for section headers (lines ending with ':' but not Suggestions/Example)
                            if (line.endsWith(':') && !line.trim().startsWith('Example') && !line.trim().startsWith('Suggestions')) {
                              // Check if it's a major section header or skill area
                              const trimmedLine = line.trim();
                              const isSkillArea = !trimmedLine.includes('Results') && 
                                                 !trimmedLine.includes('Content') && 
                                                 !trimmedLine.includes('Details') && 
                                                 !trimmedLine.includes('Breakdown');
                              
                              if (isSkillArea) {
                                // Skill/Area headers (like "Node.js:", "Security:")
                                return (
                                  <div key={lineIndex} className="font-bold text-lg text-blue-400 mt-4 mb-2 border-l-4 border-blue-400 pl-3">
                                    {line}
                                  </div>
                                );
                              } else {
                                // Regular section headers
                                return (
                                  <div key={lineIndex} className="font-bold text-lg text-blue-400 border-b border-blue-400/30 pb-2">
                                    {line}
                                  </div>
                                );
                              }
                            }
                            
                            // Check for bullet points with - (legacy format)
                            if (line.startsWith('-')) {
                              return (
                                <div key={lineIndex} className="flex items-start space-x-2 ml-2 my-1">
                                  <span className="text-blue-400 font-bold">•</span>
                                  <span className="text-gray-100">{line.substring(1).trim()}</span>
                                </div>
                              );
                            }
                            
                            // Check for numbered items
                            if (line.match(/^\d+\./)) {
                              return (
                                <div key={lineIndex} className="flex items-start space-x-2">
                                  <span className="text-blue-400 font-semibold">{line.match(/^\d+\./)[0]}</span>
                                  <span className="text-white">{line.substring(line.indexOf('.') + 1)}</span>
                                </div>
                              );
                            }
                            
                            // Check for important information (usually in all caps or with special characters)
                            if (line.match(/[A-Z\s]{4,}/) || line.includes('$') || line.includes('%')) {
                              return (
                                <div key={lineIndex} className="bg-blue-400/10 p-2 rounded-md border border-blue-400/20 text-white">
                                  {line}
                                </div>
                              );
                            }
                            
                            // Example text (longer paragraphs after "Example:")
                            const prevLine = message.content.split('\n')[lineIndex - 1];
                            if (prevLine && prevLine.trim() === 'Example:' && line.trim() !== '') {
                              return (
                                <div key={lineIndex} className="text-gray-200 bg-green-900/20 p-3 rounded-md border-l-4 border-green-400 italic leading-relaxed">
                                  {line}
                                </div>
                              );
                            }
                            
                            // Regular text
                            return line.trim() === '' ? 
                              <div key={lineIndex} className="h-2"></div> : 
                              <div key={lineIndex} className="text-white leading-relaxed">{line}</div>;
                          })}
                        </div>
                      ) : (
                        message.content
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </ScrollArea>
        </div>

        {/* Fixed Input Section */}
        <div className="border-t bg-background">
          <form onSubmit={handleSendMessage} className="p-4">
            <div className="flex gap-2">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type your message or select a feature..."
                className="flex-1 text-white placeholder:text-gray-400"
                disabled={isProcessing}
              />
              <Button type="submit" disabled={isProcessing}>
                {isProcessing ? (
                  <>
                    <Spinner className="mr-2 h-4 w-4" />
                    Processing...
                  </>
                ) : (
                  'Send'
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>

      {/* Input Section with Resume Preview */}
      {selectedFunction && (
        <div className="w-[30%] border-l bg-background">
          {/* Input Section with Scroll */}
          <ScrollArea className="h-full">
            <div className="p-4 space-y-4">
              <h2 className="text-xl font-semibold text-white mb-4">
                {selectedFunction === 'analysis' && 'Resume Analysis Input'}
                {selectedFunction === 'qa' && 'Resume Q&A Input'}
                {selectedFunction === 'questions' && 'Interview Questions Input'}
                {selectedFunction === 'improvement' && 'Resume Improvement Input'}
                {selectedFunction === 'prediction' && 'Job Possibility Input'}
                {selectedFunction === 'skillgap' && 'Salary Prediction Input'}
                {selectedFunction === 'improved-resume' && 'Improved Resume Input'}
              </h2>
              
              {/* Input Section */}
              <div className="space-y-4">
                {renderInputSection()}
              </div>
              
              {/* Resume Preview Section */}
              {resumeFile && pdfUrl && (
                <div className="mt-8">
                  <h3 className="text-lg font-semibold text-white mb-2">Resume Preview</h3>
                  <div className="bg-white rounded-lg overflow-hidden border border-gray-200">
                    <iframe
                      src={pdfUrl}
                      className="w-full h-[400px]"
                      title="Resume Preview"
                    />
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  );
};

export default EmployeeChatbot; 