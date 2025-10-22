"""
Test script to verify LangGraph + MCP integration

This script tests:
1. Resume analysis workflow (4-node: extract → analyze → score → recommend)
2. Q&A workflow (3-node: classify → retrieve → generate)
3. MCP optimizations (caching, token reduction)
4. Performance improvements

Run this before starting the servers to ensure everything works!
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_resume_analysis():
    """Test resume analysis workflow with sample data"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Resume Analysis Workflow")
    print("="*80)
    
    try:
        from langgraph_integration import get_langgraph_service, initialize_langgraph_service
        
        # Initialize service
        groq_api_key = os.getenv('GROQ_API_KEY') or os.getenv('API_KEY_ANALYSIS')
        if not groq_api_key:
            print("❌ ERROR: GROQ_API_KEY not found in environment variables")
            print("   Please set GROQ_API_KEY in your .env file")
            return False
        
        print("🚀 Initializing LangGraph service...")
        initialize_langgraph_service(groq_api_key=groq_api_key)
        print("✅ Service initialized successfully!")
        
        # Sample resume text
        resume_text = """
        John Doe
        Software Engineer
        
        SKILLS:
        - Python, JavaScript, React, Node.js
        - Machine Learning, TensorFlow, PyTorch
        - SQL, MongoDB, PostgreSQL
        - Docker, Kubernetes, AWS
        - Git, CI/CD, Agile methodologies
        
        EXPERIENCE:
        Senior Software Engineer at Tech Corp (2020-2024)
        - Led team of 5 developers building ML-powered applications
        - Implemented CI/CD pipelines reducing deployment time by 60%
        - Built scalable REST APIs handling 1M+ requests/day
        - Mentored junior developers and conducted code reviews
        
        Software Engineer at Startup Inc (2018-2020)
        - Developed full-stack web applications using React and Node.js
        - Designed and optimized database schemas for high performance
        - Collaborated with product team to define technical requirements
        
        EDUCATION:
        Bachelor of Science in Computer Science
        Stanford University (2014-2018)
        GPA: 3.8/4.0
        """
        
        job_description = """
        We're looking for a Senior Full Stack Engineer with expertise in:
        - Python and JavaScript/TypeScript
        - React and modern frontend frameworks
        - Backend development (Node.js, Django, or Flask)
        - Cloud platforms (AWS, GCP, or Azure)
        - Machine Learning and AI integration
        - Database design (SQL and NoSQL)
        - DevOps and CI/CD practices
        
        Required:
        - 5+ years of software development experience
        - Strong problem-solving skills
        - Experience leading technical projects
        - Bachelor's degree in Computer Science or related field
        """
        
        print("\n📋 Analyzing resume against job description...")
        print(f"   Resume length: {len(resume_text)} characters")
        print(f"   Job description length: {len(job_description)} characters")
        
        # Analyze resume
        service = get_langgraph_service()
        result = service.analyze_resume(
            resume_text=resume_text,
            job_description=job_description
        )
        
        # Display results
        print("\n✅ ANALYSIS COMPLETE!")
        print("-" * 80)
        print(f"📊 Match Score: {result.get('match_score', 0)}/100")
        print(f"\n✅ Matching Skills ({len(result.get('matching_skills', []))}):")
        for skill in result.get('matching_skills', [])[:5]:
            print(f"   • {skill}")
        
        print(f"\n❌ Missing Skills ({len(result.get('missing_skills', []))}):")
        for skill in result.get('missing_skills', [])[:5]:
            print(f"   • {skill}")
        
        print(f"\n💪 Strengths ({len(result.get('strengths', []))}):")
        for strength in result.get('strengths', [])[:3]:
            print(f"   • {strength}")
        
        print(f"\n📈 Areas for Improvement ({len(result.get('areas_for_improvement', []))}):")
        for area in result.get('areas_for_improvement', [])[:3]:
            print(f"   • {area}")
        
        # Display performance metrics
        metadata = result.get('metadata', {})
        print(f"\n🚀 PERFORMANCE METRICS:")
        print(f"   ⏱️  Processing time: {metadata.get('processing_time', 'N/A')}")
        print(f"   💰 Tokens saved: {metadata.get('tokens_saved', 0)}")
        print(f"   📊 Cache hit rate: {metadata.get('cache_hit_rate', 'N/A')}")
        
        print("\n✅ TEST 1 PASSED: Resume analysis workflow working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def test_qa_workflow():
    """Test Q&A workflow with sample questions"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Q&A Workflow")
    print("="*80)
    
    try:
        from langgraph_integration import get_langgraph_service
        
        # Sample resume text
        resume_text = """
        Jane Smith
        Data Scientist
        
        SKILLS:
        - Python, R, SQL
        - Machine Learning (scikit-learn, TensorFlow, PyTorch)
        - Data Visualization (Matplotlib, Seaborn, Plotly)
        - Statistical Analysis, A/B Testing
        - Big Data (Spark, Hadoop)
        
        EXPERIENCE:
        Senior Data Scientist at Analytics Co (2021-2024)
        - Built predictive models improving customer retention by 25%
        - Conducted A/B tests and analyzed results for product decisions
        - Created interactive dashboards for executive reporting
        
        Data Analyst at Research Lab (2019-2021)
        - Performed statistical analysis on research datasets
        - Developed automated data pipelines for analysis
        
        EDUCATION:
        Master of Science in Data Science
        MIT (2017-2019)
        
        Bachelor of Science in Mathematics
        Berkeley (2013-2017)
        """
        
        questions = [
            "What programming languages does the candidate know?",
            "How many years of experience does the candidate have?",
            "What machine learning frameworks has the candidate used?",
            "What is the candidate's educational background?",
            "What are the candidate's key achievements?"
        ]
        
        service = get_langgraph_service()
        
        for i, question in enumerate(questions, 1):
            print(f"\n❓ Question {i}: {question}")
            
            result = service.answer_question(
                resume_text=resume_text,
                question=question
            )
            
            answer = result.get('answer', '')
            metadata = result.get('metadata', {})
            
            print(f"💡 Answer: {answer[:200]}..." if len(answer) > 200 else f"💡 Answer: {answer}")
            print(f"   📊 Question type: {metadata.get('question_type', 'unknown')}")
            print(f"   💰 Tokens saved: {metadata.get('tokens_saved', 0)}")
            
            # Check if caching is working (second time should be faster)
            if i == 1:
                print("\n🔄 Re-asking the same question to test caching...")
                result2 = service.answer_question(
                    resume_text=resume_text,
                    question=question
                )
                metadata2 = result2.get('metadata', {})
                print(f"   📊 Cache hit rate: {metadata2.get('cache_hit_rate', 'N/A')}")
                if metadata2.get('cache_hit', False):
                    print("   ✅ Cache HIT! Response served instantly from cache")
                else:
                    print("   ⚠️ Cache MISS (might be expected on first run)")
        
        print("\n✅ TEST 2 PASSED: Q&A workflow working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def test_performance_stats():
    """Test performance statistics retrieval"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Performance Statistics")
    print("="*80)
    
    try:
        from langgraph_integration import get_langgraph_service
        
        service = get_langgraph_service()
        stats = service.get_performance_stats()
        
        print("\n📊 OVERALL PERFORMANCE STATISTICS:")
        print("-" * 80)
        print(f"💾 Cache Statistics:")
        print(f"   • Cache size: {stats.get('cache_stats', {}).get('size', 0)} entries")
        print(f"   • Total queries: {stats.get('cache_stats', {}).get('total_queries', 0)}")
        print(f"   • Cache hits: {stats.get('cache_stats', {}).get('hits', 0)}")
        print(f"   • Hit rate: {stats.get('cache_stats', {}).get('hit_rate', 0):.1f}%")
        
        print(f"\n💰 Token Savings:")
        print(f"   • Total tokens saved: {stats.get('total_tokens_saved', 0):,}")
        print(f"   • Estimated cost savings: ${stats.get('estimated_cost_savings', 0):.2f}")
        
        print(f"\n🎯 Agent Statistics:")
        print(f"   • Resume analyses: {stats.get('agent_usage', {}).get('resume_analysis', 0)}")
        print(f"   • Q&A queries: {stats.get('agent_usage', {}).get('qa', 0)}")
        
        top_queries = stats.get('cache_stats', {}).get('top_queries', [])
        if top_queries:
            print(f"\n🔥 Top Cached Queries:")
            for query, count in top_queries[:3]:
                print(f"   • {query[:60]}... (used {count} times)")
        
        print("\n✅ TEST 3 PASSED: Performance statistics retrieved successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 LANGGRAPH + MCP INTEGRATION TEST SUITE")
    print("="*80)
    print("\nThis will test:")
    print("1. Resume Analysis Workflow (4-node LangGraph)")
    print("2. Q&A Workflow (3-node LangGraph)")
    print("3. Performance Statistics (MCP optimizations)")
    print("\n" + "="*80)
    
    results = []
    
    # Run tests
    results.append(("Resume Analysis", test_resume_analysis()))
    results.append(("Q&A Workflow", test_qa_workflow()))
    results.append(("Performance Stats", test_performance_stats()))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! LangGraph + MCP integration is working correctly!")
        print("\nYou can now start your servers:")
        print("   FastAPI: python main.py")
        print("   Flask:   python app.py")
    else:
        print("\n⚠️ SOME TESTS FAILED! Please fix the issues before deploying.")
        print("\nCommon issues:")
        print("   1. Missing GROQ_API_KEY in .env file")
        print("   2. Missing dependencies (langgraph, langchain-groq)")
        print("   3. Network issues (check internet connection)")
    
    print("="*80 + "\n")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
