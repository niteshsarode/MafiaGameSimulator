#!/usr/bin/env python3
"""
Mafia Game Simulation with MCP Server and AI Agents
Main entry point for the application
"""

import asyncio
import logging
import os
from typing import Dict, Any
from mcp_server import MCPServer
from game_logic import MafiaGame
from ai_agents import AgentManager
from narrator import GameNarrator
from config import GameConfig
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mafia_game.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MafiaGameSimulation:
    """Main simulation controller for the Mafia game"""
    
    def __init__(self, config: GameConfig):
        self.config = config
        self.game = MafiaGame(config)
        self.narrator = GameNarrator()
        self.agent_manager = AgentManager(config)
        self.mcp_server = MCPServer(self.game)
        self.game_state_history = []
        
    async def initialize_game(self):
        """Initialize the game with players and roles"""
        logger.info("Initializing Mafia game simulation...")
        
        # Create players and assign roles
        await self.game.setup_game()
        
        # Initialize AI agents for each player
        await self.agent_manager.initialize_agents(self.game.players)
        
        # Start MCP server
        await self.mcp_server.start()
        
        logger.info(f"Game initialized with {len(self.game.players)} players")
        logger.info(f"Roles: {self.game.get_role_distribution()}")
        
    async def run_simulation(self):
        """Run the complete game simulation"""
        try:
            await self.initialize_game()
            
            # Game introduction
            intro_message = await self.narrator.introduce_game(self.game.players)
            logger.info(f"Game Introduction: {intro_message}")
            
            game_round = 1
            
            while not self.game.is_game_over():
                logger.info(f"\n=== ROUND {game_round} ===")
                
                # Night Phase
                await self.run_night_phase()
                
                # Check win condition after night
                if self.game.is_game_over():
                    break
                    
                # Day Phase
                await self.run_day_phase()
                
                # Save game state
                self.save_game_state()
                
                game_round += 1
                
                # Prevent infinite loops
                if game_round > 50:
                    logger.warning("Game exceeded maximum rounds, ending simulation")
                    break
                    
            # Announce winner
            winner = self.game.get_winner()
            winner_message = await self.narrator.announce_winner(winner, self.game.players)
            logger.info(f"Game Over: {winner_message}")
            
        except Exception as e:
            logger.error(f"Error during game simulation: {e}")
            raise
        finally:
            await self.cleanup()
            
    async def run_night_phase(self):
        """Execute the night phase of the game"""
        logger.info("=== NIGHT PHASE ===")
        
        # Narrator announces night
        night_message = await self.narrator.announce_night_phase(self.game.current_phase)
        logger.info(night_message)
        
        # Mafia action
        mafia_target = await self.agent_manager.get_mafia_target(
            self.game.get_living_players(),
            self.game.get_mafia_members()
        )
        
        if mafia_target:
            logger.info(f"Mafia targets: {mafia_target}")
            
        # Doctor action
        doctor_save = await self.agent_manager.get_doctor_save(
            self.game.get_living_players(),
            self.game.get_doctor()
        )
        
        if doctor_save:
            logger.info(f"Doctor saves: {doctor_save}")
            
        # Detective action
        detective_investigation = await self.agent_manager.get_detective_investigation(
            self.game.get_living_players(),
            self.game.get_detective()
        )
        
        if detective_investigation:
            logger.info(f"Detective investigates: {detective_investigation}")
            
        # Process night actions
        night_result = await self.game.process_night_actions(
            mafia_target, doctor_save, detective_investigation
        )
        
        # Announce night results
        night_result_message = await self.narrator.announce_night_results(night_result)
        logger.info(night_result_message)
        
    async def run_day_phase(self):
        """Execute the day phase of the game"""
        logger.info("=== DAY PHASE ===")
        
        # Narrator announces day
        day_message = await self.narrator.announce_day_phase(
            self.game.current_phase, 
            self.game.get_living_players()
        )
        logger.info(day_message)
        
        # Discussion phase
        discussion_summary = await self.agent_manager.conduct_discussion(
            self.game.get_living_players(),
            self.game.get_game_state()
        )
        logger.info(f"Discussion Summary: {discussion_summary}")
        
        # Voting phase
        votes = await self.agent_manager.conduct_voting(
            self.game.get_living_players(),
            self.game.get_game_state()
        )
        
        # Process votes
        elimination_result = await self.game.process_day_voting(votes)
        
        # Announce voting results
        voting_message = await self.narrator.announce_voting_results(
            votes, elimination_result
        )
        logger.info(voting_message)
        
    def save_game_state(self):
        """Save current game state to history"""
        state = {
            'round': len(self.game_state_history) + 1,
            'phase': self.game.current_phase.value if hasattr(self.game.current_phase, 'value') else str(self.game.current_phase),
            'living_players': [p.name for p in self.game.get_living_players()],
            'dead_players': [p.name for p in self.game.get_dead_players()],
            'game_state': self.serialize_game_state(self.game.get_game_state())
        }
        self.game_state_history.append(state)
        
        # Save to file
        try:
            with open('game_history.json', 'w') as f:
                json.dump(self.game_state_history, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save game history: {e}")
            
    def serialize_game_state(self, game_state):
        """Convert game state to JSON-serializable format"""
        serialized = {}
        for key, value in game_state.items():
            if hasattr(value, 'value'):  # Enum
                serialized[key] = value.value
            elif isinstance(value, dict):
                serialized[key] = {k: v.value if hasattr(v, 'value') else v for k, v in value.items()}
            else:
                serialized[key] = value
        return serialized
            
    async def cleanup(self):
        """Clean up resources"""
        await self.mcp_server.stop()
        logger.info("Game simulation completed and resources cleaned up")

async def main():
    """Main entry point"""
    # Load configuration
    config = GameConfig()
    
    # Create and run simulation
    simulation = MafiaGameSimulation(config)
    
    try:
        await simulation.run_simulation()
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
