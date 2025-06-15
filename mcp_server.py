"""
MCP Server implementation for Mafia game
Handles Model Context Protocol communication and game state management
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from models import Player, GameState, MCPRequest, MCPResponse

logger = logging.getLogger(__name__)

class MCPServer:
    """MCP Server for handling game communication and state management"""
    
    def __init__(self, game):
        self.game = game
        self.connections = {}
        self.message_handlers = {
            'get_game_state': self.handle_get_game_state,
            'get_player_info': self.handle_get_player_info,
            'submit_action': self.handle_submit_action,
            'get_voting_status': self.handle_get_voting_status,
            'get_phase_info': self.handle_get_phase_info,
            'get_role_info': self.handle_get_role_info
        }
        self.running = False
        
    async def start(self):
        """Start the MCP server"""
        self.running = True
        logger.info("MCP Server started")
        
    async def stop(self):
        """Stop the MCP server"""
        self.running = False
        logger.info("MCP Server stopped")
        
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle incoming MCP requests"""
        try:
            handler = self.message_handlers.get(request.method)
            if not handler:
                return MCPResponse(
                    id=request.id,
                    error=f"Unknown method: {request.method}",
                    result=None
                )
                
            result = await handler(request.params)
            return MCPResponse(
                id=request.id,
                result=result,
                error=None
            )
            
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return MCPResponse(
                id=request.id,
                error=str(e),
                result=None
            )
            
    async def handle_get_game_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_game_state request"""
        return {
            'phase': self.game.current_phase,
            'round': self.game.current_round,
            'living_players': [
                {
                    'name': p.name,
                    'is_alive': p.is_alive,
                    'role': p.role if params.get('reveal_roles', False) else None
                }
                for p in self.game.players
            ],
            'dead_players': [
                {
                    'name': p.name,
                    'role': p.role,
                    'death_round': p.death_round
                }
                for p in self.game.get_dead_players()
            ],
            'is_game_over': self.game.is_game_over(),
            'winner': self.game.get_winner() if self.game.is_game_over() else None
        }
        
    async def handle_get_player_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_player_info request"""
        player_name = params.get('player_name')
        if not player_name:
            raise ValueError("player_name is required")
            
        player = self.game.get_player_by_name(player_name)
        if not player:
            raise ValueError(f"Player not found: {player_name}")
            
        return {
            'name': player.name,
            'role': player.role,
            'is_alive': player.is_alive,
            'voting_history': player.voting_history,
            'actions_taken': player.actions_taken,
            'suspicion_level': player.suspicion_level
        }
        
    async def handle_submit_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle submit_action request"""
        player_name = params.get('player_name')
        action_type = params.get('action_type')
        target = params.get('target')
        
        if not all([player_name, action_type]):
            raise ValueError("player_name and action_type are required")
            
        success = await self.game.submit_player_action(
            player_name, action_type, target
        )
        
        return {
            'success': success,
            'message': f"Action {action_type} submitted for {player_name}"
        }
        
    async def handle_get_voting_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_voting_status request"""
        return {
            'votes': self.game.current_votes,
            'required_votes': len(self.game.get_living_players()) // 2 + 1,
            'voting_complete': self.game.is_voting_complete(),
            'leading_candidate': self.game.get_leading_vote_candidate()
        }
        
    async def handle_get_phase_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_phase_info request"""
        return {
            'current_phase': self.game.current_phase,
            'phase_duration': self.game.phase_duration,
            'time_remaining': self.game.get_phase_time_remaining(),
            'phase_description': self.game.get_phase_description()
        }
        
    async def handle_get_role_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_role_info request"""
        role = params.get('role')
        if not role:
            raise ValueError("role is required")
            
        role_info = {
            'mafia': {
                'description': 'Eliminate townspeople and avoid detection',
                'night_action': 'Choose a player to eliminate',
                'win_condition': 'Equal or outnumber townspeople'
            },
            'townsperson': {
                'description': 'Find and eliminate all mafia members',
                'night_action': 'None',
                'win_condition': 'Eliminate all mafia members'
            },
            'doctor': {
                'description': 'Save players from mafia attacks',
                'night_action': 'Choose a player to save',
                'win_condition': 'Same as townspeople'
            },
            'detective': {
                'description': 'Investigate players to find mafia',
                'night_action': 'Investigate a player\'s role',
                'win_condition': 'Same as townspeople'
            }
        }
        
        return role_info.get(role.lower(), {'error': f'Unknown role: {role}'})
        
    async def broadcast_game_update(self, update_type: str, data: Dict[str, Any]):
        """Broadcast game updates to all connected clients"""
        message = {
            'type': 'game_update',
            'update_type': update_type,
            'data': data,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        logger.info(f"Broadcasting {update_type}: {data}")
        
        # In a real implementation, this would send to connected WebSocket clients
        # For simulation, we'll just log the broadcast
        
    async def notify_phase_change(self, new_phase: str, round_number: int):
        """Notify all clients of phase change"""
        await self.broadcast_game_update('phase_change', {
            'phase': new_phase,
            'round': round_number
        })
        
    async def notify_player_elimination(self, player_name: str, role: str):
        """Notify all clients of player elimination"""
        await self.broadcast_game_update('player_eliminated', {
            'player': player_name,
            'role': role
        })
        
    async def notify_game_end(self, winner: str, final_state: Dict[str, Any]):
        """Notify all clients of game end"""
        await self.broadcast_game_update('game_end', {
            'winner': winner,
            'final_state': final_state
        })
