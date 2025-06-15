"""
Turn-based Mafia game controller for manual progression
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from main import MafiaGameSimulation
from config import GameConfig
from models import Phase

logger = logging.getLogger(__name__)

class TurnBasedMafiaGame:
    """Turn-based Mafia game controller"""
    
    def __init__(self):
        self.simulation = None
        self.game_initialized = False
        self.current_turn_data = {}
        self.game_history = []
        
    async def initialize_new_game(self):
        """Initialize a new game"""
        try:
            config = GameConfig()
            self.simulation = MafiaGameSimulation(config)
            
            # Initialize the game but don't run the full simulation
            await self.simulation.initialize_game()
            self.game_initialized = True
            
            # Capture initial state
            self.current_turn_data = {
                "phase": "night",
                "round": 1,
                "actions": {},
                "results": {},
                "narrative": "Game initialized. Night phase begins..."
            }
            
            return {"success": True, "message": "Game initialized successfully"}
        except Exception as e:
            logger.error(f"Failed to initialize game: {e}")
            return {"error": str(e)}
    
    async def execute_next_turn(self):
        """Execute the next turn/phase"""
        if not self.game_initialized or not self.simulation:
            return {"error": "Game not initialized"}
            
        try:
            game = self.simulation.game
            
            if game.is_game_over():
                return {"error": "Game is already over"}
            
            if game.current_phase == Phase.NIGHT:
                return await self._execute_night_phase()
            elif game.current_phase == Phase.DAY:
                return await self._execute_day_phase()
            else:
                return {"error": f"Unknown phase: {game.current_phase}"}
                
        except Exception as e:
            logger.error(f"Failed to execute turn: {e}")
            return {"error": str(e)}
    
    async def _execute_night_phase(self):
        """Execute night phase actions"""
        game = self.simulation.game
        agent_manager = self.simulation.agent_manager
        narrator = self.simulation.narrator
        
        # Get night actions from AI agents
        mafia_target = await agent_manager.get_mafia_target(
            game.get_living_players(),
            game.get_mafia_members()
        )
        
        doctor_save = await agent_manager.get_doctor_save(
            game.get_living_players(),
            game.get_doctor()
        )
        
        detective_investigation = await agent_manager.get_detective_investigation(
            game.get_living_players(),
            game.get_detective()
        )
        
        # Process night actions
        night_result = await game.process_night_actions(
            mafia_target, doctor_save, detective_investigation
        )
        
        # Get narrative
        night_narrative = await narrator.announce_night_results(night_result)
        
        # Store turn data with enhanced details
        living_players = [p.name for p in game.get_living_players()]
        dead_players = [p.name for p in game.get_dead_players()]
        
        self.current_turn_data = {
            "phase": "night",
            "round": game.current_round - 1,  # Round increments after night
            "living_players": living_players,
            "dead_players": dead_players,
            "actions": {
                "mafia_target": mafia_target,
                "doctor_save": doctor_save,
                "detective_investigation": detective_investigation
            },
            "results": night_result,
            "narrative": night_narrative,
            "game_state": {
                "last_night_actions": {
                    "round": game.current_round - 1,
                    "mafia_target": mafia_target,
                    "doctor_save": doctor_save,
                    "detective_investigation": detective_investigation,
                    "results": night_result
                },
                "phase": "night",
                "round": game.current_round - 1
            }
        }
        
        self.game_history.append(self.current_turn_data.copy())
        
        return {
            "success": True,
            "turn_data": self.current_turn_data,
            "game_state": self._get_current_game_state()
        }
    
    async def _execute_day_phase(self):
        """Execute day phase actions"""
        game = self.simulation.game
        agent_manager = self.simulation.agent_manager
        narrator = self.simulation.narrator
        
        # Build enhanced game state with history for agents
        enhanced_game_state = {
            **game.get_game_state(),
            'game_history': self.game_history
        }
        
        # Conduct discussion
        discussion_summary = await agent_manager.conduct_discussion(
            game.get_living_players(),
            enhanced_game_state
        )
        
        # Conduct voting
        votes = await agent_manager.conduct_voting(
            game.get_living_players(),
            enhanced_game_state
        )
        
        # Process votes
        elimination_result = await game.process_day_voting(votes)
        
        # Get narrative
        voting_narrative = await narrator.announce_voting_results(
            votes, elimination_result
        )
        
        # Store turn data with enhanced details
        living_players = [p.name for p in game.get_living_players()]
        dead_players = [p.name for p in game.get_dead_players()]
        
        # Parse discussions into individual player statements
        discussions = []
        if discussion_summary:
            # Split discussion by newlines and parse each statement
            statements = discussion_summary.strip().split('\n')
            for statement in statements:
                if ':' in statement:
                    player_name, message = statement.split(':', 1)
                    player_name = player_name.strip()
                    message = message.strip()
                    
                    # Find the player to get their role
                    player = next((p for p in game.players if p.name == player_name), None)
                    if player and message:
                        discussions.append({
                            "player_name": player_name,
                            "player_role": player.role.value if player.role else "unknown",
                            "message": message
                        })
        
        self.current_turn_data = {
            "phase": "day",
            "round": game.current_round - 1,  # Round increments after day
            "living_players": living_players,
            "dead_players": dead_players,
            "discussions": discussions,
            "actions": {
                "discussion": discussion_summary,
                "votes": votes
            },
            "results": elimination_result,
            "narrative": voting_narrative,
            "game_state": {
                "current_votes": votes,
                "phase": "day",
                "round": game.current_round - 1
            }
        }
        
        self.game_history.append(self.current_turn_data.copy())
        
        return {
            "success": True,
            "turn_data": self.current_turn_data,
            "game_state": self._get_current_game_state()
        }
    
    def _get_current_game_state(self):
        """Get current game state"""
        if not self.simulation:
            return None
            
        game = self.simulation.game
        players_data = []
        
        for player in game.players:
            players_data.append({
                "name": player.name,
                "role": player.role.value if player.role else "unknown",
                "alive": player.is_alive,
                "death_round": player.death_round
            })
        
        return {
            "phase": game.current_phase.value if hasattr(game.current_phase, 'value') else str(game.current_phase),
            "round": game.current_round,
            "players": players_data,
            "living_count": len(game.get_living_players()),
            "mafia_count": len(game.get_mafia_members()),
            "town_count": len(game.get_townspeople()),
            "is_game_over": game.is_game_over(),
            "winner": game.get_winner()
        }
    
    def get_game_state(self):
        """Get complete game state including turn data"""
        base_state = self._get_current_game_state()
        if not base_state:
            return {
                "phase": "setup",
                "round": 0,
                "players": [],
                "living_count": 0,
                "mafia_count": 0,
                "town_count": 0,
                "is_game_over": False,
                "winner": None,
                "current_turn": {},
                "game_history": []
            }
        
        return {
            **base_state,
            "current_turn": self.current_turn_data,
            "game_history": self.game_history,  # Full game history
            "can_advance": self.game_initialized and not base_state["is_game_over"]
        }
    
    def get_turn_history(self):
        """Get complete turn history"""
        return {
            "history": self.game_history,
            "current_turn": self.current_turn_data
        }