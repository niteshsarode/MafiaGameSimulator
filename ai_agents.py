"""
AI Agent implementations for different Mafia game roles
Each agent has distinct personality and decision-making patterns
"""

import asyncio
import json
import logging
import random
from typing import Dict, List, Optional, Any, Tuple
import google.generativeai as genai
import os
from models import Player, Role

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for all AI agents"""
    
    def __init__(self, player: Player, personality: str):
        self.player = player
        self.personality = personality
        # Configure Gemini API - use a fallback key for testing
        api_key = os.getenv("GEMINI_API_KEY", "test_key")
        if api_key and api_key != "test_key":
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.use_ai = True
            except Exception as e:
                logger.warning(f"Failed to configure Gemini API: {e}")
                self.model = None
                self.use_ai = False
        else:
            self.model = None
            self.use_ai = False
        self.memory = []  # Store conversation history
        self.suspicions = {}  # Track suspicions of other players
        
    async def make_llm_request(self, prompt: str, system_message: str = None) -> str:
        """Make a request to the LLM with error handling"""
        if not self.use_ai or not self.model:
            return self.get_fallback_response(prompt)
            
        try:
            # Combine system message and prompt for Gemini
            full_prompt = prompt
            if system_message:
                full_prompt = f"{system_message}\n\n{prompt}"
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt
            )
            return response.text if response.text else self.get_fallback_response(prompt)
        except Exception as e:
            logger.error(f"LLM request failed for {self.player.name}: {e}")
            return self.get_fallback_response(prompt)
            
    def get_fallback_response(self, prompt: str) -> str:
        """Provide fallback response when LLM is unavailable"""
        return f"I need to think about this... ({self.player.name})"
        
    def update_memory(self, event: str, context: Dict[str, Any]):
        """Update agent's memory with new information"""
        self.memory.append({
            'event': event,
            'context': context,
            'round': context.get('round', 0)
        })
        
        # Keep memory limited to prevent context overflow
        if len(self.memory) > 20:
            self.memory = self.memory[-15:]
            
    def update_suspicion(self, target: str, level: float, reason: str):
        """Update suspicion level for a target player"""
        if target not in self.suspicions:
            self.suspicions[target] = {'level': 0.0, 'reasons': []}
            
        self.suspicions[target]['level'] = max(0, min(1, 
            self.suspicions[target]['level'] + level))
        self.suspicions[target]['reasons'].append(reason)

class MafiaAgent(BaseAgent):
    """AI Agent for Mafia role players"""
    
    def __init__(self, player: Player):
        super().__init__(player, "deceptive_manipulative")
        
    async def choose_target(self, living_players: List[Player], mafia_members: List[Player]) -> Optional[str]:
        """Choose a target to eliminate during night phase"""
        # Filter out mafia members and self
        possible_targets = [
            p for p in living_players 
            if p.role != Role.MAFIA and p.name != self.player.name
        ]
        
        if not possible_targets:
            return None
            
        # Create context for LLM decision
        context = self.build_targeting_context(possible_targets, mafia_members)
        
        system_message = f"""You are {self.player.name}, a Mafia member in a Mafia game. Your goal is to eliminate townspeople while avoiding detection. You are strategic, deceptive, and work with your fellow Mafia members.

Your personality: {self.personality}
- You deflect suspicion onto others
- You appear helpful and trustworthy
- You target threats to the Mafia
- You coordinate with fellow Mafia members

Choose your target wisely. Prioritize:
1. Special roles like Detective or Doctor if suspected
2. Players who are suspicious of you or other Mafia
3. Strong players who could lead the town

Respond with only the name of your chosen target."""

        prompt = f"""Current situation:
{context}

Who do you choose to eliminate tonight? Consider:
- Who poses the biggest threat to the Mafia?
- Who might be a special role?
- Who is most suspicious of Mafia members?

Your choice:"""

        try:
            response = await self.make_llm_request(prompt, system_message)
            
            # Extract target name from response
            for target in possible_targets:
                if target.name.lower() in response.lower():
                    logger.info(f"Mafia {self.player.name} chose target: {target.name}")
                    return target.name
                    
            # Fallback to random choice
            target = random.choice(possible_targets)
            logger.info(f"Mafia {self.player.name} chose random target: {target.name}")
            return target.name
            
        except Exception as e:
            logger.error(f"Error in Mafia target selection: {e}")
            return random.choice(possible_targets).name if possible_targets else None
            
    def build_targeting_context(self, possible_targets: List[Player], mafia_members: List[Player]) -> str:
        """Build context for target selection"""
        context = f"Living players (excluding Mafia): {[p.name for p in possible_targets]}\n"
        context += f"Fellow Mafia members: {[p.name for p in mafia_members if p.name != self.player.name]}\n"
        
        if self.memory:
            context += "Recent events:\n"
            for event in self.memory[-5:]:
                context += f"- {event['event']}\n"
                
        if self.suspicions:
            context += "Player suspicions:\n"
            for player, data in self.suspicions.items():
                context += f"- {player}: {data['level']:.2f} suspicion\n"
                
        return context
        
    async def participate_in_discussion(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Participate in day phase discussion"""
        system_message = f"""You are {self.player.name}, a Mafia member pretending to be a townsperson. Deflect suspicion from yourself and other Mafia while casting doubt on innocent players. Act like a concerned townsperson and appear cooperative. Keep your response to maximum 4 sentences and sound natural."""

        context = f"""Game state: {game_state}
Living players: {[p.name for p in living_players]}
Your recent observations: {self.memory[-3:] if self.memory else 'None'}

What do you want to say in the discussion?"""

        response = await self.make_llm_request(context, system_message)
        
        self.update_memory("participated_in_discussion", {
            'statement': response,
            'round': game_state.get('round', 0)
        })
        
        return response
        
    async def vote_for_elimination(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Vote for a player to eliminate"""
        # Don't vote for fellow Mafia members
        possible_votes = [
            p for p in living_players 
            if p.role != Role.MAFIA and p.name != self.player.name
        ]
        
        if not possible_votes:
            return random.choice([p.name for p in living_players if p.name != self.player.name])
            
        system_message = f"""You are {self.player.name}, a Mafia member. Choose who to vote for elimination. 

Priorities:
1. Vote for players who suspect you or other Mafia
2. Follow the crowd to avoid standing out
3. Target special roles if identified
4. Never vote for fellow Mafia members

You can also choose "no_vote" if you don't want to vote.
Respond with only the player's name or "no_vote"."""

        context = f"""Players you can vote for: {[p.name for p in possible_votes]}
Current discussion sentiment: {game_state}
Your suspicions: {self.suspicions}

Who do you vote to eliminate?"""

        response = await self.make_llm_request(context, system_message)
        
        # Check for no vote first
        if "no_vote" in response.lower():
            return "no_vote"
            
        # Extract vote from response
        for player in possible_votes:
            if player.name.lower() in response.lower():
                return player.name
                
        # Fallback to random vote or no vote
        import random
        return random.choice([random.choice(possible_votes).name, "no_vote"])

class TownspersonAgent(BaseAgent):
    """AI Agent for regular Townsperson role"""
    
    def __init__(self, player: Player):
        super().__init__(player, "analytical_cooperative")
        
    async def participate_in_discussion(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Participate in day phase discussion"""
        system_message = f"""You are {self.player.name}, an innocent townsperson trying to find the Mafia. Share observations about suspicious behavior and ask questions to gather information. Build trust with other townspeople and look for inconsistencies. Keep your response to maximum 4 sentences and be collaborative."""

        context = f"""Game state: {game_state}
Living players: {[p.name for p in living_players]}
Your observations: {self.memory[-3:] if self.memory else 'None'}
Your suspicions: {self.suspicions}

What do you want to contribute to the discussion?"""

        response = await self.make_llm_request(context, system_message)
        
        self.update_memory("participated_in_discussion", {
            'statement': response,
            'round': game_state.get('round', 0)
        })
        
        return response
        
    async def vote_for_elimination(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Vote for a player to eliminate"""
        possible_votes = [p.name for p in living_players if p.name != self.player.name]
        
        if not possible_votes:
            return ""
            
        system_message = f"""You are {self.player.name}, a townsperson voting to eliminate someone you suspect is Mafia.

Consider:
- Who has acted most suspiciously?
- Who has been deflecting or aggressive?
- Who benefits from recent eliminations?
- What does your gut tell you?

Respond with only the player's name you want to eliminate."""

        context = f"""Players to choose from: {possible_votes}
Your suspicions: {self.suspicions}
Game events: {self.memory[-5:] if self.memory else 'None'}

Who do you vote to eliminate?"""

        response = await self.make_llm_request(context, system_message)
        
        # Extract vote from response
        for name in possible_votes:
            if name.lower() in response.lower():
                return name
                
        # Use suspicion levels as fallback
        if self.suspicions:
            most_suspicious = max(self.suspicions.items(), key=lambda x: x[1]['level'])
            if most_suspicious[0] in possible_votes:
                return most_suspicious[0]
                
        # Random fallback
        return random.choice(possible_votes)

class DoctorAgent(BaseAgent):
    """AI Agent for Doctor role"""
    
    def __init__(self, player: Player):
        super().__init__(player, "protective_cautious")
        self.previous_saves = []
        
    async def choose_save_target(self, living_players: List[Player]) -> Optional[str]:
        """Choose a player to save during night phase"""
        possible_saves = [p.name for p in living_players]
        
        if not possible_saves:
            return None
            
        system_message = f"""You are {self.player.name}, the Doctor. Each night you can save one player from Mafia elimination. You want to protect the most valuable townspeople.

Your strategy:
- Save suspected special roles (Detective)
- Save strong town leaders
- Save yourself if you feel threatened
- Avoid predictable patterns
- Consider who the Mafia might target

Previous saves: {self.previous_saves}

Respond with only the player's name to save."""

        context = f"""Living players: {possible_saves}
Recent eliminations and events: {self.memory[-3:] if self.memory else 'None'}
Your assessment of who might be targeted: {self.suspicions}

Who do you choose to save tonight?"""

        response = await self.make_llm_request(context, system_message)
        
        # Extract save target from response
        for name in possible_saves:
            if name.lower() in response.lower():
                self.previous_saves.append(name)
                logger.info(f"Doctor {self.player.name} chose to save: {name}")
                return name
                
        # Fallback logic
        if self.player.name in possible_saves and random.random() < 0.3:
            # 30% chance to save self
            self.previous_saves.append(self.player.name)
            return self.player.name
        else:
            # Save random player
            target = random.choice(possible_saves)
            self.previous_saves.append(target)
            return target
            
    async def participate_in_discussion(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Participate in discussion while hiding role"""
        system_message = f"""You are {self.player.name}, the Doctor, but you must hide your role. Act like a regular townsperson while subtly trying to protect the town.

Your approach:
- Act like a concerned townsperson
- Don't reveal your role
- Support logical analysis
- Protect suspected special roles indirectly
- Be helpful but not too prominent

Keep your response natural and avoid suspicion."""

        context = f"""Game state: {game_state}
Your hidden role: Doctor
Recent observations: {self.memory[-3:] if self.memory else 'None'}

What do you say in the discussion?"""

        response = await self.make_llm_request(context, system_message)
        
        self.update_memory("participated_in_discussion", {
            'statement': response,
            'round': game_state.get('round', 0)
        })
        
        return response

    async def vote_for_elimination(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Vote for a player to eliminate while hiding role"""
        possible_votes = [p for p in living_players if p.name != self.player.name]
        
        if not possible_votes:
            return ""
            
        system_message = f"""You are {self.player.name}, the Doctor, voting to eliminate someone. You must hide your role and act like a regular townsperson.

Your strategy:
- Vote to eliminate suspected Mafia members
- Don't reveal you're the Doctor
- Support logical town decisions
- Protect the town's interests

Respond with only the player's name."""

        context = f"""Players you can vote for: {[p.name for p in possible_votes]}
Current discussion sentiment: {game_state}
Your suspicions: {self.suspicions}

Who do you vote to eliminate?"""

        try:
            response = await self.make_llm_request(context, system_message)
            
            # Extract vote from response
            for player in possible_votes:
                if player.name.lower() in response.lower():
                    return player.name
                    
            # Fallback to random vote
            import random
            return random.choice(possible_votes).name
        except Exception as e:
            logger.error(f"Error in doctor voting: {e}")
            import random
            return random.choice(possible_votes).name

class DetectiveAgent(BaseAgent):
    """AI Agent for Detective role"""
    
    def __init__(self, player: Player):
        super().__init__(player, "investigative_strategic")
        self.investigation_results = {}
        
    async def choose_investigation_target(self, living_players: List[Player]) -> Optional[str]:
        """Choose a player to investigate during night phase"""
        possible_targets = [p.name for p in living_players if p.name != self.player.name]
        
        if not possible_targets:
            return None
            
        system_message = f"""You are {self.player.name}, the Detective. Each night you can investigate one player to learn if they are Mafia. Use this information strategically.

Your strategy:
- Investigate most suspicious players first
- Investigate influential players
- Build a clear picture of who is innocent
- Plan how to use your information without revealing your role
- Don't investigate the same player twice

Previous investigations: {list(self.investigation_results.keys())}

Respond with only the player's name to investigate."""

        context = f"""Players to investigate: {possible_targets}
Your suspicions: {self.suspicions}
Recent game events: {self.memory[-3:] if self.memory else 'None'}

Who do you choose to investigate tonight?"""

        response = await self.make_llm_request(context, system_message)
        
        # Extract investigation target from response
        for name in possible_targets:
            if name.lower() in response.lower() and name not in self.investigation_results:
                logger.info(f"Detective {self.player.name} chose to investigate: {name}")
                return name
                
        # Fallback to most suspicious uninvestigated player
        uninvestigated = [name for name in possible_targets if name not in self.investigation_results]
        if uninvestigated:
            if self.suspicions:
                # Choose most suspicious uninvestigated player
                for player, data in sorted(self.suspicions.items(), key=lambda x: x[1]['level'], reverse=True):
                    if player in uninvestigated:
                        return player
            return random.choice(uninvestigated)
            
        return None
        
    def receive_investigation_result(self, target: str, is_mafia: bool):
        """Receive and store investigation result"""
        self.investigation_results[target] = is_mafia
        self.update_memory("investigation_result", {
            'target': target,
            'is_mafia': is_mafia
        })
        
        # Update suspicion based on result
        if is_mafia:
            self.update_suspicion(target, 1.0, "Confirmed Mafia via investigation")
        else:
            self.update_suspicion(target, -0.5, "Confirmed innocent via investigation")
            
    async def participate_in_discussion(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Participate in discussion using investigation knowledge"""
        system_message = f"""You are {self.player.name}, the Detective with secret investigation results. You must guide the town toward eliminating Mafia without revealing your role.

Your knowledge:
- Investigation results: {self.investigation_results}
- You know who is innocent and who is Mafia
- You must subtly influence votes without being obvious
- If you reveal your role, you become a target

Strategy:
- Subtly cast suspicion on confirmed Mafia
- Defend confirmed innocents indirectly
- Use "logical reasoning" to support your knowledge
- Don't be too obvious or you'll be targeted

Keep your response strategic but not revealing."""

        context = f"""Game state: {game_state}
Your secret knowledge: {self.investigation_results}
Living players: {[p.name for p in living_players]}

How do you subtly guide the discussion?"""

        response = await self.make_llm_request(context, system_message)
        
        self.update_memory("participated_in_discussion", {
            'statement': response,
            'round': game_state.get('round', 0)
        })
        
        return response
        
    async def vote_for_elimination(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Vote based on investigation results"""
        possible_votes = [p for p in living_players if p.name != self.player.name]
        
        if not possible_votes:
            return ""
        
        # Vote for confirmed Mafia first
        for player_name, is_mafia in self.investigation_results.items():
            if is_mafia and player_name in [p.name for p in possible_votes]:
                return player_name
                
        # Otherwise vote strategically using detective knowledge
        system_message = f"""You are {self.player.name}, the Detective with secret investigation knowledge. Vote strategically to eliminate Mafia.

Your knowledge: {self.investigation_results}
Strategy: Vote for most suspicious players, prioritize confirmed Mafia, avoid revealing your role.

Respond with only the player's name."""

        context = f"""Players you can vote for: {[p.name for p in possible_votes]}
Your investigation results: {self.investigation_results}
Game state: {game_state}

Who do you vote to eliminate?"""

        try:
            response = await self.make_llm_request(context, system_message)
            
            # Extract vote from response
            for player in possible_votes:
                if player.name.lower() in response.lower():
                    return player.name
                    
            # Fallback to random vote
            import random
            return random.choice(possible_votes).name
        except Exception as e:
            logger.error(f"Error in detective voting: {e}")
            import random
            return random.choice(possible_votes).name

class AgentManager:
    """Manages all AI agents in the game"""
    
    def __init__(self, config):
        self.config = config
        self.agents: Dict[str, BaseAgent] = {}
        
    async def initialize_agents(self, players: List[Player]):
        """Initialize AI agents for all players"""
        for player in players:
            if player.role == Role.MAFIA:
                self.agents[player.name] = MafiaAgent(player)
            elif player.role == Role.DOCTOR:
                self.agents[player.name] = DoctorAgent(player)
            elif player.role == Role.DETECTIVE:
                self.agents[player.name] = DetectiveAgent(player)
            else:
                self.agents[player.name] = TownspersonAgent(player)
                
        logger.info(f"Initialized {len(self.agents)} AI agents")
        
    async def get_mafia_target(self, living_players: List[Player], mafia_members: List[Player]) -> Optional[str]:
        """Get Mafia's target choice for night kill"""
        if not mafia_members:
            return None
            
        # Use first living mafia member to choose target
        for mafia in mafia_members:
            agent = self.agents.get(mafia.name)
            if agent and isinstance(agent, MafiaAgent):
                return await agent.choose_target(living_players, mafia_members)
                
        return None
        
    async def get_doctor_save(self, living_players: List[Player], doctor: Optional[Player]) -> Optional[str]:
        """Get Doctor's save choice"""
        if not doctor:
            return None
            
        agent = self.agents.get(doctor.name)
        if agent and isinstance(agent, DoctorAgent):
            return await agent.choose_save_target(living_players)
            
        return None
        
    async def get_detective_investigation(self, living_players: List[Player], detective: Optional[Player]) -> Optional[str]:
        """Get Detective's investigation choice"""
        if not detective:
            return None
            
        agent = self.agents.get(detective.name)
        if agent and isinstance(agent, DetectiveAgent):
            return await agent.choose_investigation_target(living_players)
            
        return None
        
    async def notify_investigation_result(self, detective: Player, target: str, is_mafia: bool):
        """Notify detective of investigation result"""
        agent = self.agents.get(detective.name)
        if agent and isinstance(agent, DetectiveAgent):
            agent.receive_investigation_result(target, is_mafia)
            
    async def conduct_discussion(self, living_players: List[Player], game_state: Dict[str, Any]) -> str:
        """Conduct day phase discussion among all living players"""
        discussion_statements = []
        
        # Randomize discussion order
        discussion_order = random.sample(living_players, len(living_players))
        
        for player in discussion_order:
            agent = self.agents.get(player.name)
            if agent:
                try:
                    statement = await agent.participate_in_discussion(living_players, game_state)
                    discussion_statements.append(f"{player.name}: {statement}")
                    
                    # Update other agents' memories with this statement
                    for other_agent in self.agents.values():
                        if other_agent != agent:
                            other_agent.update_memory("player_statement", {
                                'speaker': player.name,
                                'statement': statement,
                                'round': game_state.get('round', 0)
                            })
                            
                except Exception as e:
                    logger.error(f"Error in discussion for {player.name}: {e}")
                    discussion_statements.append(f"{player.name}: I need to think about this...")
                    
        return "\n".join(discussion_statements)
        
    async def conduct_voting(self, living_players: List[Player], game_state: Dict[str, Any]) -> Dict[str, str]:
        """Conduct voting phase and return votes"""
        votes = {}
        
        for player in living_players:
            agent = self.agents.get(player.name)
            if agent:
                try:
                    vote = await agent.vote_for_elimination(living_players, game_state)
                    if vote:
                        votes[player.name] = vote
                        logger.info(f"{player.name} votes for {vote}")
                except Exception as e:
                    logger.error(f"Error in voting for {player.name}: {e}")
                    
        return votes
