"""
Google Meet Bot Configuration

Centralized configuration for Google Meet bot settings, credentials,
and environment variables.

Author: AI Recruiter Team
Created: February 2026
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GoogleMeetBotConfig(BaseModel):
    """
    Configuration model for Google Meet bot.
    """
    
    # Google Account Credentials
    google_email: str = Field(
        default=os.getenv('MEET_BOT_EMAIL', ''),
        description="Google account email for Meet bot"
    )
    google_password: str = Field(
        default=os.getenv('MEET_BOT_PASSWORD', ''),
        description="Google account password for Meet bot"
    )
    
    # Browser Settings
    headless_mode: bool = Field(
        default=os.getenv('MEET_BOT_HEADLESS', 'false').lower() == 'true',
        description="Run browser in headless mode"
    )
    browser_timeout: int = Field(
        default=int(os.getenv('MEET_BOT_TIMEOUT', '30000')),
        description="Browser operation timeout in milliseconds"
    )
    
    # Session Management
    session_directory: str = Field(
        default=os.getenv('MEET_BOT_SESSION_DIR', './meet_bot_sessions'),
        description="Directory to store persistent browser sessions"
    )
    session_duration_days: int = Field(
        default=7,
        description="Number of days session remains valid"
    )
    
    # Audio Settings
    audio_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate for recording (Hz)"
    )
    audio_chunk_duration_ms: int = Field(
        default=1000,
        description="Duration of each audio chunk in milliseconds"
    )
    enable_echo_cancellation: bool = Field(
        default=True,
        description="Enable acoustic echo cancellation"
    )
    enable_noise_suppression: bool = Field(
        default=True,
        description="Enable noise suppression"
    )
    
    # Interview Settings
    max_question_wait_time: int = Field(
        default=60,
        description="Maximum time to wait for candidate to start answering (seconds)"
    )
    max_answer_duration: int = Field(
        default=300,
        description="Maximum duration for candidate answer (seconds)"
    )
    silence_threshold_db: float = Field(
        default=-40.0,
        description="Audio level threshold to detect silence (dB)"
    )
    silence_duration_for_end: float = Field(
        default=3.0,
        description="Duration of silence to consider answer complete (seconds)"
    )
    
    # Meet Bot Behavior
    auto_join_meeting: bool = Field(
        default=True,
        description="Automatically click 'Join now' button"
    )
    auto_disable_camera: bool = Field(
        default=True,
        description="Keep camera disabled during meeting"
    )
    bot_display_name: str = Field(
        default="AI Interviewer",
        description="Display name for the bot in Meet"
    )
    
    # Error Handling
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed operations"
    )
    retry_delay_seconds: int = Field(
        default=5,
        description="Delay between retries (seconds)"
    )
    
    # Logging
    log_level: str = Field(
        default=os.getenv('LOG_LEVEL', 'INFO'),
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    enable_audio_logging: bool = Field(
        default=False,
        description="Save audio chunks to disk for debugging"
    )
    audio_log_directory: str = Field(
        default='./meet_bot_audio_logs',
        description="Directory to save audio logs"
    )
    
    model_config = ConfigDict(
        env_file='.env',
        case_sensitive=False
    )
    
    def validate_credentials(self) -> bool:
        """
        Validate that required credentials are set.
        
        Returns:
            bool: True if credentials are valid
        """
        if not self.google_email or self.google_email == '':
            return False
        if not self.google_password or self.google_password == '':
            return False
        return True
    
    def get_validation_errors(self) -> list[str]:
        """
        Get list of validation errors.
        
        Returns:
            list[str]: List of error messages
        """
        errors = []
        
        if not self.google_email or self.google_email == '':
            errors.append("MEET_BOT_EMAIL not set in environment variables")
        
        if not self.google_password or self.google_password == '':
            errors.append("MEET_BOT_PASSWORD not set in environment variables")
        
        return errors


# Global configuration instance
meet_bot_config = GoogleMeetBotConfig()


def get_config() -> GoogleMeetBotConfig:
    """
    Get global Meet bot configuration instance.
    
    Returns:
        GoogleMeetBotConfig: Configuration object
    """
    return meet_bot_config


def print_config_status():
    """
    Print current configuration status (for debugging).
    """
    config = get_config()
    
    print("\n" + "="*60)
    print("GOOGLE MEET BOT CONFIGURATION")
    print("="*60)
    
    # Credentials (masked)
    email_display = config.google_email if config.google_email else "❌ NOT SET"
    password_display = "✓ SET" if config.google_password else "❌ NOT SET"
    
    print(f"Google Email:        {email_display}")
    print(f"Google Password:     {password_display}")
    print(f"Headless Mode:       {config.headless_mode}")
    print(f"Browser Timeout:     {config.browser_timeout}ms")
    print(f"Session Directory:   {config.session_directory}")
    print(f"Audio Sample Rate:   {config.audio_sample_rate} Hz")
    print(f"Max Answer Duration: {config.max_answer_duration}s")
    print(f"Bot Display Name:    {config.bot_display_name}")
    print(f"Log Level:           {config.log_level}")
    
    # Validation
    print("\n" + "-"*60)
    if config.validate_credentials():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors:")
        for error in config.get_validation_errors():
            print(f"   - {error}")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    # Print configuration when run directly
    print_config_status()
