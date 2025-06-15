"""
Utility functions for the Mafia game simulation
"""

import asyncio
import json
import logging
import random
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

class GameTimer:
    """Timer utility for managing game phases"""
    
    def __init__(self, duration: float):
        self.duration = duration
        self.start_time = None
        self.is_running = False
        
    def start(self):
        """Start the timer"""
        self.start_time = time.time()
        self.is_running = True
        
    def stop(self):
        """Stop the timer"""
        self.is_running = False
        
    def get_remaining_time(self) -> float:
        """Get remaining time in seconds"""
        if not self.is_running or not self.start_time:
            return 0.0
            
        elapsed = time.time() - self.start_time
        return max(0.0, self.duration - elapsed)
        
    def is_expired(self) -> bool:
        """Check if timer has expired"""
        return self.get_remaining_time() <= 0.0
        
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time

class VoteCounter:
    """Utility for counting and analyzing votes"""
    
    def __init__(self):
        self.votes: Dict[str, str] = {}  # voter -> target
        self.vote_counts: Counter = Counter()
        
    def add_vote(self, voter: str, target: str):
        """Add or update a vote"""
        # Remove previous vote if exists
        if voter in self.votes:
            old_target = self.votes[voter]
            self.vote_counts[old_target] -= 1
            if self.vote_counts[old_target] <= 0:
                del self.vote_counts[old_target]
                
        # Add new vote
        self.votes[voter] = target
        self.vote_counts[target] += 1
        
    def remove_vote(self, voter: str):
        """Remove a voter's vote"""
        if voter in self.votes:
            target = self.votes[voter]
            del self.votes[voter]
            self.vote_counts[target] -= 1
            if self.vote_counts[target] <= 0:
                del self.vote_counts[target]
                
    def get_leading_candidate(self) -> Optional[str]:
        """Get the candidate with the most votes"""
        if not self.vote_counts:
            return None
        return self.vote_counts.most_common(1)[0][0]
        
    def get_tied_candidates(self) -> List[str]:
        """Get all candidates tied for the most votes"""
        if not self.vote_counts:
            return []
            
        max_votes = max(self.vote_counts.values())
        return [candidate for candidate, votes in self.vote_counts.items() 
                if votes == max_votes]
                
    def get_vote_distribution(self) -> Dict[str, int]:
        """Get the complete vote distribution"""
        return dict(self.vote_counts)
        
    def get_total_votes(self) -> int:
        """Get total number of votes cast"""
        return len(self.votes)
        
    def has_majority(self, total_voters: int) -> bool:
        """Check if any candidate has a majority"""
        if not self.vote_counts:
            return False
        max_votes = max(self.vote_counts.values())
        return max_votes > total_voters // 2
        
    def clear(self):
        """Clear all votes"""
        self.votes.clear()
        self.vote_counts.clear()

class GameStatistics:
    """Utility for tracking game statistics"""
    
    def __init__(self):
        self.stats = {
            'total_games': 0,
            'mafia_wins': 0,
            'town_wins': 0,
            'average_game_length': 0.0,
            'role_win_rates': defaultdict(lambda: {'wins': 0, 'games': 0}),
            'player_stats': defaultdict(lambda: {
                'games_played': 0,
                'games_won': 0,
                'survival_rate': 0.0,
                'elimination_rate': 0.0
            })
        }
        
    def record_game(self, winner: str, players: List[Dict[str, Any]], 
                   game_length: int):
        """Record the results of a completed game"""
        self.stats['total_games'] += 1
        
        if winner.lower() == 'mafia':
            self.stats['mafia_wins'] += 1
        else:
            self.stats['town_wins'] += 1
            
        # Update average game length
        total_length = (self.stats['average_game_length'] * 
                       (self.stats['total_games'] - 1) + game_length)
        self.stats['average_game_length'] = total_length / self.stats['total_games']
        
        # Update role and player statistics
        for player in players:
            role = player['role']
            name = player['name']
            won = (winner.lower() == 'mafia' and role == 'mafia') or \
                  (winner.lower() != 'mafia' and role != 'mafia')
                  
            # Update role stats
            self.stats['role_win_rates'][role]['games'] += 1
            if won:
                self.stats['role_win_rates'][role]['wins'] += 1
                
            # Update player stats
            self.stats['player_stats'][name]['games_played'] += 1
            if won:
                self.stats['player_stats'][name]['games_won'] += 1
                
            if player.get('survived', False):
                self.stats['player_stats'][name]['survival_rate'] = \
                    (self.stats['player_stats'][name]['survival_rate'] * 
                     (self.stats['player_stats'][name]['games_played'] - 1) + 1) / \
                    self.stats['player_stats'][name]['games_played']
                    
    def get_win_rates(self) -> Dict[str, float]:
        """Get win rates for different factions"""
        total = self.stats['total_games']
        if total == 0:
            return {'mafia': 0.0, 'town': 0.0}
            
        return {
            'mafia': self.stats['mafia_wins'] / total,
            'town': self.stats['town_wins'] / total
        }
        
    def get_role_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for each role"""
        role_stats = {}
        for role, data in self.stats['role_win_rates'].items():
            if data['games'] > 0:
                role_stats[role] = {
                    'win_rate': data['wins'] / data['games'],
                    'games_played': data['games']
                }
        return role_stats
        
    def get_player_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each player"""
        return dict(self.stats['player_stats'])

class GameLogger:
    """Enhanced logging utility for game events"""
    
    def __init__(self, log_file: str = "mafia_game_detailed.log"):
        self.log_file = log_file
        self.game_events = []
        self.current_game_id = None
        
    def start_game(self, game_id: str, players: List[str], roles: Dict[str, str]):
        """Start logging a new game"""
        self.current_game_id = game_id
        self.game_events = []
        
        event = {
            'game_id': game_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'game_start',
            'players': players,
            'roles': roles
        }
        self.game_events.append(event)
        self._write_event(event)
        
    def log_phase_change(self, phase: str, round_num: int):
        """Log a phase change"""
        event = {
            'game_id': self.current_game_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'phase_change',
            'phase': phase,
            'round': round_num
        }
        self.game_events.append(event)
        self._write_event(event)
        
    def log_night_action(self, actor: str, action: str, target: Optional[str] = None):
        """Log a night action"""
        event = {
            'game_id': self.current_game_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'night_action',
            'actor': actor,
            'action': action,
            'target': target
        }
        self.game_events.append(event)
        self._write_event(event)
        
    def log_discussion(self, speaker: str, statement: str):
        """Log a discussion statement"""
        event = {
            'game_id': self.current_game_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'discussion',
            'speaker': speaker,
            'statement': statement
        }
        self.game_events.append(event)
        self._write_event(event)
        
    def log_vote(self, voter: str, target: str):
        """Log a vote"""
        event = {
            'game_id': self.current_game_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'vote',
            'voter': voter,
            'target': target
        }
        self.game_events.append(event)
        self._write_event(event)
        
    def log_elimination(self, eliminated: str, role: str, method: str):
        """Log a player elimination"""
        event = {
            'game_id': self.current_game_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'elimination',
            'eliminated': eliminated,
            'role': role,
            'method': method  # 'vote', 'mafia_kill', etc.
        }
        self.game_events.append(event)
        self._write_event(event)
        
    def log_game_end(self, winner: str, final_state: Dict[str, Any]):
        """Log game end"""
        event = {
            'game_id': self.current_game_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'game_end',
            'winner': winner,
            'final_state': final_state
        }
        self.game_events.append(event)
        self._write_event(event)
        
    def _write_event(self, event: Dict[str, Any]):
        """Write event to log file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to game log: {e}")
            
    def get_game_summary(self) -> Dict[str, Any]:
        """Get summary of current game"""
        if not self.game_events:
            return {}
            
        start_event = self.game_events[0]
        end_event = self.game_events[-1] if self.game_events[-1]['event_type'] == 'game_end' else None
        
        summary = {
            'game_id': self.current_game_id,
            'start_time': start_event['timestamp'],
            'end_time': end_event['timestamp'] if end_event else None,
            'total_events': len(self.game_events),
            'players': start_event['players'],
            'winner': end_event['winner'] if end_event else None
        }
        
        # Count event types
        event_counts = Counter(event['event_type'] for event in self.game_events)
        summary['event_breakdown'] = dict(event_counts)
        
        return summary

def calculate_optimal_roles(player_count: int) -> Dict[str, int]:
    """Calculate optimal role distribution for given player count"""
    if player_count < 5:
        raise ValueError("Minimum 5 players required")
        
    # Base calculations
    mafia_count = max(1, player_count // 4)  # 25% mafia
    doctor_count = 1 if player_count >= 5 else 0
    detective_count = 1 if player_count >= 7 else 0
    
    # Ensure mafia doesn't exceed 1/3 of players
    max_mafia = player_count // 3
    mafia_count = min(mafia_count, max_mafia)
    
    townspeople_count = player_count - mafia_count - doctor_count - detective_count
    
    # Ensure at least 1 townsperson
    if townspeople_count < 1:
        if detective_count > 0:
            detective_count = 0
            townspeople_count += 1
        elif doctor_count > 0:
            doctor_count = 0
            townspeople_count += 1
        else:
            mafia_count -= 1
            townspeople_count += 1
            
    return {
        'mafia': mafia_count,
        'doctor': doctor_count,
        'detective': detective_count,
        'townsperson': townspeople_count
    }

def generate_player_names(count: int) -> List[str]:
    """Generate a list of diverse player names"""
    names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
        "Isabella", "Jack", "Katherine", "Liam", "Maya", "Noah", "Olivia", "Peter",
        "Quinn", "Rachel", "Samuel", "Tara", "Uma", "Victor", "Wendy", "Xavier",
        "Yara", "Zoe", "Adrian", "Bella", "Caleb", "Dahlia"
    ]
    
    if count > len(names):
        # Generate additional names if needed
        for i in range(len(names), count):
            names.append(f"Player{i+1}")
            
    return names[:count]

async def simulate_thinking_delay(min_delay: float = 0.5, max_delay: float = 2.0):
    """Simulate AI thinking time with random delay"""
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)

def format_game_time(seconds: float) -> str:
    """Format game time in a readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def validate_game_state(game_state: Dict[str, Any]) -> bool:
    """Validate that game state is consistent"""
    required_fields = ['phase', 'round', 'living_players', 'dead_players']
    
    for field in required_fields:
        if field not in game_state:
            return False
            
    # Check that living + dead players don't overlap
    living = set(game_state['living_players'])
    dead = set(game_state['dead_players'])
    
    if living.intersection(dead):
        return False
        
    return True

def safe_json_serialize(obj: Any) -> str:
    """Safely serialize object to JSON, handling non-serializable types"""
    try:
        return json.dumps(obj, default=str, indent=2)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        return json.dumps({"error": "Serialization failed", "type": str(type(obj))})
