import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Upload, ArrowLeft } from "lucide-react";
import { useNavigate } from 'react-router-dom';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { API_ENDPOINTS } from '@/config/api';
import * as pdfjsLib from 'pdfjs-dist';
import '@/lib/pdfWorker';

export const extractTextFromPdf = async (file: File): Promise<string> => {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ 
      data: arrayBuffer,
      useWorker: false // Disable worker for simpler operation
    }).promise;
    
    let fullText = '';
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      const pageText = textContent.items
        .map((item: any) => {
          if ('str' in item) {
            return item.str;
          }
          return '';
        })
        .join(' ');
      fullText += pageText + ' ';
    }
    
    return fullText.trim();
  } catch (err) {
    console.error('Error extracting text from PDF:', err);
    throw new Error('Failed to extract text from PDF');
  }
};

const IT_ROLES = [
  "Software Engineer",
  "Full Stack Developer",
  "Frontend Developer",
  "Backend Developer",
  "DevOps Engineer",
  "Data Scientist",
  "Data Engineer",
  "Machine Learning Engineer",
  "Cloud Architect",
  "Security Engineer"
];

interface AnalysisResult {
  match_score: number;
  matching_skills: string[];
  missing_skills: string[];
  strengths: string[];
  areas_for_improvement: string[];
}

interface ResumeAnalysisProps {
  onResumeUpload: (file: File, text: string) => void;
  onAnalysisComplete: (analysis: AnalysisResult) => void;
}

export const ResumeAnalysis: React.FC<ResumeAnalysisProps> = ({ onResumeUpload, onAnalysisComplete }) => {
  const navigate = useNavigate();
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [selectedRole, setSelectedRole] = useState('');
  const [customRole, setCustomRole] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isUploadHovered, setIsUploadHovered] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      console.log('File uploaded:', file.name);
      setResumeFile(file);
      setError(null);

      try {
        const extractedText = await extractTextFromPdf(file);
        console.log('Text extracted from PDF:', extractedText.substring(0, 100) + '...');
        onResumeUpload(file, extractedText);
      } catch (err) {
        console.error('Error extracting text from PDF:', err);
        setError('Failed to extract text from PDF. Please try another file.');
      }
    } else {
      setError('Please upload a PDF file');
      setResumeFile(null);
    }
  };

  // Cleanup URL when component unmounts
  React.useEffect(() => {
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const handleAnalyze = async () => {
    if (!resumeFile) {
      setError('Please upload a resume first');
      return;
    }

    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const formData = new FormData();
      formData.append('resume', resumeFile);
      formData.append('job_description', jobDescription);

      const response = await fetch(API_ENDPOINTS.analyze, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      const result = await response.json();
      setAnalysisResult(result);
      onAnalysisComplete(result);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      <motion.div 
        className="flex justify-between items-center"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Button
          variant="ghost"
          onClick={() => navigate('/resumeAnalyzer')}
          className="gap-2 text-white font-sans"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Multi Resume Analyzer
        </Button>
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle>Upload Resume</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <motion.div
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => document.getElementById('resume-upload')?.click()}
              onMouseEnter={() => setIsUploadHovered(true)}
              onMouseLeave={() => setIsUploadHovered(false)}
            >
              <input
                id="resume-upload"
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="hidden"
                disabled={isAnalyzing}
              />
              <motion.div
                animate={{
                  scale: isUploadHovered ? 1.1 : 1,
                  transition: { duration: 0.3 }
                }}
              >
                <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <motion.p 
                  className="text-lg font-medium"
                  animate={{
                    scale: isUploadHovered ? 1.1 : 1,
                    transition: { duration: 0.3 }
                  }}
                >
                  {resumeFile ? resumeFile.name : 'Click to upload or drag and drop'}
                </motion.p>
                <p className="text-sm text-muted-foreground mt-2">
                  PDF files only
                </p>
              </motion.div>
            </motion.div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Job Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Select Role</label>
              <Select onValueChange={setSelectedRole} value={selectedRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a role" />
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
            <div className="space-y-2">
              <label className="text-sm font-medium">Custom Role</label>
              <Input
                placeholder="Or enter custom role"
                value={customRole}
                onChange={(e) => setCustomRole(e.target.value)}
                disabled={isAnalyzing}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Job Description</label>
            <Textarea
              placeholder="Enter the job description, including required skills, experience, and qualifications..."
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              className="min-h-[200px]"
              disabled={isAnalyzing}
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !resumeFile || !jobDescription}
            className="w-full"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze Resume'}
          </Button>
        </CardContent>
      </Card>

      {isAnalyzing && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
              <p className="text-muted-foreground">Analyzing your resume...</p>
              <Progress value={33} className="w-full" />
            </div>
          </CardContent>
        </Card>
      )}

      {analysisResult && !isAnalyzing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Analysis Results</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-medium">Match Score</label>
                  <span className="text-lg font-semibold">
                    {analysisResult.match_score}%
                  </span>
                </div>
                <Progress
                  value={analysisResult.match_score}
                  className="h-2"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h3 className="font-semibold">Matching Skills</h3>
                  <div className="flex flex-wrap gap-2">
                    {analysisResult.matching_skills.map((skill: string) => (
                      <Badge key={skill} variant="default" className="bg-green-100 text-green-800 hover:bg-green-200">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="font-semibold">Missing Skills</h3>
                  <div className="flex flex-wrap gap-2">
                    {analysisResult.missing_skills.map((skill: string) => (
                      <Badge key={skill} variant="destructive">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h3 className="font-semibold">Strengths</h3>
                  <ScrollArea className="h-[200px] rounded-md border p-4">
                    <ul className="space-y-2">
                      {analysisResult.strengths.map((strength: string, index: number) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-primary">•</span>
                          {strength}
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                </div>

                <div className="space-y-4">
                  <h3 className="font-semibold">Areas for Improvement</h3>
                  <ScrollArea className="h-[200px] rounded-md border p-4">
                    <ul className="space-y-2">
                      {analysisResult.areas_for_improvement.map((area: string, index: number) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-destructive">•</span>
                          {area}
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
};