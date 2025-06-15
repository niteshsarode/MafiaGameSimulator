"""
Game Narrator implementation for Mafia game
Provides dramatic storytelling and phase management
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any
import google.generativeai as genai
import os
from models import Player, Phase, GameEvent

logger = logging.getLogger(__name__)

class GameNarrator:
    """AI-powered game narrator for dramatic storytelling"""
    
    def __init__(self):
        # Configure Gemini API - use fallback if not available
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.use_ai = True
            except Exception as e:
                logger.warning(f"Failed to configure Gemini API: {e}")
                self.model = None
                self.use_ai = False
        else:
            self.model = None
            self.use_ai = False
        self.narrative_style = "dramatic_mysterious"
        self.story_elements = []
        
    async def make_llm_request(self, prompt: str, system_message: str = None) -> str:
        """Make a request to the LLM for narrative generation"""
        if not self.use_ai or not self.model:
            return self.get_fallback_narration(prompt)
            
        try:
            # Combine system message and prompt for Gemini
            full_prompt = prompt
            if system_message:
                full_prompt = f"{system_message}\n\n{prompt}"
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt
            )
            return response.text if response.text else self.get_fallback_narration(prompt)
        except Exception as e:
            logger.error(f"Narrator LLM request failed: {e}")
            return self.get_fallback_narration(prompt)
            
    def get_fallback_narration(self, context: str) -> str:
        """Provide fallback narration when LLM is unavailable"""
        fallback_lines = [
            "The tension in the town is palpable...",
            "Strange events continue to unfold...",
            "The mystery deepens as the story continues...",
            "Citizens whisper nervously among themselves...",
            "The shadow of suspicion falls over the town..."
        ]
        return random.choice(fallback_lines)
        
    async def introduce_game(self, players: List[Player]) -> str:
        """Generate game introduction narrative"""
        system_message = """You are a dramatic game narrator for a Mafia game. Create an engaging, atmospheric introduction that sets the scene for a social deduction game. 

Your style:
- Dramatic and mysterious
- Create atmosphere and tension
- Welcome players to the game
- Explain the basic premise
- Build excitement

Keep it concise but engaging (2-3 paragraphs max)."""

        player_names = [p.name for p in players]
        prompt = f"""Welcome the following players to a new Mafia game: {', '.join(player_names)}

Create an atmospheric introduction that:
- Sets the scene in a mysterious town
- Explains that some players are secretly Mafia
- Mentions the alternating night and day phases
- Builds tension and excitement
- Welcomes all players by name

Introduction:"""

        narration = await self.make_llm_request(prompt, system_message)
        
        self.story_elements.append({
            'type': 'introduction',
            'content': narration,
            'round': 0
        })
        
        return narration
        
    async def announce_night_phase(self, round_number: int) -> str:
        """Generate night phase announcement"""
        system_message = """You are a dramatic game narrator. Announce the beginning of the night phase in a Mafia game.

Your style:
- Mysterious and atmospheric
- Create tension about what might happen
- Mention that the town sleeps while dark forces move
- Keep it dramatic but concise

Make it feel like a horror movie or mystery novel."""

        prompt = f"""Announce the beginning of Night {round_number} in the Mafia game.

Create a dramatic announcement that:
- Tells everyone the night has fallen
- Hints at danger in the darkness
- Mentions that the town sleeps unaware
- Builds suspense about what the Mafia might do

Night announcement:"""

        narration = await self.make_llm_request(prompt, system_message)
        
        self.story_elements.append({
            'type': 'night_phase',
            'content': narration,
            'round': round_number
        })
        
        return narration
        
    async def announce_night_results(self, night_result: Dict[str, Any]) -> str:
        """Generate dramatic announcement of night phase results"""
        system_message = """You are a dramatic game narrator announcing the results of the night phase in a Mafia game.

Your style:
- Dramatic revelation of events
- Create suspense and shock
- Use vivid imagery
- Make eliminations feel impactful
- Celebrate saves when they happen

Keep it engaging and atmospheric."""

        eliminated = night_result.get('eliminated')
        saved = night_result.get('saved', False)
        
        if eliminated and not saved:
            prompt = f"""Announce that {eliminated} was eliminated by the Mafia during the night.

Create a dramatic announcement that:
- Reveals the victim was found eliminated
- Creates shock and concern among survivors
- Hints at the Mafia's ruthless nature
- Builds tension for the upcoming day

Death announcement:"""
            
        elif saved:
            prompt = f"""Announce that someone was attacked but saved by the Doctor.

Create a dramatic announcement that:
- Reveals an attack was thwarted
- Credits the mysterious Doctor's intervention
- Builds hope while maintaining tension
- Keeps the saved person's identity mysterious if appropriate

Save announcement:"""
            
        else:
            prompt = """Announce that the night was quiet with no eliminations.

Create a brief announcement that:
- Notes the peaceful night
- Builds suspense about what might come
- Maintains the mysterious atmosphere

Quiet night announcement:"""

        narration = await self.make_llm_request(prompt, system_message)
        
        self.story_elements.append({
            'type': 'night_results',
            'content': narration,
            'round': len(self.story_elements) + 1,
            'eliminated': eliminated,
            'saved': saved
        })
        
        return narration
        
    async def announce_day_phase(self, round_number: int, living_players: List[Player]) -> str:
        """Generate day phase announcement"""
        system_message = """You are a dramatic game narrator announcing the day phase in a Mafia game.

Your style:
- Hopeful but tense
- Emphasize the importance of discussion and voting
- Create urgency about finding the Mafia
- Encourage participation

Make players feel the weight of their decisions."""

        player_names = [p.name for p in living_players]
        prompt = f"""Announce the beginning of Day {round_number} in the Mafia game.

Surviving players: {', '.join(player_names)}

Create an announcement that:
- Welcomes the dawn and new day
- Emphasizes the need for discussion and investigation
- Reminds players they must vote to eliminate someone
- Builds urgency about finding the Mafia
- Encourages careful consideration

Day announcement:"""

        narration = await self.make_llm_request(prompt, system_message)
        
        self.story_elements.append({
            'type': 'day_phase',
            'content': narration,
            'round': round_number
        })
        
        return narration
        
    async def announce_voting_results(self, votes: Dict[str, str], elimination_result: Dict[str, Any]) -> str:
        """Generate dramatic announcement of voting results"""
        system_message = """You are a dramatic game narrator announcing voting results in a Mafia game.

Your style:
- Build suspense about the vote count
- Create drama around the elimination
- Reveal the eliminated player's role dramatically
- Show the impact on remaining players

Make the elimination feel significant and impactful."""

        eliminated = elimination_result.get('eliminated')
        eliminated_role = elimination_result.get('eliminated_role')
        vote_counts = elimination_result.get('votes', {})
        
        prompt = f"""Announce the voting results where {eliminated} was eliminated.

Voting details:
- Eliminated player: {eliminated}
- Their role: {eliminated_role}
- Vote distribution: {vote_counts}

Create a dramatic announcement that:
- Builds suspense about the vote count
- Dramatically reveals who was eliminated
- Shockingly reveals their role
- Shows the town's reaction to the revelation
- Sets up tension for what comes next

Voting results announcement:"""

        narration = await self.make_llm_request(prompt, system_message)
        
        self.story_elements.append({
            'type': 'voting_results',
            'content': narration,
            'round': len(self.story_elements) + 1,
            'eliminated': eliminated,
            'role': eliminated_role
        })
        
        return narration
        
    async def announce_winner(self, winner: str, remaining_players: List[Player]) -> str:
        """Generate dramatic game conclusion announcement"""
        system_message = """You are a dramatic game narrator announcing the winner of a Mafia game.

Your style:
- Epic and conclusive
- Celebrate the winning team
- Reveal the final truth about players
- Create a satisfying ending
- Thank players for participating

Make it feel like the climax of a great story."""

        surviving_names = [p.name for p in remaining_players if p.is_alive]
        all_players = [(p.name, p.role.value) for p in remaining_players]
        
        prompt = f"""Announce that the {winner} team has won the Mafia game!

Game details:
- Winning team: {winner}
- Surviving players: {surviving_names}
- All players and their roles: {all_players}

Create an epic conclusion that:
- Dramatically announces the winner
- Reveals all player roles and identities
- Tells the story of how the game concluded
- Celebrates the winning strategy
- Thanks all players for their participation

Victory announcement:"""

        narration = await self.make_llm_request(prompt, system_message)
        
        self.story_elements.append({
            'type': 'game_conclusion',
            'content': narration,
            'winner': winner,
            'final_players': all_players
        })
        
        return narration
        
    async def provide_phase_transition(self, from_phase: Phase, to_phase: Phase, context: Dict[str, Any]) -> str:
        """Generate smooth transition between game phases"""
        transitions = {
            (Phase.NIGHT, Phase.DAY): "As dawn breaks over the town, the citizens emerge to face a new day...",
            (Phase.DAY, Phase.NIGHT): "As darkness falls, the town prepares for another uncertain night...",
            (Phase.SETUP, Phase.NIGHT): "The game begins as night falls over the unsuspecting town...",
        }
        
        fallback = transitions.get((from_phase, to_phase))
        if fallback:
            return fallback
            
        system_message = "Create a brief, atmospheric transition between game phases."
        prompt = f"Create a transition from {from_phase.value} to {to_phase.value} phase. Context: {context}"
        
        return await self.make_llm_request(prompt, system_message)
        
    def get_story_summary(self) -> str:
        """Get a summary of the narrative story"""
        if not self.story_elements:
            return "No story elements recorded yet."
            
        summary = "Game Story Summary:\n"
        for element in self.story_elements:
            summary += f"- {element['type'].title()}: {element['content'][:100]}...\n"
            
        return summary
        
    async def generate_custom_announcement(self, event_type: str, context: Dict[str, Any]) -> str:
        """Generate custom announcement for special events"""
        system_message = f"""You are a dramatic game narrator creating a special announcement for a {event_type} event in a Mafia game. Keep it atmospheric and engaging."""
        
        prompt = f"""Create a dramatic announcement for this event: {event_type}
Context: {context}

Make it atmospheric and fitting for a mystery/social deduction game."""

        return await self.make_llm_request(prompt, system_message)
