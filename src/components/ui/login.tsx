import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../../lib/firebase';
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { motion } from "framer-motion";
import { useTheme } from '../../context/ThemeContext';
import { Mail, Lock, User, LogOut, CheckCircle2, Building2, Briefcase, UserCircle } from 'lucide-react';
import { registerUser, loginUser } from '../../services/authService';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<'hr' | 'employee' | ''>('');
  const [company, setCompany] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showWelcome, setShowWelcome] = useState(false);
  const [activeTab, setActiveTab] = useState('signin');
  const [userRole, setUserRole] = useState<'hr' | 'employee' | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { theme } = useTheme();

  const handleSignIn = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      // Sign in with Firebase
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;
      
      // Sync with MongoDB backend
      const response = await loginUser(firebaseUser.uid, firebaseUser.email || email);
      
      if (response.success && response.user) {
        setUserRole(response.user.role);
        setSuccess('Successfully signed in!');
        setShowWelcome(true);
      } else {
        throw new Error(response.error || 'Login failed');
      }
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validation
    if (!name.trim()) {
      setError('Please enter your full name');
      return;
    }
    
    if (!role) {
      setError('Please select your role (HR or Employee)');
      return;
    }
    
    if (role === 'hr' && !company.trim()) {
      setError('Please enter your company name');
      return;
    }
    
    setLoading(true);
    
    try {
      // Create user in Firebase
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;
      
      // Register in MongoDB backend with role
      const response = await registerUser(
        firebaseUser.uid,
        firebaseUser.email || email,
        name,
        role as 'hr' | 'employee',
        role === 'hr' ? company : null,
        phone || null
      );
      
      if (response.success) {
        setSuccess('Account created successfully! You can now sign in.');
        setActiveTab('signin');
        // Clear form
        setEmail('');
        setPassword('');
        setName('');
        setRole('');
        setCompany('');
        setPhone('');
      } else {
        throw new Error(response.error || 'Registration failed');
      }
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await auth.signOut();
      setShowWelcome(false);
      navigate('/');
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message);
      }
    }
  };

  const handleGetStarted = () => {
    if (userRole === 'hr') {
      navigate('/hr-resume-analysis');
    } else {
      navigate('/employee-resume-analysis');
    }
  };

  if (showWelcome) {
    return (
      <div className={`min-h-screen flex items-center justify-center p-4 ${
        theme === 'dark' 
          ? 'bg-gradient-to-br from-cyan-900 via-blue-900 to-cyan-900' 
          : 'bg-gradient-to-br from-cyan-100 via-white to-cyan-100'
      }`}>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Card className={`w-[400px] ${
            theme === 'dark' 
              ? 'bg-slate-900/50 backdrop-blur-sm border-cyan-300 border-2 shadow-lg' 
              : 'bg-white/50 backdrop-blur-sm border-cyan-500 border-2 shadow-lg'
          }`}>
            <CardHeader className="text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-cyan-400/10 flex items-center justify-center">
                <CheckCircle2 className="w-8 h-8 text-cyan-400" />
              </div>
              <CardTitle className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                Welcome to ResumeAI
              </CardTitle>
              <CardDescription className={`text-lg ${theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}`}>
                Your account is ready to use
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4 justify-center">
                <Button 
                  onClick={handleGetStarted}
                  className="w-full text-bold bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-500 hover:to-blue-600 text-slate-950 font-semibold"
                >
                  Get Started as {userRole === 'hr' ? 'HR' : 'Employee'}
                </Button>
              </div>
              <Button 
                variant="outline" 
                onClick={handleLogout}
                className={`w-full ${
                  theme === 'dark'
                    ? 'border-cyan-400 text-cyan-400 hover:bg-cyan-400 hover:text-slate-950'
                    : 'border-cyan-600 text-cyan-600 hover:bg-cyan-600 hover:text-white'
                }`}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen flex items-center justify-center p-4 ${
      theme === 'dark' 
        ? 'bg-gradient-to-br from-cyan-900 via-blue-900 to-cyan-900' 
        : 'bg-gradient-to-br from-cyan-100 via-white to-cyan-100'
    }`}>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <Card className={`w-[400px] ${
          theme === 'dark' 
            ? 'bg-slate-900/50 backdrop-blur-sm border-cyan-300 border-2 shadow-lg' 
            : 'bg-white/50 backdrop-blur-sm border-cyan-500 border-2 shadow-lg'
        }`}>
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 rounded-full bg-cyan-400/10 flex items-center justify-center">
              <User className="w-8 h-8 text-cyan-400" />
            </div>
            <CardTitle className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
              Welcome Back
            </CardTitle>
            <CardDescription className={`text-lg ${theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}`}>
              Sign in to your account or create a new one
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-8">
                <TabsTrigger value="signin">Sign In</TabsTrigger>
                <TabsTrigger value="signup">Sign Up</TabsTrigger>
              </TabsList>
              <TabsContent value="signin" className="space-y-4">
                <form onSubmit={handleSignIn} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email" className={theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}>
                      Email
                    </Label>
                    <div className="relative">
                      <Mail className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${theme === 'dark' ? 'text-cyan-300' : 'text-cyan-600'}`} size={18} />
                      <Input
                        id="email"
                        type="email"
                        placeholder="Enter your email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password" className={theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}>
                      Password
                    </Label>
                    <div className="relative">
                      <Lock className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${theme === 'dark' ? 'text-cyan-300' : 'text-cyan-600'}`} size={18} />
                      <Input
                        id="password"
                        type="password"
                        placeholder="Enter your password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  {error && <p className="text-red-500 text-sm">{error}</p>}
                  {success && <p className="text-green-500 text-sm">{success}</p>}
                  <Button 
                    type="submit" 
                    className="w-full bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-500 hover:to-blue-600 text-slate-950 font-semibold"
                    disabled={loading}
                  >
                    {loading ? 'Signing in...' : 'Sign In'}
                  </Button>
                </form>
              </TabsContent>
              <TabsContent value="signup" className="space-y-4">
                <form onSubmit={handleSignUp} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name" className={theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}>
                      Full Name
                    </Label>
                    <div className="relative">
                      <User className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${theme === 'dark' ? 'text-cyan-300' : 'text-cyan-600'}`} size={18} />
                      <Input
                        id="name"
                        type="text"
                        placeholder="Enter your full name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                  
                  {/* Role Selection */}
                  <div className="space-y-3">
                    <Label className={theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}>
                      Select Your Role *
                    </Label>
                    <div className="grid grid-cols-2 gap-3">
                      <label className={`cursor-pointer ${role === 'hr' ? 'scale-105' : ''} transition-transform`}>
                        <input 
                          type="radio" 
                          name="role" 
                          value="hr" 
                          checked={role === 'hr'}
                          onChange={(e) => setRole(e.target.value as 'hr')}
                          className="sr-only"
                          required
                        />
                        <div className={`border-2 rounded-lg p-4 text-center transition-all ${
                          role === 'hr'
                            ? theme === 'dark'
                              ? 'border-cyan-400 bg-cyan-400/10 shadow-lg'
                              : 'border-cyan-600 bg-cyan-50 shadow-lg'
                            : theme === 'dark'
                              ? 'border-slate-600 hover:border-cyan-400/50'
                              : 'border-slate-300 hover:border-cyan-600/50'
                        }`}>
                          <Briefcase className={`w-8 h-8 mx-auto mb-2 ${
                            role === 'hr' 
                              ? 'text-cyan-400' 
                              : theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
                          }`} />
                          <h3 className={`font-semibold mb-1 ${
                            theme === 'dark' ? 'text-white' : 'text-slate-900'
                          }`}>
                            HR / Recruiter
                          </h3>
                          <p className={`text-xs ${
                            theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
                          }`}>
                            Post jobs & manage candidates
                          </p>
                        </div>
                      </label>
                      
                      <label className={`cursor-pointer ${role === 'employee' ? 'scale-105' : ''} transition-transform`}>
                        <input 
                          type="radio" 
                          name="role" 
                          value="employee" 
                          checked={role === 'employee'}
                          onChange={(e) => setRole(e.target.value as 'employee')}
                          className="sr-only"
                          required
                        />
                        <div className={`border-2 rounded-lg p-4 text-center transition-all ${
                          role === 'employee'
                            ? theme === 'dark'
                              ? 'border-cyan-400 bg-cyan-400/10 shadow-lg'
                              : 'border-cyan-600 bg-cyan-50 shadow-lg'
                            : theme === 'dark'
                              ? 'border-slate-600 hover:border-cyan-400/50'
                              : 'border-slate-300 hover:border-cyan-600/50'
                        }`}>
                          <UserCircle className={`w-8 h-8 mx-auto mb-2 ${
                            role === 'employee' 
                              ? 'text-cyan-400' 
                              : theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
                          }`} />
                          <h3 className={`font-semibold mb-1 ${
                            theme === 'dark' ? 'text-white' : 'text-slate-900'
                          }`}>
                            Employee / Candidate
                          </h3>
                          <p className={`text-xs ${
                            theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
                          }`}>
                            Apply for jobs
                          </p>
                        </div>
                      </label>
                    </div>
                  </div>
                  
                  {/* Company Name - Only for HR */}
                  {role === 'hr' && (
                    <div className="space-y-2">
                      <Label htmlFor="company" className={theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}>
                        Company Name *
                      </Label>
                      <div className="relative">
                        <Building2 className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${theme === 'dark' ? 'text-cyan-300' : 'text-cyan-600'}`} size={18} />
                        <Input
                          id="company"
                          type="text"
                          placeholder="Enter your company name"
                          value={company}
                          onChange={(e) => setCompany(e.target.value)}
                          className="pl-10"
                          required
                        />
                      </div>
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="signup-email" className={theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}>
                      Email
                    </Label>
                    <div className="relative">
                      <Mail className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${theme === 'dark' ? 'text-cyan-300' : 'text-cyan-600'}`} size={18} />
                      <Input
                        id="signup-email"
                        type="email"
                        placeholder="Enter your email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-password" className={theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}>
                      Password
                    </Label>
                    <div className="relative">
                      <Lock className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${theme === 'dark' ? 'text-cyan-300' : 'text-cyan-600'}`} size={18} />
                      <Input
                        id="signup-password"
                        type="password"
                        placeholder="Create a password (min 6 characters)"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="pl-10"
                        required
                        minLength={6}
                      />
                    </div>
                  </div>
                  {error && <p className="text-red-500 text-sm">{error}</p>}
                  {success && <p className="text-green-500 text-sm">{success}</p>}
                  <Button 
                    type="submit" 
                    className="w-full bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-500 hover:to-blue-600 text-slate-950 font-semibold"
                    disabled={loading}
                  >
                    {loading ? 'Creating Account...' : 'Create Account'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
          <Separator className="my-6" />
          <CardFooter className="flex flex-col space-y-4">
            <p className={`text-sm ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
              By continuing, you agree to our Terms of Service and Privacy Policy
            </p>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
};

export default Login;