"""
Data models for the Mafia game simulation
Defines game entities, states, and communication protocols
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import uuid

class Role(Enum):
    """Player roles in the Mafia game"""
    MAFIA = "mafia"
    TOWNSPERSON = "townsperson"
    DOCTOR = "doctor"
    DETECTIVE = "detective"

class Phase(Enum):
    """Game phases"""
    SETUP = "setup"
    NIGHT = "night"
    DAY = "day"
    GAME_OVER = "game_over"

class Player(BaseModel):
    """Represents a player in the Mafia game"""
    name: str
    role: Optional[Role] = None
    is_alive: bool = True
    death_round: Optional[int] = None
    voting_history: List[Dict[str, Any]] = Field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    suspicion_level: float = 0.0  # 0.0 to 1.0 scale
    
    class Config:
        use_enum_values = True

class GameState(BaseModel):
    """Represents the current state of the game"""
    phase: Phase
    round: int
    living_players: List[str]
    dead_players: List[str]
    mafia_count: int
    townspeople_count: int
    is_game_over: bool
    winner: Optional[str] = None
    current_votes: Dict[str, str] = Field(default_factory=dict)
    last_night_actions: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class MCPRequest(BaseModel):
    """MCP protocol request message"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    
class MCPResponse(BaseModel):
    """MCP protocol response message"""
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class NightAction(BaseModel):
    """Represents a night phase action"""
    player: str
    action_type: str  # "kill", "save", "investigate"
    target: Optional[str] = None
    round: int

class VoteAction(BaseModel):
    """Represents a day phase vote"""
    voter: str
    target: str
    round: int

class GameEvent(BaseModel):
    """Represents a significant game event"""
    event_type: str
    description: str
    round: int
    phase: Phase
    affected_players: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class PlayerStatistics(BaseModel):
    """Statistics for a player's performance"""
    name: str
    role: Role
    survival_rounds: int
    votes_cast: int
    votes_received: int
    actions_taken: int
    final_status: str  # "alive", "eliminated_day", "eliminated_night"
    
    class Config:
        use_enum_values = True

class GameSummary(BaseModel):
    """Summary of a completed game"""
    game_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    winner: str
    total_rounds: int
    player_count: int
    role_distribution: Dict[str, int]
    player_statistics: List[PlayerStatistics]
    key_events: List[GameEvent]
    duration_minutes: float
    
class AgentPersonality(BaseModel):
    """Defines an AI agent's personality traits"""
    aggression: float = Field(ge=0.0, le=1.0)  # How aggressive in accusations
    trust: float = Field(ge=0.0, le=1.0)       # How trusting of others
    logic: float = Field(ge=0.0, le=1.0)       # How logical vs emotional
    deception: float = Field(ge=0.0, le=1.0)   # Ability to deceive (for Mafia)
    cooperation: float = Field(ge=0.0, le=1.0) # Willingness to cooperate
    
class AgentMemory(BaseModel):
    """Represents an agent's memory of game events"""
    event_type: str
    content: str
    round: int
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)

class SuspicionLevel(BaseModel):
    """Represents how suspicious one player is of another"""
    target: str
    level: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    last_updated: int  # Round when last updated

class DiscussionStatement(BaseModel):
    """Represents a statement made during discussion"""
    speaker: str
    content: str
    round: int
    phase: Phase
    response_to: Optional[str] = None  # Name of player being responded to
    
    class Config:
        use_enum_values = True

class GameConfig(BaseModel):
    """Configuration for a Mafia game"""
    min_players: int = 5
    max_players: int = 12
    default_players: List[str] = Field(default_factory=lambda: [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"
    ])
    phase_duration_minutes: int = 5
    discussion_rounds: int = 2
    enable_special_roles: bool = True
    mafia_ratio: float = 0.25  # 25% of players are Mafia
    doctor_enabled: bool = True
    detective_enabled: bool = True
    
    def get_player_names(self) -> List[str]:
        """Get the list of player names for the game"""
        return self.default_players[:self.max_players]
