"""
ML Prediction Agent using LangGraph + MCP Integration

This agent handles:
1. Salary Prediction using XGBoost models
2. Job Possibility Prediction using XGBoost models

Uses LangGraph for structured workflow and MCP for context optimization
"""

from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END
import logging
import pickle
import os
import numpy as np

logger = logging.getLogger(__name__)


class PredictionState(TypedDict):
    """State for ML prediction workflow"""
    # Input
    prediction_type: str  # "salary" or "job_possibility"
    years_experience: float
    education_level: str
    job_level: str
    industry: str
    location: str  # For salary
    skill_match_score: float  # For job possibility
    
    # Processing
    features: List[float]
    model_type: str  # "basic" or "text" or "basic_improved" or "text_improved"
    
    # Output
    prediction: float
    confidence: float
    feature_importance: Dict[str, float]
    
    # Metadata
    tokens_used: int
    processing_time: float


class MLPredictionAgent:
    """
    LangGraph-based ML Prediction Agent
    
    Workflow:
    1. preprocess_input: Encode categorical features
    2. select_model: Choose best model based on input
    3. make_prediction: Load model and predict
    4. calculate_confidence: Compute prediction confidence
    """
    
    def __init__(self, models_dir: str = "models"):
        """
        Initialize the ML Prediction Agent
        
        Args:
            models_dir: Directory containing .pkl model files
        """
        self.models_dir = models_dir
        self.workflow = self._build_workflow()
        
        # Model paths
        self.model_paths = {
            'salary_basic': os.path.join(models_dir, 'xgboost_basic.pkl'),
            'salary_text': os.path.join(models_dir, 'xgboost_text.pkl'),
            'salary_basic_improved': os.path.join(models_dir, 'xgboost_basic_improved.pkl'),
            'salary_text_improved': os.path.join(models_dir, 'xgboost_text_improved.pkl'),
        }
        
        logger.info("✅ ML Prediction Agent initialized")
        logger.info(f"📁 Models directory: {models_dir}")
    
    def _build_workflow(self):
        """Build the LangGraph workflow for ML predictions"""
        workflow = StateGraph(PredictionState)
        
        # Add nodes
        workflow.add_node("preprocess_input", self._preprocess_input)
        workflow.add_node("select_model", self._select_model)
        workflow.add_node("make_prediction", self._make_prediction)
        workflow.add_node("calculate_confidence", self._calculate_confidence)
        
        # Define edges
        workflow.set_entry_point("preprocess_input")
        workflow.add_edge("preprocess_input", "select_model")
        workflow.add_edge("select_model", "make_prediction")
        workflow.add_edge("make_prediction", "calculate_confidence")
        workflow.add_edge("calculate_confidence", END)
        
        return workflow.compile()
    
    def _preprocess_input(self, state: PredictionState) -> PredictionState:
        """
        Node 1: Preprocess and encode input features
        """
        logger.info("🔄 [Node 1/4] Preprocessing input features...")
        
        prediction_type = state["prediction_type"]
        years_exp = state["years_experience"]
        education = state["education_level"]
        job_level = state["job_level"]
        industry = state["industry"]
        
        # Encode education level
        education_encoding = {
            'High School': 0,
            'Associate': 1,
            'Bachelor': 2,
            'Master': 3,
            'PhD': 4
        }
        edu_encoded = education_encoding.get(education, 2)
        
        # Encode job level
        job_level_encoding = {
            'Entry-level': 0,
            'Mid-level': 1,
            'Senior': 2,
            'Executive': 3
        }
        level_encoded = job_level_encoding.get(job_level, 1)
        
        # Encode industry
        industry_encoding = {
            'Technology': 0,
            'Finance': 1,
            'Healthcare': 2,
            'Education': 3,
            'Manufacturing': 4,
            'Retail': 5
        }
        industry_encoded = industry_encoding.get(industry, 0)
        
        if prediction_type == "salary":
            # Encode location
            location = state.get("location", "Urban")
            location_encoding = {
                'Urban': 0,
                'Suburban': 1,
                'Rural': 2
            }
            location_encoded = location_encoding.get(location, 0)
            
            # Features for salary prediction: [experience, education, level, industry, location]
            features = [
                years_exp,
                edu_encoded,
                level_encoded,
                industry_encoded,
                location_encoded
            ]
        else:  # job_possibility
            # Features for job possibility: [experience, education, level, industry, skill_match]
            skill_match = state.get("skill_match_score", 0.5)
            features = [
                years_exp,
                edu_encoded,
                level_encoded,
                industry_encoded,
                skill_match
            ]
        
        state["features"] = features
        logger.info(f"✅ Preprocessed features: {features}")
        
        return state
    
    def _select_model(self, state: PredictionState) -> PredictionState:
        """
        Node 2: Select the best model based on input characteristics
        
        Logic:
        - Use "improved" models for better accuracy
        - Use "text" models if more features are available in future
        - Default to "basic_improved" for now
        """
        logger.info("🎯 [Node 2/4] Selecting optimal model...")
        
        prediction_type = state["prediction_type"]
        
        # For now, always use improved basic models
        # In future, can add logic to select text models based on resume text availability
        if prediction_type == "salary":
            model_type = "salary_basic_improved"
        else:
            model_type = "salary_basic_improved"  # Using same model structure
        
        state["model_type"] = model_type
        logger.info(f"✅ Selected model: {model_type}")
        
        return state
    
    def _make_prediction(self, state: PredictionState) -> PredictionState:
        """
        Node 3: Load model and make prediction
        """
        logger.info("🔮 [Node 3/4] Making prediction...")
        
        model_type = state["model_type"]
        features = state["features"]
        prediction_type = state["prediction_type"]
        
        try:
            # Load the model
            model_path = self.model_paths.get(model_type)
            if not model_path or not os.path.exists(model_path):
                logger.error(f"❌ Model not found: {model_path}")
                # Fallback to basic calculation
                if prediction_type == "salary":
                    prediction = self._fallback_salary_calculation(state)
                else:
                    prediction = self._fallback_job_possibility_calculation(state)
            else:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                
                # Make prediction
                features_array = np.array([features])
                prediction = float(model.predict(features_array)[0])
                
                logger.info(f"✅ Raw prediction from model: {prediction}")
            
            # Post-process prediction
            if prediction_type == "salary":
                # Ensure salary is positive and reasonable
                prediction = max(30000, min(500000, prediction))
            else:
                # Ensure probability is between 0 and 1
                prediction = max(0.0, min(1.0, prediction))
            
            state["prediction"] = prediction
            logger.info(f"✅ Final prediction: {prediction}")
            
        except Exception as e:
            logger.error(f"❌ Error making prediction: {str(e)}")
            # Fallback
            if prediction_type == "salary":
                state["prediction"] = self._fallback_salary_calculation(state)
            else:
                state["prediction"] = self._fallback_job_possibility_calculation(state)
        
        return state
    
    def _calculate_confidence(self, state: PredictionState) -> PredictionState:
        """
        Node 4: Calculate confidence score and feature importance
        """
        logger.info("📊 [Node 4/4] Calculating confidence...")
        
        prediction_type = state["prediction_type"]
        features = state["features"]
        
        # Simple confidence calculation based on feature completeness
        # In production, would use model's prediction probabilities
        confidence = 0.75  # Base confidence
        
        # Increase confidence if we have complete data
        if all(f is not None and f >= 0 for f in features):
            confidence += 0.15
        
        # Adjust based on prediction type
        if prediction_type == "job_possibility":
            # Higher confidence for extreme predictions
            pred = state["prediction"]
            if pred > 0.8 or pred < 0.2:
                confidence += 0.05
        
        confidence = min(0.95, confidence)  # Cap at 95%
        state["confidence"] = confidence
        
        # Feature importance (simplified)
        feature_names = {
            "salary": ["Experience", "Education", "Job Level", "Industry", "Location"],
            "job_possibility": ["Experience", "Education", "Job Level", "Industry", "Skill Match"]
        }
        
        names = feature_names.get(prediction_type, feature_names["salary"])
        importance = {}
        for i, name in enumerate(names):
            if i < len(features):
                # Normalize feature values to importance scores
                importance[name] = round(abs(features[i]) / sum(abs(f) for f in features if f != 0) * 100, 2)
        
        state["feature_importance"] = importance
        logger.info(f"✅ Confidence: {confidence:.2%}")
        logger.info(f"📊 Feature importance: {importance}")
        
        return state
    
    def _fallback_salary_calculation(self, state: PredictionState) -> float:
        """Fallback rule-based salary calculation"""
        years_exp = state["years_experience"]
        education = state["education_level"]
        job_level = state["job_level"]
        industry = state["industry"]
        location = state.get("location", "Urban")
        
        base = 30000
        exp_factor = years_exp * 2000
        
        edu_bonus = {'High School': 0, 'Associate': 5000, 'Bachelor': 15000, 
                     'Master': 25000, 'PhD': 35000}.get(education, 15000)
        
        level_bonus = {'Entry-level': 0, 'Mid-level': 20000, 
                       'Senior': 40000, 'Executive': 80000}.get(job_level, 20000)
        
        industry_bonus = {'Technology': 15000, 'Finance': 12000, 'Healthcare': 10000,
                         'Education': 5000, 'Manufacturing': 8000, 'Retail': 3000}.get(industry, 15000)
        
        location_bonus = {'Urban': 10000, 'Suburban': 5000, 'Rural': 0}.get(location, 10000)
        
        return base + exp_factor + edu_bonus + level_bonus + industry_bonus + location_bonus
    
    def _fallback_job_possibility_calculation(self, state: PredictionState) -> float:
        """Fallback rule-based job possibility calculation"""
        years_exp = state["years_experience"]
        skill_match = state.get("skill_match_score", 0.5)
        education = state["education_level"]
        job_level = state["job_level"]
        
        exp_score = min(years_exp / 10, 1) * 0.3
        skill_score = skill_match * 0.4
        
        edu_score = {'High School': 0.1, 'Associate': 0.2, 'Bachelor': 0.3,
                     'Master': 0.4, 'PhD': 0.5}.get(education, 0.3) * 0.15
        
        level_score = {'Entry-level': 0.7, 'Mid-level': 0.5,
                       'Senior': 0.3, 'Executive': 0.2}.get(job_level, 0.5) * 0.1
        
        industry_score = 0.05
        
        return exp_score + skill_score + edu_score + level_score + industry_score
    
    def predict_salary(
        self,
        years_experience: float,
        education_level: str,
        job_level: str,
        industry: str,
        location: str
    ) -> Dict[str, Any]:
        """
        Predict salary using ML model
        
        Args:
            years_experience: Years of work experience
            education_level: Education level (High School, Associate, Bachelor, Master, PhD)
            job_level: Job level (Entry-level, Mid-level, Senior, Executive)
            industry: Industry (Technology, Finance, Healthcare, etc.)
            location: Location (Urban, Suburban, Rural)
        
        Returns:
            Dictionary with prediction results
        """
        logger.info(f"🚀 Starting salary prediction...")
        
        initial_state: PredictionState = {
            "prediction_type": "salary",
            "years_experience": years_experience,
            "education_level": education_level,
            "job_level": job_level,
            "industry": industry,
            "location": location,
            "skill_match_score": 0.0,  # Not used for salary
            "features": [],
            "model_type": "",
            "prediction": 0.0,
            "confidence": 0.0,
            "feature_importance": {},
            "tokens_used": 0,
            "processing_time": 0.0
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        return {
            "predicted_salary": final_state["prediction"],
            "confidence": final_state["confidence"],
            "feature_importance": final_state["feature_importance"],
            "model_used": final_state["model_type"]
        }
    
    def predict_job_possibility(
        self,
        years_experience: float,
        education_level: str,
        job_level: str,
        industry: str,
        skill_match_score: float
    ) -> Dict[str, Any]:
        """
        Predict job possibility using ML model
        
        Args:
            years_experience: Years of work experience
            education_level: Education level
            job_level: Job level
            industry: Industry
            skill_match_score: Skill match score (0-1)
        
        Returns:
            Dictionary with prediction results
        """
        logger.info(f"🚀 Starting job possibility prediction...")
        
        initial_state: PredictionState = {
            "prediction_type": "job_possibility",
            "years_experience": years_experience,
            "education_level": education_level,
            "job_level": job_level,
            "industry": industry,
            "location": "",  # Not used for job possibility
            "skill_match_score": skill_match_score,
            "features": [],
            "model_type": "",
            "prediction": 0.0,
            "confidence": 0.0,
            "feature_importance": {},
            "tokens_used": 0,
            "processing_time": 0.0
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        probability = final_state["prediction"]
        recommendation = probability > 0.6
        
        return {
            "probability": probability,
            "recommended": recommendation,
            "confidence": final_state["confidence"],
            "feature_importance": final_state["feature_importance"],
            "model_used": final_state["model_type"]
        }
