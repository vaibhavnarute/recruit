import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { extractTextFromPdf } from './ResumeAnalysis';
import { API_ENDPOINTS } from '@/config/api';
import { ResumeQA } from './ResumeQA';
import { InterviewQuestions } from './InterviewQuestions';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import Spinner from "@/components/ui/spinner";
import { useNavigate } from 'react-router-dom';
import StartAnimation from '@/components/ui/StartAnimation';
import ParticleBackground from '@/components/ui/ParticleBackground';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { detectIntent } from '@/services/intentDetection';
import '@/lib/pdfWorker';

interface Message {
  type: 'user' | 'ai';
  content: string;
}

interface HRChatbotProps {
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

const HRChatbot: React.FC<HRChatbotProps> = ({ onSelectFunction }) => {
  const navigate = useNavigate();
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
  const [difficulty, setDifficulty] = useState('easy');
  const [numQuestions, setNumQuestions] = useState('5');
  const [questionTypes, setQuestionTypes] = useState(['technical', 'behavioral']);
  const [multipleResumes, setMultipleResumes] = useState<File[]>([]);
  const [showChatbot, setShowChatbot] = useState(false);
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
      const { intent, response } = await detectIntent(inputMessage, true);
      
      // Add AI response to chat
      setMessages(prev => [...prev, { type: 'ai', content: response }]);

      // If intent is detected with high confidence, automatically select the feature
      if (intent) {
        // Map intent to function name
        const functionMap: { [key: string]: string } = {
          'resume_analysis': 'analysis',
          'resume_qa': 'qa',
          'interview_questions': 'questions',
          'multiple_resume': 'multiple',
          'resume_improvement': 'improvement'
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
    if (selectedFunction === functionName) return;
    
    setSelectedFunction(functionName);
    onSelectFunction(functionName);
    
    setMessages(prev => [...prev, {
      type: 'user',
      content: `Selected function: ${functionName}`
    }]);

    if (functionName === 'multiple') {
      navigate('/resumeAnalyzer');
    }
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

  const handleMultipleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setMultipleResumes(files);
      setMessages(prev => [...prev, {
        type: 'user',
        content: `Uploaded ${files.length} resumes for analysis`
      }]);
    }
  };

  const handleMultipleResumeAnalysis = async () => {
    if (multipleResumes.length === 0) {
      setMessages(prev => [...prev, {
        type: 'ai',
        content: 'Please upload at least one resume.'
      }]);
      return;
    }

    setIsAnalyzing(true);
    setMessages(prev => [...prev, {
      type: 'user',
      content: `Analyzing ${multipleResumes.length} resumes`
    }]);

    try {
      const formData = new FormData();
      multipleResumes.forEach((file, index) => {
        formData.append(`resume_${index}`, file);
      });

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
Multiple Resume Analysis Results:
------------------------------
Total Resumes Analyzed: ${multipleResumes.length}

Summary:
${data.summary || 'No summary available'}

Top Candidates:
${data.top_candidates ? data.top_candidates.map((candidate: any, index: number) => 
  `${index + 1}. ${candidate.name || `Resume ${index + 1}`} - Match Score: ${candidate.match_score}%`
).join('\n') : 'No candidate data available'}
      `;

      setMessages(prev => [...prev, {
        type: 'ai',
        content: analysisResult
      }]);
    } catch (error) {
      console.error('Multiple resume analysis error:', error);
      setMessages(prev => [...prev, {
        type: 'ai',
        content: `Error analyzing resumes: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
      }]);
    } finally {
      setIsAnalyzing(false);
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
      // Backend expects 'resume_files' (one or multiple) + job_description + threshold
      formData.append('job_description', jobDescription);
      formData.append('threshold', String(50));
      formData.append('resume_files', resumeFile);

      const response = await fetch(API_ENDPOINTS.analyze, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.[0]?.msg || errorData.error || `Server responded with status ${response.status}`);
      }

      const data = await response.json();

      // The Flask /api/analyze endpoint returns a list of results
      const first = Array.isArray(data?.results) && data.results.length > 0 ? data.results[0] : undefined;
      const rawScore = first?.similarity ?? first?.match_score ?? 0;
      const matchScore = typeof rawScore === 'number'
        ? (rawScore <= 1 ? Math.round(rawScore * 100) : Math.round(rawScore))
        : 0;
      const matchingSkills = Array.isArray(first?.matching_skills) ? first.matching_skills : [];
      const missingSkills = Array.isArray(first?.missing_skills) ? first.missing_skills : [];
      const strengthsArr = Array.isArray(first?.strengths) ? first.strengths : [];
      let improvements = Array.isArray(first?.areas_for_improvement)
        ? first.areas_for_improvement
        : (Array.isArray(first?.improvement_areas) ? first.improvement_areas : []);
      // Fallback: if backend didn't provide improvements, derive from missing skills
      if ((!improvements || improvements.length === 0) && Array.isArray(missingSkills) && missingSkills.length > 0) {
        improvements = missingSkills.map((skill: string) => `Strengthen ${skill} with hands-on projects and practice`);
      }

      const analysisResult = `
Resume Analysis Results:
------------------------
Match Score: ${matchScore}%

Matching Skills:
${matchingSkills.map((skill: string) => `- ${skill}`).join('\n')}

Missing Skills:
${missingSkills.map((skill: string) => `- ${skill}`).join('\n')}

Strengths:
${strengthsArr.map((strength: string) => `- ${strength}`).join('\n')}

Areas for Improvement:
${improvements.map((area: string) => `- ${area}`).join('\n')}
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

      if (sendFile) {
        // Flask QA endpoint expects JSON only (resume_text + question)
        // If we failed to extract text on the frontend, abort with guidance
        throw new Error('Resume text extraction failed. Please try again or upload a clearer PDF.');
      }

      const response = await fetch(API_ENDPOINTS.qa, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          resume_text: textToUse || '',
          question
        })
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

  const renderResumeUpload = () => (
    <div>
      <label className="text-white mb-2 block">Resume (PDF)</label>
      <Input
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        className="text-white"
      />
    </div>
  );

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
              <label className="text-white mb-2 block">Number of Questions</label>
              <Select value={numQuestions} onValueChange={setNumQuestions}>
                <SelectTrigger className="text-white">
                  <SelectValue placeholder="Select number of questions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">5 Questions</SelectItem>
                  <SelectItem value="10">10 Questions</SelectItem>
                  <SelectItem value="15">15 Questions</SelectItem>
                  <SelectItem value="20">20 Questions</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-white mb-2 block">Difficulty</label>
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
              <label className="text-white mb-2 block">Question Types</label>
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="technical"
                    checked={questionTypes.includes('technical')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes(prev => [...prev, 'technical']);
                      } else {
                        setQuestionTypes(prev => prev.filter(t => t !== 'technical'));
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
                        setQuestionTypes(prev => [...prev, 'behavioral']);
                      } else {
                        setQuestionTypes(prev => prev.filter(t => t !== 'behavioral'));
                      }
                    }}
                  />
                  <label htmlFor="behavioral" className="text-white">Behavioral</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="situational"
                    checked={questionTypes.includes('situational')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes(prev => [...prev, 'situational']);
                      } else {
                        setQuestionTypes(prev => prev.filter(t => t !== 'situational'));
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
                        setQuestionTypes(prev => [...prev, 'problem-solving']);
                      } else {
                        setQuestionTypes(prev => prev.filter(t => t !== 'problem-solving'));
                      }
                    }}
                  />
                  <label htmlFor="problem-solving" className="text-white">Problem Solving</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="leadership"
                    checked={questionTypes.includes('leadership')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes(prev => [...prev, 'leadership']);
                      } else {
                        setQuestionTypes(prev => prev.filter(t => t !== 'leadership'));
                      }
                    }}
                  />
                  <label htmlFor="leadership" className="text-white">Leadership</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="culture-fit"
                    checked={questionTypes.includes('culture-fit')}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setQuestionTypes(prev => [...prev, 'culture-fit']);
                      } else {
                        setQuestionTypes(prev => prev.filter(t => t !== 'culture-fit'));
                      }
                    }}
                  />
                  <label htmlFor="culture-fit" className="text-white">Culture Fit</label>
                </div>
              </div>
            </div>
            <Button 
              className="w-full"
              onClick={handleInterviewQuestions}
              disabled={isAnalyzing || !resumeFile || questionTypes.length === 0}
            >
              {isAnalyzing ? 'Generating...' : 'Generate Questions'}
            </Button>
          </div>
        );

      case 'multiple':
        return (
          <div className="space-y-4">
            <div>
              <label className="text-white mb-2 block">Multiple Resumes (PDF)</label>
              <Input
                type="file"
                accept=".pdf"
                onChange={handleMultipleFileChange}
                className="text-white"
                multiple
              />
            </div>
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
              onClick={handleMultipleResumeAnalysis}
              disabled={isAnalyzing || multipleResumes.length === 0}
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze Multiple Resumes'}
            </Button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-background relative">
      {/* Chat Section */}
      <div className={`flex flex-col ${selectedFunction ? 'w-[70%]' : 'w-full'} relative`}>
        <ParticleBackground />
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
                    <p>Analyze a single resume against a job description to get match score, matching skills, and areas for improvement.</p>
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
                    <p>Ask questions about a resume and get AI-powered answers based on the resume content.</p>
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
                    <p>Generate customized interview questions based on the candidate's resume, job role, and difficulty level.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider delayDuration={0}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => handleFunctionSelect('multiple')}
                      className={`${selectedFunction === 'multiple' ? 'bg-primary text-black hover:text-black' : 'text-white hover:text-white'}`}
                    >
                      Screen 100s of Resume's
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="bg-gray-800 text-white p-3 max-w-xs">
                    <p>Upload multiple resumes at once to efficiently screen and rank candidates based on job requirements. Can screen 1000 resume below 50kb.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            {!selectedFunction && <StartAnimation onAnimationComplete={() => setShowChatbot(true)} />}
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
                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} px-4`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-4 ${
                        message.type === 'user'
                          ? 'bg-primary text-black'
                          : 'bg-gray-800 text-white'
                      }`}
                    >
                      {message.type === 'ai' ? (
                        <div className="space-y-2">
                          {message.content.split('\n').map((line, lineIndex) => {
                            // Check for section headers (lines ending with ':')
                            if (line.endsWith(':') && ['Results:', 'Content:', 'Details:', 'Breakdown:'].some(header => line.includes(header))) {
                              return (
                                <div key={lineIndex} className="text-lg font-bold text-blue-300 border-b border-blue-300 mb-2">
                                  {line}
                                </div>
                              );
                            }
                            
                            // Check for bullet points
                            if (line.startsWith('- ')) {
                              return (
                                <div key={lineIndex} className="flex items-start space-x-2 mb-1">
                                  <span className="text-blue-300">•</span>
                                  <span>{line.substring(2)}</span>
                                </div>
                              );
                            }
                            
                            // Check for numbered items
                            if (line.match(/^\d+\./)) {
                              return (
                                <div key={lineIndex} className="flex items-start space-x-2">
                                  <span className="text-blue-400">{line.match(/^\d+\./)[0]}</span>
                                  <span>{line.substring(line.indexOf('.') + 1)}</span>
                                </div>
                              );
                            }
                            
                            // Check for important information (usually in all caps or with special characters)
                            if (line.match(/[A-Z\s]{4,}/) || line.includes('$') || line.includes('%')) {
                              return (
                                <div key={lineIndex} className="bg-blue-400/10 p-2 rounded-md border border-blue-400/20">
                                  {line}
                                </div>
                              );
                            }
                            
                            // Regular text
                            return <div key={lineIndex}>{line}</div>;
                          })}
                        </div>
                      ) : (
                        message.content
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div ref={messagesEndRef} />
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
                {selectedFunction === 'multiple' && 'Multiple Resume Analysis Input'}
              </h2>
              
              {/* Input Section */}
              <div className="space-y-4">
                {renderInputSection()}
              </div>
              
              {/* Resume Preview Section */}
              {pdfUrl && (
                <div className="mt-4">
                  <h3 className="text-lg font-semibold text-white mb-2">Resume Preview</h3>
                  <iframe
                    src={pdfUrl}
                    className="w-full h-96 border border-gray-700 rounded"
                    title="PDF Preview"
                  />
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  );
};

export default HRChatbot; 