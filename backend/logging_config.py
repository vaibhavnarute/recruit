"""
Centralized Logging Configuration for AI Recruiter
Provides consistent logging across all modules with proper formatting
"""

import logging
import sys
from datetime import datetime
import os

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file paths
MAIN_LOG_FILE = os.path.join(LOGS_DIR, f'ai_recruiter_{datetime.now().strftime("%Y%m%d")}.log')
TTS_LOG_FILE = os.path.join(LOGS_DIR, f'tts_{datetime.now().strftime("%Y%m%d")}.log')
MEETING_BOT_LOG_FILE = os.path.join(LOGS_DIR, f'meeting_bot_{datetime.now().strftime("%Y%m%d")}.log')
INTERVIEW_LOG_FILE = os.path.join(LOGS_DIR, f'interview_{datetime.now().strftime("%Y%m%d")}.log')
ERROR_LOG_FILE = os.path.join(LOGS_DIR, f'errors_{datetime.now().strftime("%Y%m%d")}.log')


def setup_logging(log_level=logging.INFO):
    """
    Setup centralized logging configuration
    
    Creates multiple handlers:
    - Console output (INFO+)
    - Main log file (DEBUG+)
    - Error log file (ERROR+)
    - Module-specific log files
    """
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # ==================== Console Handler ====================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # ==================== Main Log File Handler ====================
    main_file_handler = logging.FileHandler(MAIN_LOG_FILE, mode='a', encoding='utf-8')
    main_file_handler.setLevel(logging.DEBUG)
    main_file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    main_file_handler.setFormatter(main_file_formatter)
    root_logger.addHandler(main_file_handler)
    
    # ==================== Error Log File Handler ====================
    error_file_handler = logging.FileHandler(ERROR_LOG_FILE, mode='a', encoding='utf-8')
    error_file_handler.setLevel(logging.ERROR)
    error_file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d]\n'
        'Message: %(message)s\n'
        'Exception: %(exc_info)s\n'
        '---\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_file_handler.setFormatter(error_file_formatter)
    root_logger.addHandler(error_file_handler)
    
    # ==================== TTS Logger ====================
    tts_logger = logging.getLogger('langgraph_agents.tts_agent')
    tts_file_handler = logging.FileHandler(TTS_LOG_FILE, mode='a', encoding='utf-8')
    tts_file_handler.setLevel(logging.DEBUG)
    tts_file_handler.setFormatter(main_file_formatter)
    tts_logger.addHandler(tts_file_handler)
    
    # ==================== Meeting Bot Logger ====================
    bot_logger = logging.getLogger('langgraph_agents.meeting_bot_agent')
    bot_file_handler = logging.FileHandler(MEETING_BOT_LOG_FILE, mode='a', encoding='utf-8')
    bot_file_handler.setLevel(logging.DEBUG)
    bot_file_handler.setFormatter(main_file_formatter)
    bot_logger.addHandler(bot_file_handler)
    
    # ==================== Interview Logger ====================
    interview_logger = logging.getLogger('langgraph_agents.interview_conductor_agent')
    interview_file_handler = logging.FileHandler(INTERVIEW_LOG_FILE, mode='a', encoding='utf-8')
    interview_file_handler.setLevel(logging.DEBUG)
    interview_file_handler.setFormatter(main_file_formatter)
    interview_logger.addHandler(interview_file_handler)
    
    # Log startup
    root_logger.info("=" * 80)
    root_logger.info("🚀 AI RECRUITER LOGGING INITIALIZED")
    root_logger.info("=" * 80)
    root_logger.info(f"📁 Log Directory: {LOGS_DIR}")
    root_logger.info(f"📄 Main Log: {MAIN_LOG_FILE}")
    root_logger.info(f"🔊 TTS Log: {TTS_LOG_FILE}")
    root_logger.info(f"🤖 Bot Log: {MEETING_BOT_LOG_FILE}")
    root_logger.info(f"🎤 Interview Log: {INTERVIEW_LOG_FILE}")
    root_logger.info(f"❌ Error Log: {ERROR_LOG_FILE}")
    root_logger.info("=" * 80)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger for specific module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for detailed logging of specific operations
    
    Usage:
        with LogContext("TTS Generation", logger) as ctx:
            ctx.log("Starting TTS generation")
            # ... operation ...
            ctx.log("TTS completed")
    """
    
    def __init__(self, operation_name: str, logger: logging.Logger):
        self.operation_name = operation_name
        self.logger = logger
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"🎬 START: {self.operation_name}")
        self.logger.info(f"   Time: {self.start_time.isoformat()}")
        return self
    
    def log(self, message: str, level: str = "INFO"):
        """Log message within context"""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(f"   {message}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(f"❌ FAILED: {self.operation_name}")
            self.logger.error(f"   Error: {exc_val}")
            self.logger.error(f"   Duration: {duration:.2f}s")
        else:
            self.logger.info(f"✅ COMPLETE: {self.operation_name}")
            self.logger.info(f"   Duration: {duration:.2f}s")
        
        self.logger.info("-" * 80)
        
        return False  # Don't suppress exceptions


# Emoji logging helpers
class LogEmojis:
    """Standard emojis for consistent logging"""
    START = "🎬"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    TTS = "🔊"
    BOT = "🤖"
    INTERVIEW = "🎤"
    QUESTION = "❓"
    ANSWER = "💬"
    AUDIO = "🎵"
    VIDEO = "📹"
    DATABASE = "💾"
    API = "🔌"
    NETWORK = "🌐"
    TIME = "⏱️"
    COMPLETE = "🎉"


def log_tts_event(logger: logging.Logger, event: str, **kwargs):
    """
    Log TTS-specific event with consistent formatting
    
    Args:
        logger: Logger instance
        event: Event type (generation_start, generation_complete, etc.)
        **kwargs: Additional context data
    """
    logger.info(f"{LogEmojis.TTS} TTS Event: {event}")
    for key, value in kwargs.items():
        logger.info(f"   {key}: {value}")


def log_bot_event(logger: logging.Logger, event: str, **kwargs):
    """
    Log Meeting Bot event with consistent formatting
    
    Args:
        logger: Logger instance
        event: Event type (join_start, join_complete, etc.)
        **kwargs: Additional context data
    """
    logger.info(f"{LogEmojis.BOT} Bot Event: {event}")
    for key, value in kwargs.items():
        logger.info(f"   {key}: {value}")


def log_interview_event(logger: logging.Logger, event: str, **kwargs):
    """
    Log Interview event with consistent formatting
    
    Args:
        logger: Logger instance
        event: Event type (start, question, answer, etc.)
        **kwargs: Additional context data
    """
    logger.info(f"{LogEmojis.INTERVIEW} Interview Event: {event}")
    for key, value in kwargs.items():
        logger.info(f"   {key}: {value}")


def log_api_request(logger: logging.Logger, method: str, endpoint: str, **kwargs):
    """
    Log API request with consistent formatting
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint
        **kwargs: Request context (user, params, etc.)
    """
    logger.info(f"{LogEmojis.API} API Request: {method} {endpoint}")
    for key, value in kwargs.items():
        logger.info(f"   {key}: {value}")


def log_api_response(logger: logging.Logger, status_code: int, duration: float, **kwargs):
    """
    Log API response with consistent formatting
    
    Args:
        logger: Logger instance
        status_code: HTTP status code
        duration: Request duration in seconds
        **kwargs: Response context
    """
    emoji = LogEmojis.SUCCESS if status_code == 200 else LogEmojis.ERROR
    logger.info(f"{emoji} API Response: {status_code} ({duration:.3f}s)")
    for key, value in kwargs.items():
        logger.info(f"   {key}: {value}")


def log_database_operation(logger: logging.Logger, operation: str, collection: str, **kwargs):
    """
    Log database operation with consistent formatting
    
    Args:
        logger: Logger instance
        operation: Operation type (insert, update, query, etc.)
        collection: MongoDB collection name
        **kwargs: Operation context
    """
    logger.info(f"{LogEmojis.DATABASE} DB Operation: {operation} on {collection}")
    for key, value in kwargs.items():
        logger.info(f"   {key}: {value}")


# Initialize logging on import
if __name__ != "__main__":
    setup_logging()
