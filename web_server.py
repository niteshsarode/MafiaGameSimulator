"""
Web server for Mafia game visualization and interaction
"""

from flask import Flask, render_template, jsonify, request
import asyncio
import json
import logging
import threading
from main import MafiaGameSimulation
from config import GameConfig

app = Flask(__name__)
logger = logging.getLogger(__name__)

class WebGameController:
    def __init__(self):
        self.current_simulation = None
        self.game_running = False
        self.game_state = {}
        
    def start_new_game(self):
        """Start a new game simulation"""
        if self.game_running:
            return {"error": "Game already running"}
            
        try:
            config = GameConfig()
            self.current_simulation = MafiaGameSimulation(config)
            
            # Run simulation in background thread
            def run_simulation():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.current_simulation.run_simulation())
                finally:
                    loop.close()
                    self.game_running = False
            
            self.game_running = True
            thread = threading.Thread(target=run_simulation)
            thread.daemon = True
            thread.start()
            
            return {"success": True, "message": "Game started"}
        except Exception as e:
            logger.error(f"Failed to start game: {e}")
            return {"error": str(e)}
    
    def get_game_state(self):
        """Get current game state"""
        if not self.current_simulation:
            return {"error": "No active game"}
            
        try:
            game = self.current_simulation.game
            players_data = []
            
            for player in game.players:
                players_data.append({
                    "name": player.name,
                    "role": player.role.value if player.role else "unknown",
                    "alive": player.is_alive,
                    "death_round": player.death_round
                })
            
            return {
                "phase": game.current_phase.value,
                "round": game.current_round,
                "players": players_data,
                "living_count": len(game.get_living_players()),
                "mafia_count": len(game.get_mafia_members()),
                "town_count": len(game.get_townspeople()),
                "is_game_over": game.is_game_over(),
                "winner": game.get_winner(),
                "game_running": self.game_running
            }
        except Exception as e:
            logger.error(f"Failed to get game state: {e}")
            return {"error": str(e)}

# Global game controller
game_controller = WebGameController()

@app.route('/')
def index():
    """Serve the main game interface"""
    return render_template('index.html')

@app.route('/api/start_game', methods=['POST'])
def start_game():
    """Start a new game"""
    result = game_controller.start_new_game()
    return jsonify(result)

@app.route('/api/game_state')
def get_game_state():
    """Get current game state"""
    state = game_controller.get_game_state()
    return jsonify(state)

@app.route('/api/game_history')
def get_game_history():
    """Get game history if available"""
    try:
        with open('game_history.json', 'r') as f:
            history = json.load(f)
        return jsonify({"history": history})
    except FileNotFoundError:
        return jsonify({"history": []})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)