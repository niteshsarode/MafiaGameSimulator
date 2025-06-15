"""
Web server for Mafia game visualization and interaction
"""

from flask import Flask, render_template, jsonify, request
import asyncio
import json
import logging
import threading
from turn_based_game import TurnBasedMafiaGame

app = Flask(__name__)
logger = logging.getLogger(__name__)

class WebGameController:
    def __init__(self):
        self.turn_based_game = None
        self.game_running = False
        
    def start_new_game(self):
        """Start a new turn-based game"""
        try:
            self.turn_based_game = TurnBasedMafiaGame()
            
            # Initialize the game in a background thread
            def initialize_game():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.turn_based_game.initialize_new_game())
                    self.game_running = result.get("success", False)
                finally:
                    loop.close()
            
            thread = threading.Thread(target=initialize_game)
            thread.daemon = True
            thread.start()
            thread.join()  # Wait for initialization to complete
            
            return {"success": True, "message": "Turn-based game initialized"}
        except Exception as e:
            logger.error(f"Failed to start game: {e}")
            return {"error": str(e)}
    
    def get_game_state(self):
        """Get current game state"""
        if not self.turn_based_game:
            return {
                "phase": "setup",
                "round": 0,
                "players": [],
                "living_count": 0,
                "mafia_count": 0,
                "town_count": 0,
                "is_game_over": False,
                "winner": None,
                "game_running": False,
                "can_advance": False,
                "current_turn": {},
                "game_history": []
            }
            
        try:
            return self.turn_based_game.get_game_state()
        except Exception as e:
            logger.error(f"Failed to get game state: {e}")
            return {
                "error": str(e),
                "phase": "error",
                "round": 0,
                "players": [],
                "living_count": 0,
                "mafia_count": 0,
                "town_count": 0,
                "is_game_over": False,
                "winner": None,
                "game_running": False,
                "can_advance": False,
                "current_turn": {},
                "game_history": []
            }
    
    def execute_next_turn(self):
        """Execute the next turn"""
        if not self.turn_based_game:
            return {"error": "No game initialized"}
            
        try:
            def run_turn():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self.turn_based_game.execute_next_turn())
                finally:
                    loop.close()
            
            thread = threading.Thread(target=run_turn)
            thread.daemon = True
            thread.start()
            thread.join()  # Wait for turn to complete
            
            return {"success": True, "message": "Turn executed"}
        except Exception as e:
            logger.error(f"Failed to execute turn: {e}")
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

@app.route('/api/next_turn', methods=['POST'])
def next_turn():
    """Execute the next turn"""
    result = game_controller.execute_next_turn()
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