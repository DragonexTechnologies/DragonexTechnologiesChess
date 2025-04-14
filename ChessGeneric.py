import pygame
import chess
import chess.engine
import sys
import os
import time

# --- Pygame Initialization ---
pygame.init()
print("Pygame initialized.")

# --- Constants ---
INITIAL_SQUARE_SIZE = 80
INFO_PANEL_HEIGHT = 80
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 120
MENU_BUTTON_WIDTH = 150 # Width for menu buttons
MENU_BUTTON_HEIGHT = 50 # Height for menu buttons
BUTTON_MARGIN = 15
FPS = 30
LIGHT_SQUARE = (238, 238, 210)
DARK_SQUARE = (118, 150, 86)
HIGHLIGHT_COLOR = (255, 255, 0, 150)
FONT_SIZE = 28
INFO_FONT_SIZE = 20
MENU_TITLE_FONT_SIZE = 48
MENU_BUTTON_FONT_SIZE = 32
BUTTON_COLOR = (60, 179, 113)
BUTTON_TEXT_COLOR = (255, 255, 255)
BUTTON_HOVER_COLOR = (70, 200, 130) # Consider adding hover effect later if desired
MENU_BG_COLOR = (200, 200, 220)
MIN_BOARD_SIZE = 400  # Minimum size to prevent extreme shrinking
PROMOTION_CHOICE = ['q', 'r', 'n', 'b']
PROMOTION_PANEL_HEIGHT = 50
PROMOTION_BUTTON_WIDTH = 60
ANIMATION_DURATION = 0.3  # Seconds for piece movement animation

# --- Game States ---
MENU = 0
PLAYING = 1
GAME_OVER = 2 # We might implicitly handle this via game_over_text, but state is cleaner
animating = False
animation_start_time = 0
animation_piece = None
animation_start_pos = None
animation_end_pos = None
last_player_move = None # Store the last player move for visual feedback
print("Game state variables initialized.")

# --- Pygame Setup ---
# Initial screen size - might be adjusted by menu later
fixed_size = 1024
screen = pygame.display.set_mode((fixed_size, fixed_size))
screen_width, screen_height = fixed_size, fixed_size # Update width and height
pygame.display.set_caption("Dragonex Technologies Chess")
clock = pygame.time.Clock()
font = pygame.font.Font(None, FONT_SIZE)
info_font = pygame.font.Font(None, INFO_FONT_SIZE)
promotion_font = pygame.font.Font(None, 24)
menu_title_font = pygame.font.Font(None, MENU_TITLE_FONT_SIZE)
menu_button_font = pygame.font.Font(None, MENU_BUTTON_FONT_SIZE)
print("Pygame setup complete (screen, clock, fonts).")

# --- Load Images ---
piece_images_raw = {}
pieces = ['p', 'r', 'n', 'b', 'q', 'k']
colors = ['w', 'b']
print("Loading piece images...")
# Assuming 'assets' folder is in the same directory as the script
assets_path = os.path.join(os.path.dirname(__file__), "assets")
for color in colors:
    for piece in pieces:
        filename = os.path.join(assets_path, f"{color}{piece}.png")
        try:
            piece_images_raw[color + piece] = pygame.image.load(filename).convert_alpha()
            print(f"Loaded image: {filename}")
        except FileNotFoundError:
            print(f"Error: Could not load image: {filename}")
            print("Make sure you have an 'assets' folder with PNG chess piece images (e.g., wp.png, bb.png) in the same directory as the script.")
            pygame.quit()
            sys.exit()
print("Piece images loaded.")

piece_images = {}  # Will store scaled images

def load_and_scale_images(square_size):
    piece_images.clear()
    for key, img in piece_images_raw.items():
        piece_images[key] = pygame.transform.scale(img, (square_size, square_size))

# --- Game State Variables ---
board = chess.Board()
selected_square = None
possible_moves = []
engine = None
engine_process = None
# player_turn = True # Player is always White, starts True
# Let's rename to make it clearer:
is_player_move = True # True if it's the human player's turn (White)
promotion_move = None  # Stores the move that resulted in promotion
game_state = MENU # Start in the menu
engine_difficulty = None # Will be set by the menu (e.g., skill level 1, 10, 20)
game_over_text = None
menu_buttons = {} # To store menu button rects and associated difficulty levels
print("Game state variables initialized.")

# --- Functions ---
def get_square_from_pos(pos, square_size, board_origin):
    board_x, board_y = board_origin
    x, y = pos
    board_size = 8 * square_size
    if board_x <= x < board_x + board_size and board_y <= y < board_y + board_size:
        # Adjust coordinates relative to the board's top-left corner
        rel_x = x - board_x
        rel_y = y - board_y
        col = rel_x // square_size
        row = 7 - (rel_y // square_size) # Invert row for chess notation
        if 0 <= col < 8 and 0 <= row < 8: # Double check bounds
             result = chess.square_name(chess.square(col, row))
             return result
    return None

def get_pos_from_square(square_name, square_size, board_origin):
    board_x, board_y = board_origin
    square_index = chess.parse_square(square_name)
    col = chess.square_file(square_index)
    row = 7 - chess.square_rank(square_index) # Invert row for drawing
    return board_x + col * square_size, board_y + row * square_size

def draw_board(surface, square_size):
    board_size = 8 * square_size
    for row in range(8):
        for col in range(8):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            pygame.draw.rect(surface, color, (col * square_size, row * square_size, square_size, square_size))

def draw_pieces(surface, board, square_size, animating, animation_piece, animation_start_pos, animation_end_pos):
     for square in chess.SQUARES:
         piece = board.piece_at(square)
         if piece:
             color_char = 'w' if piece.color == chess.WHITE else 'b'
             symbol_char = piece.symbol().lower()
             key = color_char + symbol_char
             # Calculate position relative to the surface we are drawing on (the board_surface)
             col = chess.square_file(square)
             row = 7 - chess.square_rank(square)  # Invert row for drawing
             pos = (col * square_size, row * square_size)

             if animating and chess.square_name(square) == animation_piece:
                 # Draw the animating piece at its current interpolated position
                 fraction = (time.time() - animation_start_time) / ANIMATION_DURATION
                 if 0 <= fraction <= 1:
                     x = animation_start_pos[0] + (animation_end_pos[0] - animation_start_pos[0]) * fraction
                     y = animation_start_pos[1] + (animation_end_pos[1] - animation_start_pos[1]) * fraction
                     if key in piece_images_raw:  # Use raw images for scaling on the fly
                         scaled_image = pygame.transform.scale(piece_images_raw[key], (square_size, square_size))
                         surface.blit(scaled_image, (x, y))
                 # If animation is over, it will be reset in the game loop
             else:
                 if key in piece_images_raw:  # Use raw images for scaling on the fly
                     scaled_image = pygame.transform.scale(piece_images_raw[key], (square_size, square_size))
                     surface.blit(scaled_image, pos)
                 else:
                     print(f"Warning: Missing image key {key}")  # Should not happen

def highlight_squares(surface, square_size):
    if selected_square:
        # Calculate position relative to the surface (board_surface)
        square_index = chess.parse_square(selected_square)
        col = chess.square_file(square_index)
        row = 7 - chess.square_rank(square_index)
        s_pos = (col * square_size, row * square_size)

        highlight_surface = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
        pygame.draw.rect(highlight_surface, HIGHLIGHT_COLOR, (0, 0, square_size, square_size))
        surface.blit(highlight_surface, s_pos)

        for move in possible_moves:
            # Ensure the move starts from the selected square before highlighting destination
            if move.from_square == square_index:
                to_col = chess.square_file(move.to_square)
                to_row = 7 - chess.square_rank(move.to_square)
                to_pos = (to_col * square_size, to_row * square_size)
                highlight_surface_move = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
                center_x = square_size // 2
                center_y = square_size // 2
                radius = square_size // 4 # Make the circle smaller
                # Draw a circle indicator for legal moves
                pygame.draw.circle(highlight_surface_move, (0, 0, 0, 80), (center_x, center_y), radius)
                surface.blit(highlight_surface_move, to_pos)


def draw_info_panel(surface, text, turn_is_white, panel_rect, last_move):
     pygame.draw.rect(surface, (220, 220, 220), panel_rect)

     # Determine whose turn it is based on board state
     turn_str = f"Turn: {'White (You)' if turn_is_white else 'Black (AI)'}"
     turn_text = info_font.render(turn_str, True, (0, 0, 0))
     turn_rect = turn_text.get_rect(centery=panel_rect.centery, left=panel_rect.left + 10)
     surface.blit(turn_text, turn_rect)

     # Display last move
     if last_move:
         last_move_text = info_font.render(f"Last Move: {last_move.uci()}", True, (0, 0, 0))
         last_move_rect = last_move_text.get_rect(centery=panel_rect.centery, centerx=panel_rect.centerx)
         surface.blit(last_move_text, last_move_rect)

     # Display game over text if applicable
     if text:
         info_text = info_font.render(text, True, (200, 0, 0))  # Red color for game over
         info_rect = info_text.get_rect(center=panel_rect.center)
         surface.blit(info_text, info_rect)


def create_button(surface, text, rect, color, text_color, font):
    pygame.draw.rect(surface, color, rect, border_radius=5)
    button_text = font.render(text, True, text_color)
    text_rect = button_text.get_rect(center=rect.center)
    surface.blit(button_text, text_rect)
    return rect # Return rect for potential hover/click detection outside this func

def draw_promotion_panel(surface, board_origin, square_size):
    global promotion_move # Make sure we're using the global
    board_x, board_y = board_origin
    color_char = 'w' # Player is always white
    panel_width = len(PROMOTION_CHOICE) * PROMOTION_BUTTON_WIDTH
    # Position panel near the promotion square rank (top for white)
    panel_x = board_x + (8 * square_size - panel_width) // 2
    panel_y = board_y # White promotes at rank 8 (top of the board visually)

    pygame.draw.rect(surface, (200, 200, 200), (panel_x, panel_y, panel_width, PROMOTION_PANEL_HEIGHT))
    buttons_data = [] # Store rect and piece char
    for i, piece_char in enumerate(PROMOTION_CHOICE):
        piece_symbol = color_char + piece_char
        img = pygame.transform.scale(piece_images_raw[piece_symbol], (PROMOTION_BUTTON_WIDTH - 10, PROMOTION_PANEL_HEIGHT - 10))
        button_rect = pygame.Rect(panel_x + i * PROMOTION_BUTTON_WIDTH, panel_y, PROMOTION_BUTTON_WIDTH, PROMOTION_PANEL_HEIGHT)
        img_rect = img.get_rect(center=button_rect.center)
        surface.blit(img, img_rect)
        buttons_data.append({'rect': button_rect, 'piece': piece_char})
    return buttons_data

def handle_promotion_click(pos, promotion_buttons_data):
    global promotion_move, board, is_player_move, game_over_text # Declare globals needed

    if not promotion_move: # Should not happen if called correctly, but safe check
        print("Error: handle_promotion_click called without a pending promotion_move.")
        return False

    for button_data in promotion_buttons_data:
        if button_data['rect'].collidepoint(pos):
            promotion_piece_char = button_data['piece']

            # --- START CHANGE ---
            # promotion_move now holds the base move (e.g., d7c8 squares)
            base_uci = promotion_move.uci() # Get UCI like "d7c8"
            final_uci = base_uci + promotion_piece_char # Append choice, e.g., "d7c8" + "q" -> "d7c8q"
            print(f"Attempting promotion move: {final_uci}")

            try:
                # Create the final move object from the correctly formed UCI string
                promoted_move = chess.Move.from_uci(final_uci)

                # Double-check this constructed move is actually legal in the current position
                if promoted_move in board.legal_moves:
                     board.push(promoted_move)
                     promotion_move = None # Clear promotion state AFTER successful push
                     is_player_move = False # Switch turn to AI
                     game_over_text = check_game_over() # Check if this move ended the game
                     print("Promotion successful. Turn switched to AI.")
                     return True # Indicate promotion was handled
                else:
                    # This could happen if something went very wrong, but good to check
                    print(f"Error: Constructed promotion move {final_uci} is illegal in current board state?")
                    promotion_move = None # Reset promotion state on error
                    return False
            # --- END CHANGE ---

            except ValueError as e: # Catch potential errors from from_uci
                 print(f"Error creating move from UCI '{final_uci}': {e}")
                 promotion_move = None # Reset promotion state on error
                 return False
            except Exception as e:
                 print(f"Error processing promotion click: {e}")
                 promotion_move = None # Reset on error
                 return False
    return False # Click was not on a promotion button

def handle_board_click(pos, square_size, board_origin):
     global selected_square, possible_moves, board, is_player_move, promotion_move, game_over_text, animating, animation_piece, animation_start_time, animation_start_pos, animation_end_pos, last_player_move

     # Get clicked square relative to board origin
     clicked_square_name = get_square_from_pos(pos, square_size, board_origin)

     if not clicked_square_name:
         print("Click outside board")
         return False # Click was outside the board

     clicked_square_index = chess.parse_square(clicked_square_name)
     piece = board.piece_at(clicked_square_index)

     if selected_square is None:
         # Player clicked on a square, potential piece selection
         if piece and piece.color == chess.WHITE: # Player is always White
             selected_square = clicked_square_name
             possible_moves = [move for move in board.legal_moves if move.from_square == clicked_square_index]
             print(f"Selected square: {selected_square}. Possible moves: {[m.uci() for m in possible_moves]}")
             return False # Just selected, no move made yet
         else:
             print("Clicked on empty square or opponent's piece - deselecting.")
             selected_square = None
             possible_moves = []
             return False
     else:
         # A piece was already selected, try to move or deselect
         from_square_index = chess.parse_square(selected_square)

         if clicked_square_name == selected_square:
             # Clicked the same square again - deselect
             print("Deselected square.")
             selected_square = None
             possible_moves = []
             return False

         # Construct potential move (without promotion initially)
         move_uci = selected_square + clicked_square_name
         potential_move = chess.Move.from_uci(move_uci)
         is_promotion = (
             board.piece_at(from_square_index).piece_type == chess.PAWN and
             chess.square_rank(clicked_square_index) == 7 # White promotes on rank 8 (index 7)
         )

         # Check if this exact move (without promotion yet) is legal
         # We need to check with potential promotion possibilities as well
         found_legal_move = False
         actual_move_to_push = None

         for legal_move in board.legal_moves:
             if legal_move.from_square == from_square_index and legal_move.to_square == clicked_square_index:
                 found_legal_move = True
                 actual_move_to_push = legal_move # This includes promotion info if needed
                 break

         if found_legal_move:
             if is_promotion:
                 # --- START CHANGE ---
                 print(f"Promotion condition met for move from {selected_square} to {clicked_square_name}")
                 # Store only the base move information (from/to squares).
                 # We create a move object just holding the squares, ignoring promotion for now.
                 base_move = chess.Move(from_square_index, clicked_square_index)
                 promotion_move = base_move # Store this base move object
                 # --- END CHANGE ---

                 selected_square = None
                 possible_moves = []
                 print("Waiting for promotion selection.")
                 return False # Move sequence initiated but needs promotion choice
             else:
                 # Regular legal move (no changes needed here)
                 print(f"Making move: {actual_move_to_push.uci()}")
                 start_pos = get_pos_from_square(selected_square, square_size, board_origin)
                 end_pos = get_pos_from_square(clicked_square_name, square_size, board_origin)
                 piece = board.piece_at(from_square_index)
                 if piece:
                     start_animation(selected_square, start_pos, end_pos)
                     board.push(actual_move_to_push)
                     last_player_move = actual_move_to_push
                     selected_square = None
                     possible_moves = []
                     is_player_move = False # Switch turn to AI
                     game_over_text = check_game_over() # Check game status
                     print("Move successful. Turn switched to AI.")
                     return True # Move completed
                 else:
                     print("Error: No piece at the starting square of the move.")
                     selected_square = None
                     possible_moves = []
                     return False
         else:
             # Clicked square is not a legal destination, maybe select another piece?
             print(f"Illegal move: {move_uci}. Checking if selecting another piece.")
             if piece and piece.color == chess.WHITE:
                 # Clicked on another white piece - select it instead
                 selected_square = clicked_square_name
                 possible_moves = [move for move in board.legal_moves if move.from_square == clicked_square_index]
                 print(f"Selected new square: {selected_square}. Possible moves: {[m.uci() for m in possible_moves]}")
                 return False
             else:
                 # Clicked on empty or black piece - deselect current
                 print("Clicked on non-legal square - deselecting.")
                 selected_square = None
                 possible_moves = []
                 return False

def make_engine_move():
    global is_player_move, board, game_over_text, animating, animation_piece, animation_start_time, animation_start_pos, animation_end_pos

    if animating:
        return # Don't make a new move while animation is in progress

    if engine and not board.is_game_over():
        print("Engine is thinking...")
        try:
            if engine_difficulty is not None:
                print(f"Engine using Skill Level: {engine_difficulty}")
                engine.configure({"Skill Level": engine_difficulty})
            else:
                print("Warning: Engine difficulty not set, using engine default skill.")

            move_limit = chess.engine.Limit(time=1.0)
            result = engine.play(board, move_limit)

            if result and result.move:
                print(f"Engine move: {result.move.uci()}")
                from_square = chess.square_name(result.move.from_square)
                to_square = chess.square_name(result.move.to_square)
                start_pos = get_pos_from_square(from_square, INITIAL_SQUARE_SIZE, board_origin)
                end_pos = get_pos_from_square(to_square, INITIAL_SQUARE_SIZE, board_origin)
                start_animation(from_square, start_pos, end_pos)
                board.push(result.move)
                game_over_text = check_game_over()
                is_player_move = True  # Switch back to player's turn AFTER successful engine move
            else:
                print("Engine did not return a move (or resigned/drew).")
                if result and result.resigned:
                    game_over_text = "AI Resigned! You Win!"
                elif result and result.draw_offered:
                    game_over_text = "AI Offered Draw"

        except chess.engine.EngineTerminatedError:
            print("Engine terminated unexpectedly.")
            game_over_text = "Engine Error - Game Over"
        except chess.engine.EngineError as e:
            print(f"Stockfish Engine Error: {e}")
            game_over_text = "Engine Error - Game Over"
        except Exception as e:
            print(f"An unexpected error occurred during engine move: {e}")
            import traceback
            traceback.print_exc()
            game_over_text = "Error - Game Over"
    else:
        if not engine: print("Engine move skipped: Engine not available.")
        if board.is_game_over(): print("Engine move skipped: Game is over.")

def check_game_over():
    if board.is_checkmate():
        winner = "Black (AI)" if board.turn == chess.WHITE else "White (You)"
        return f"Checkmate! {winner} wins."
    elif board.is_stalemate():
        return "Stalemate!"
    elif board.is_insufficient_material():
        return "Draw: Insufficient material!"
    elif board.is_seventyfive_moves():
        return "Draw: 75-move rule!"
    elif board.is_fivefold_repetition():
        return "Draw: Fivefold repetition!"
    elif board.is_variant_draw(): # Catches other draw conditions if applicable
        return "Draw!"
    return None # Game is not over

def restart_game():
    global board, selected_square, possible_moves, is_player_move, game_over_text, promotion_move, game_state, animating, animation_piece, animation_start_time, animation_start_pos, animation_end_pos, last_player_move
    print("Restarting game...")
    board = chess.Board() # p this line
    selected_square = None
    possible_moves = []
    is_player_move = True # Player (White) starts
    game_over_text = None
    promotion_move = None
    animating = False
    animation_piece = None
    animation_start_time = 0
    animation_start_pos = None
    animation_end_pos = None
    last_player_move = None

def quit_game():
     global running, engine
     print("Quitting game...")
     running = False
     if engine:
         try:
             engine.quit()
         except chess.engine.EngineTerminatedError:
             print("Engine already terminated.")
         except Exception as e:
             print(f"Error quitting engine: {e}")
     pygame.quit()
     sys.exit()

 # --- Animation Helper Function ---
def start_animation(piece, start_pos, end_pos):
    global animating, animation_start_time, animation_piece, animation_start_pos, animation_end_pos
    animating = True
    animation_start_time = time.time()
    animation_piece = piece
    animation_start_pos = start_pos
    animation_end_pos = end_pos
    print(f"Starting animation for {piece} from {start_pos} to {end_pos}")

# --- Load Stockfish Engine ---
# Define path relative to the script's location
try:
    script_dir = os.path.dirname(__file__) # Get directory of the current script
    # Adjust the relative path to your Stockfish executable
    # Go up one level from script dir, then into stockfish folder
    engine_path_relative = os.path.join("stockfish", "stockfish-generic")#replace with real stockfish path
    engine_path = os.path.join(script_dir, engine_path_relative)
    # For different OS or paths, adjust engine_path accordingly
    # Example for Linux: engine_path = os.path.join(script_dir, "stockfish", "stockfish")
    # Example for specific user path (like your original):
    # engine_path = "C:\\Users\\blake\\Documents\\ChessApp\\stockfish\\stockfish-windows-x86-64-avx2.exe"

    print(f"Attempting to load engine from: {engine_path}")
    # Make sure the path exists before trying to open
    if not os.path.exists(engine_path):
         raise FileNotFoundError(f"Engine executable not found at resolved path: {engine_path}")

    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    # Engine is loaded, but difficulty will be configured later via menu
    print("Stockfish engine loaded successfully.")
except FileNotFoundError as e:
    print(f"Error: Stockfish engine not found. {e}")
    print("Please ensure Stockfish is installed and the path in the script is correct.")
    engine = None # Set engine to None so the game knows it's unavailable
except chess.engine.EngineError as e:
    print(f"Error initializing Stockfish engine: {e}")
    engine = None
except Exception as e:
    print(f"An unexpected error occurred loading the engine: {e}")
    engine = None

# --- Menu Drawing Function ---
def draw_menu(surface):
    global menu_buttons # Allow modification of global dict
    surface.fill(MENU_BG_COLOR)
    menu_buttons.clear() # Clear previous buttons if screen resized

    # Title
    title_text = menu_title_font.render("Select Difficulty", True, (0, 0, 50))
    title_rect = title_text.get_rect(center=(surface.get_width() // 2, surface.get_height() // 4))
    surface.blit(title_text, title_rect)

    # Difficulty Buttons
    difficulties = {"Easy": 1, "Medium": 8, "Hard": 15, "Max": 20} # Label -> Skill Level
    button_y_start = surface.get_height() // 2 - (len(difficulties) * (MENU_BUTTON_HEIGHT + BUTTON_MARGIN)) // 2
    button_x = surface.get_width() // 2 - MENU_BUTTON_WIDTH // 2

    for i, (label, skill) in enumerate(difficulties.items()):
        button_rect = pygame.Rect(button_x, button_y_start + i * (MENU_BUTTON_HEIGHT + BUTTON_MARGIN), MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)
        create_button(surface, label, button_rect, BUTTON_COLOR, BUTTON_TEXT_COLOR, menu_button_font)
        menu_buttons[skill] = button_rect # Store rect keyed by skill level

    # Display engine status
    engine_status = "Engine: Ready" if engine else "Engine: Not Found/Error"
    status_color = (0, 150, 0) if engine else (200, 0, 0)
    status_text = info_font.render(engine_status, True, status_color)
    status_rect = status_text.get_rect(center=(surface.get_width() // 2, surface.get_height() * 0.85))
    surface.blit(status_text, status_rect)

    # Quit Button on Menu
    quit_rect = pygame.Rect(surface.get_width() - BUTTON_WIDTH - BUTTON_MARGIN, surface.get_height() - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT)
    create_button(surface, "Quit", quit_rect, (200, 50, 50), BUTTON_TEXT_COLOR, font) # Use smaller font
    menu_buttons['quit'] = quit_rect # Add quit button to clickable items

# --- Game Loop ---
running = True
load_and_scale_images(INITIAL_SQUARE_SIZE) # Initial image scaling

while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit_game()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                click_pos = event.pos

                if game_state == MENU:
                    # Handle menu clicks
                    for skill, rect in menu_buttons.items():
                        if rect.collidepoint(click_pos):
                            if skill == 'quit':
                                quit_game()
                            elif engine: # Only start if engine is loaded
                                engine_difficulty = skill
                                print(f"Selected difficulty: {skill}")
                                try:
                                    engine.configure({"Skill Level": engine_difficulty})
                                    print(f"Engine Skill Level set to {engine_difficulty}")
                                except Exception as e:
                                    print(f"Error configuring engine: {e}")
                                game_state = PLAYING
                                restart_game() # Reset board for the new game
                            else:
                                print("Cannot start game - Engine not loaded.")
                            break # Exit loop once a button is clicked

                elif game_state == PLAYING:
                    # --- Calculate layout for PLAYING state ---
                    board_size = 8 * INITIAL_SQUARE_SIZE # Use initial square size for fixed board size
                    board_x = (screen_width - board_size) // 2  # Center horizontally
                    board_y = (screen_height - INFO_PANEL_HEIGHT - board_size) // 2 # Center board vertically above info panel
                    board_origin = (board_x, board_y)
                    info_panel_rect = pygame.Rect(0, board_y + board_size, screen_width, INFO_PANEL_HEIGHT)
                    restart_button_rect = pygame.Rect((screen_width - BUTTON_WIDTH) // 2, screen_height - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT)
                    quit_button_rect = pygame.Rect(screen_width - BUTTON_WIDTH - BUTTON_MARGIN, screen_height - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT)

                    # --- Handle PLAYING state clicks ---
                    if promotion_move and is_player_move and not animating:
                        promo_buttons_data = draw_promotion_panel(screen, board_origin, INITIAL_SQUARE_SIZE)
                        if handle_promotion_click(click_pos, promo_buttons_data):
                            last_move = board.peek()
                            start_animation(chess.square_name(last_move.from_square), get_pos_from_square(chess.square_name(last_move.from_square), INITIAL_SQUARE_SIZE, board_origin), get_pos_from_square(chess.square_name(last_move.to_square), INITIAL_SQUARE_SIZE, board_origin))

                    elif is_player_move and not game_over_text and not animating:
                        if board_origin[0] <= click_pos[0] < board_origin[0] + board_size and \
                           board_origin[1] <= click_pos[1] < board_origin[1] + board_size:
                            move_made = handle_board_click(click_pos, INITIAL_SQUARE_SIZE, board_origin)
                            if move_made and board.peek():
                                last_move = board.peek()
                                start_animation(chess.square_name(last_move.from_square), get_pos_from_square(chess.square_name(last_move.from_square), INITIAL_SQUARE_SIZE, board_origin), get_pos_from_square(chess.square_name(last_move.to_square), INITIAL_SQUARE_SIZE, board_origin))

                    # Check button clicks
                    if restart_button_rect.collidepoint(click_pos):
                        restart_game()
                    elif quit_button_rect.collidepoint(click_pos):
                        quit_game()

    # --- Game Logic ---
    if game_state == PLAYING:
        # --- Calculate layout for PLAYING state ---
        board_size = 8 * INITIAL_SQUARE_SIZE # Use initial square size for fixed board size
        board_x = (screen_width - board_size) // 2  # Center horizontally
        board_y = (screen_height - INFO_PANEL_HEIGHT - board_size) // 2 # Center board vertically above info panel
        board_origin = (board_x, board_y)
        info_panel_rect = pygame.Rect(0, board_y + board_size, screen_width, INFO_PANEL_HEIGHT)

        if animating:
            if time.time() - animation_start_time >= ANIMATION_DURATION:
                animating = False
                animation_piece = None
                if not is_player_move and not board.is_game_over() and not promotion_move:
                    make_engine_move()

        elif not is_player_move and not board.is_game_over() and not animating and not promotion_move:
            pygame.time.delay(int(0.2 * 1000))
            make_engine_move()

    # --- Drawing ---
    screen.fill((200, 200, 200)) # Background color

    if game_state == MENU:
        draw_menu(screen)
    elif game_state == PLAYING:
        # --- Calculate layout for PLAYING state (again for drawing) ---
        board_size = 8 * INITIAL_SQUARE_SIZE # Use initial square size for fixed board size
        board_x = (screen_width - board_size) // 2  # Center horizontally
        board_y = (screen_height - INFO_PANEL_HEIGHT - board_size) // 2 # Center board vertically above info panel
        board_origin = (board_x, board_y)
        info_panel_rect = pygame.Rect(0, board_y + board_size, screen_width, INFO_PANEL_HEIGHT)
        restart_button_rect = pygame.Rect((screen_width - BUTTON_WIDTH) // 2, screen_height - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT)
        quit_button_rect = pygame.Rect(screen_width - BUTTON_WIDTH - BUTTON_MARGIN, screen_height - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT)

        # Draw the board at the calculated board_origin
        draw_board(screen.subsurface((board_origin[0], board_origin[1], board_size, board_size)), INITIAL_SQUARE_SIZE)

        # Highlight squares also needs to be drawn on the board's surface
        highlight_surface = pygame.Surface((board_size, board_size), pygame.SRCALPHA)
        highlight_squares(highlight_surface, INITIAL_SQUARE_SIZE)
        screen.blit(highlight_surface, board_origin)

        # Draw pieces at the calculated board_origin
        draw_pieces(screen.subsurface((board_origin[0], board_origin[1], board_size, board_size)), board, INITIAL_SQUARE_SIZE, animating, animation_piece, animation_start_pos, animation_end_pos)

        draw_info_panel(screen, game_over_text, is_player_move, info_panel_rect, last_player_move if 'last_player_move' in locals() else None)

        if promotion_move and is_player_move and not animating:
            draw_promotion_panel(screen, board_origin, INITIAL_SQUARE_SIZE)

        # Draw buttons
        create_button(screen, "Restart", restart_button_rect, BUTTON_COLOR, BUTTON_TEXT_COLOR, font)
        create_button(screen, "Quit", quit_button_rect, (200, 50, 50), BUTTON_TEXT_COLOR, font)

    pygame.display.flip()
    clock.tick(FPS)