"""
Configuration settings for the Mafia game simulation
"""

import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class GameConfig(BaseModel):
    """Configuration for Mafia game parameters"""
    
    # Player configuration
    min_players: int = 5
    max_players: int = 12
    default_player_count: int = 8
    
    # Default player names
    default_players: List[str] = Field(default_factory=lambda: [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
        "Isabella", "Jack", "Katherine", "Liam"
    ])
    
    # Role configuration
    mafia_ratio: float = 0.25  # 25% of players are Mafia
    doctor_enabled: bool = True
    detective_enabled: bool = True
    min_mafia_count: int = 1
    max_mafia_count: int = 4
    
    # Phase timing (in seconds for simulation)
    night_phase_duration: int = 30
    day_discussion_duration: int = 60
    day_voting_duration: int = 30
    
    # Game flow
    max_rounds: int = 50  # Prevent infinite games
    discussion_rounds: int = 1  # Number of discussion rounds per day
    voting_time_limit: int = 30  # Time limit for voting in seconds
    
    # AI Agent configuration
    agent_response_timeout: int = 10  # Timeout for agent responses
    agent_thinking_delay: float = 1.0  # Delay to simulate thinking
    llm_temperature: float = 0.7  # Temperature for LLM responses
    max_memory_size: int = 20  # Maximum memory items per agent
    
    # Narrator configuration
    narrator_enabled: bool = True
    narrative_style: str = "dramatic_mysterious"
    detailed_narration: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: str = "mafia_game.log"
    save_game_history: bool = True
    game_history_file: str = "game_history.json"
    
    # MCP Server configuration
    mcp_server_enabled: bool = True
    mcp_server_port: int = 8000
    mcp_server_host: str = "0.0.0.0"
    
    # Web interface configuration
    web_interface_enabled: bool = True
    web_interface_port: int = 5000
    web_interface_host: str = "0.0.0.0"
    
    # OpenAI configuration
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "default_key"))
    openai_model: str = "gpt-4o"  # Latest OpenAI model
    max_tokens: int = 500
    
    def get_player_names(self) -> List[str]:
        """Get the list of player names for the game"""
        return self.default_players[:self.get_total_players()]
        
    def get_total_players(self) -> int:
        """Get the total number of players for the game"""
        return min(self.default_player_count, len(self.default_players))
        
    def get_role_distribution(self) -> Dict[str, int]:
        """Calculate role distribution based on player count"""
        total_players = self.get_total_players()
        
        # Calculate Mafia count
        mafia_count = max(self.min_mafia_count, min(self.max_mafia_count, 
                         int(total_players * self.mafia_ratio)))
        
        # Calculate special roles
        doctor_count = 1 if self.doctor_enabled and total_players >= 5 else 0
        detective_count = 1 if self.detective_enabled and total_players >= 6 else 0
        
        # Calculate townspeople count
        townspeople_count = total_players - mafia_count - doctor_count - detective_count
        
        return {
            "mafia": mafia_count,
            "doctor": doctor_count,
            "detective": detective_count,
            "townsperson": townspeople_count
        }
        
    def validate_configuration(self) -> bool:
        """Validate that the configuration is valid"""
        total_players = self.get_total_players()
        
        if total_players < self.min_players:
            return False
            
        if total_players > self.max_players:
            return False
            
        role_dist = self.get_role_distribution()
        if sum(role_dist.values()) != total_players:
            return False
            
        if role_dist["townsperson"] < 1:
            return False
            
        return True
        
    def get_phase_durations(self) -> Dict[str, int]:
        """Get phase durations in seconds"""
        return {
            "night": self.night_phase_duration,
            "day_discussion": self.day_discussion_duration,
            "day_voting": self.day_voting_duration
        }
        
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent-specific configuration"""
        return {
            "response_timeout": self.agent_response_timeout,
            "thinking_delay": self.agent_thinking_delay,
            "llm_temperature": self.llm_temperature,
            "max_memory_size": self.max_memory_size,
            "openai_api_key": self.openai_api_key,
            "openai_model": self.openai_model,
            "max_tokens": self.max_tokens
        }
        
    def get_narrator_config(self) -> Dict[str, Any]:
        """Get narrator-specific configuration"""
        return {
            "enabled": self.narrator_enabled,
            "style": self.narrative_style,
            "detailed": self.detailed_narration,
            "openai_api_key": self.openai_api_key,
            "openai_model": self.openai_model
        }
        
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "level": self.log_level,
            "file": self.log_file,
            "save_history": self.save_game_history,
            "history_file": self.game_history_file
        }

# Global configuration instance
config = GameConfig()

# Environment-specific overrides
if os.getenv("MAFIA_DEBUG", "false").lower() == "true":
    config.log_level = "DEBUG"
    config.agent_thinking_delay = 0.1
    config.night_phase_duration = 10
    config.day_discussion_duration = 20
    config.day_voting_duration = 10

if os.getenv("MAFIA_QUICK_MODE", "false").lower() == "true":
    config.night_phase_duration = 5
    config.day_discussion_duration = 10
    config.day_voting_duration = 5
    config.agent_thinking_delay = 0.1
    config.detailed_narration = False
