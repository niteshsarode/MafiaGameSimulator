"""
Core game logic for Mafia game simulation
Handles game state, rules, and phase transitions
"""

import asyncio
import random
import logging
from typing import Dict, List, Optional, Tuple, Any
from models import Player, GameState, Role, Phase
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class MafiaGame:
    """Core Mafia game logic and state management"""
    
    def __init__(self, config):
        self.config = config
        self.players: List[Player] = []
        self.current_phase = Phase.SETUP
        self.current_round = 0
        self.current_votes: Dict[str, str] = {}
        self.night_actions: Dict[str, Any] = {}
        self.game_history: List[Dict[str, Any]] = []
        self.phase_start_time = None
        self.phase_duration = 300  # 5 minutes per phase
        
    async def setup_game(self):
        """Set up the game with players and role assignments"""
        logger.info("Setting up Mafia game...")
        
        # Create players
        player_names = self.config.get_player_names()
        self.players = [Player(name=name) for name in player_names]
        
        # Assign roles
        await self.assign_roles()
        
        # Initialize game state
        self.current_phase = Phase.NIGHT
        self.current_round = 1
        self.phase_start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Game setup complete. Players: {len(self.players)}")
        
    async def assign_roles(self):
        """Assign roles to players based on game configuration"""
        total_players = len(self.players)
        
        # Calculate role distribution
        num_mafia = max(1, total_players // 4)  # 25% mafia
        num_doctor = 1 if total_players >= 5 else 0
        num_detective = 1 if total_players >= 6 else 0
        num_townspeople = total_players - num_mafia - num_doctor - num_detective
        
        roles = (
            [Role.MAFIA] * num_mafia +
            [Role.DOCTOR] * num_doctor +
            [Role.DETECTIVE] * num_detective +
            [Role.TOWNSPERSON] * num_townspeople
        )
        
        # Shuffle and assign roles
        random.shuffle(roles)
        for player, role in zip(self.players, roles):
            player.role = role
            
        logger.info(f"Roles assigned: {self.get_role_distribution()}")
        
    def get_role_distribution(self) -> Dict[str, int]:
        """Get the distribution of roles in the game"""
        role_counts = Counter(player.role.value for player in self.players)
        return dict(role_counts)
        
    def get_living_players(self) -> List[Player]:
        """Get all living players"""
        return [p for p in self.players if p.is_alive]
        
    def get_dead_players(self) -> List[Player]:
        """Get all dead players"""
        return [p for p in self.players if not p.is_alive]
        
    def get_mafia_members(self) -> List[Player]:
        """Get all living mafia members"""
        return [p for p in self.get_living_players() if p.role == Role.MAFIA]
        
    def get_townspeople(self) -> List[Player]:
        """Get all living townspeople (including special roles)"""
        return [p for p in self.get_living_players() if p.role != Role.MAFIA]
        
    def get_doctor(self) -> Optional[Player]:
        """Get the doctor if alive"""
        doctors = [p for p in self.get_living_players() if p.role == Role.DOCTOR]
        return doctors[0] if doctors else None
        
    def get_detective(self) -> Optional[Player]:
        """Get the detective if alive"""
        detectives = [p for p in self.get_living_players() if p.role == Role.DETECTIVE]
        return detectives[0] if detectives else None
        
    def get_player_by_name(self, name: str) -> Optional[Player]:
        """Get player by name"""
        for player in self.players:
            if player.name == name:
                return player
        return None
        
    async def process_night_actions(self, mafia_target: Optional[str], 
                                  doctor_save: Optional[str],
                                  detective_investigation: Optional[str]) -> Dict[str, Any]:
        """Process all night actions and return results"""
        results = {
            'eliminated': None,
            'saved': False,
            'investigation_result': None
        }
        
        # Process mafia kill
        if mafia_target:
            target_player = self.get_player_by_name(mafia_target)
            if target_player and target_player.is_alive:
                # Check if doctor saved the target
                if doctor_save == mafia_target:
                    results['saved'] = True
                    logger.info(f"Doctor saved {mafia_target} from mafia attack")
                else:
                    target_player.is_alive = False
                    target_player.death_round = self.current_round
                    results['eliminated'] = mafia_target
                    logger.info(f"Mafia eliminated {mafia_target}")
                    
        # Process detective investigation
        if detective_investigation:
            investigated_player = self.get_player_by_name(detective_investigation)
            if investigated_player:
                is_mafia = investigated_player.role == Role.MAFIA
                results['investigation_result'] = {
                    'target': detective_investigation,
                    'is_mafia': is_mafia
                }
                logger.info(f"Detective investigated {detective_investigation}: {'MAFIA' if is_mafia else 'INNOCENT'}")
                
        # Record night actions
        self.night_actions = {
            'round': self.current_round,
            'mafia_target': mafia_target,
            'doctor_save': doctor_save,
            'detective_investigation': detective_investigation,
            'results': results
        }
        
        # Advance to day phase
        self.current_phase = Phase.DAY
        self.phase_start_time = asyncio.get_event_loop().time()
        
        return results
        
    async def process_day_voting(self, votes: Dict[str, str]) -> Dict[str, Any]:
        """Process day phase voting and return results"""
        self.current_votes = votes
        
        # Count votes
        vote_counts = Counter(votes.values())
        
        # Handle no votes case
        if not vote_counts:
            return {
                'eliminated': None,
                'votes': {},
                'reason': 'No votes cast'
            }
            
        # Find player with most votes
        max_votes = max(vote_counts.values())
        candidates = [player for player, count in vote_counts.items() if count == max_votes]
        
        # Handle ties (random selection)
        if len(candidates) > 1:
            eliminated_player_name = random.choice(candidates)
            logger.info(f"Tie broken randomly, eliminating {eliminated_player_name}")
        else:
            eliminated_player_name = candidates[0]
            
        # Eliminate player
        eliminated_player = self.get_player_by_name(eliminated_player_name)
        if eliminated_player:
            eliminated_player.is_alive = False
            eliminated_player.death_round = self.current_round
            
        result = {
            'eliminated': eliminated_player_name,
            'eliminated_role': eliminated_player.role.value if eliminated_player else None,
            'votes': dict(vote_counts),
            'reason': 'Majority vote'
        }
        
        # Record voting history
        for voter, voted_for in votes.items():
            voter_player = self.get_player_by_name(voter)
            if voter_player:
                voter_player.voting_history.append({
                    'round': self.current_round,
                    'voted_for': voted_for
                })
                
        # Advance to next night phase
        self.current_round += 1
        self.current_phase = Phase.NIGHT
        self.phase_start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Day {self.current_round - 1} voting complete. Eliminated: {eliminated_player_name}")
        
        return result
        
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        living_mafia = len(self.get_mafia_members())
        living_townspeople = len(self.get_townspeople())
        
        # Mafia wins if they equal or outnumber townspeople
        if living_mafia >= living_townspeople:
            return True
            
        # Townspeople win if all mafia are eliminated
        if living_mafia == 0:
            return True
            
        return False
        
    def get_winner(self) -> Optional[str]:
        """Get the winner of the game"""
        if not self.is_game_over():
            return None
            
        living_mafia = len(self.get_mafia_members())
        living_townspeople = len(self.get_townspeople())
        
        if living_mafia >= living_townspeople:
            return "Mafia"
        elif living_mafia == 0:
            return "Townspeople"
        else:
            return None
            
    def get_game_state(self) -> Dict[str, Any]:
        """Get current game state"""
        return {
            'phase': self.current_phase.value,
            'round': self.current_round,
            'living_players': len(self.get_living_players()),
            'dead_players': len(self.get_dead_players()),
            'mafia_count': len(self.get_mafia_members()),
            'townspeople_count': len(self.get_townspeople()),
            'is_game_over': self.is_game_over(),
            'winner': self.get_winner(),
            'current_votes': self.current_votes,
            'last_night_actions': self.night_actions
        }
        
    async def submit_player_action(self, player_name: str, action_type: str, target: Optional[str] = None) -> bool:
        """Submit a player action"""
        player = self.get_player_by_name(player_name)
        if not player or not player.is_alive:
            return False
            
        action = {
            'type': action_type,
            'target': target,
            'round': self.current_round,
            'phase': self.current_phase.value
        }
        
        player.actions_taken.append(action)
        return True
        
    def is_voting_complete(self) -> bool:
        """Check if voting is complete"""
        living_players = self.get_living_players()
        return len(self.current_votes) >= len(living_players)
        
    def get_leading_vote_candidate(self) -> Optional[str]:
        """Get the player with the most votes"""
        if not self.current_votes:
            return None
            
        vote_counts = Counter(self.current_votes.values())
        return vote_counts.most_common(1)[0][0]
        
    def get_phase_time_remaining(self) -> float:
        """Get remaining time in current phase"""
        if not self.phase_start_time:
            return 0
            
        elapsed = asyncio.get_event_loop().time() - self.phase_start_time
        return max(0, self.phase_duration - elapsed)
        
    def get_phase_description(self) -> str:
        """Get description of current phase"""
        descriptions = {
            Phase.SETUP: "Setting up the game...",
            Phase.NIGHT: "Night time - special roles take their actions",
            Phase.DAY: "Day time - discussion and voting",
            Phase.GAME_OVER: "Game has ended"
        }
        return descriptions.get(self.current_phase, "Unknown phase")
