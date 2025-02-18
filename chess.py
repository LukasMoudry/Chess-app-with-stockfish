import os
import threading
import pygame
import chess
from stockfish import Stockfish

# Define a custom event for the AI move
AI_MOVE_EVENT = pygame.USEREVENT + 1

class ChessGame:
    def __init__(self):
        # -------------------------------------------------------
        #     CONFIGURATION
        # -------------------------------------------------------
        self.STOCKFISH_PATH = r"C:\Users\Admin\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
        self.WIDTH, self.HEIGHT = 800, 400
        self.BOARD_SIZE = 400
        self.BAR_WIDTH = 60
        self.SQUARE_SIZE = self.BOARD_SIZE // 8

        # Colors
        self.WHITE  = (255, 255, 255)
        self.BLACK  = (0, 0, 0)
        self.GRAY   = (128, 128, 128)
        self.GREEN  = (0, 200, 0)
        self.RED    = (200, 0, 0)
        self.YELLOW = (255, 255, 0)
        self.ORANGE = (255, 165, 0)  # Used to highlight the AI's last move

        # -------------------------------------------------------
        #     INITIALIZATION
        # -------------------------------------------------------
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Chess with AI's Move Highlight")
        self.font = pygame.font.SysFont("Arial", 20)

        # Preload piece images with error handling.
        self.images = self.load_images()

        # Initialize Stockfish engine with error handling.
        try:
            self.stockfish = Stockfish(self.STOCKFISH_PATH)
            self.stockfish.set_skill_level(5)  # Skill level from 0 to 20.
        except Exception as e:
            print("Error initializing Stockfish:", e)
            self.stockfish = None

        # Game state variables.
        self.board = chess.Board()
        self.selected_square = None
        self.last_ai_move = None
        self.current_score = 0.0
        self.ai_move_scheduled = False

    def load_images(self):
        """Preload all piece images from the assets folder with error handling."""
        images = {}
        asset_folder = "assets"
        pieces = ['P', 'N', 'B', 'R', 'Q', 'K']
        # We'll use 'w' for white pieces and 'b' for black pieces.
        for color_prefix in ['w', 'b']:
            for piece in pieces:
                key = color_prefix + piece
                image_path = os.path.join(asset_folder, f"{key}.png")
                try:
                    img = pygame.image.load(image_path)
                    img = pygame.transform.scale(img, (self.SQUARE_SIZE, self.SQUARE_SIZE))
                    images[key] = img
                except Exception as e:
                    print(f"Error loading image {image_path}: {e}")
                    # Create a dummy surface if the image is not found.
                    dummy = pygame.Surface((self.SQUARE_SIZE, self.SQUARE_SIZE))
                    dummy.fill(self.GRAY)
                    images[key] = dummy
        return images

    def get_piece_image(self, piece: chess.Piece):
        """Return the preloaded image for the given chess piece."""
        color_prefix = "w" if piece.color else "b"
        piece_type = piece.symbol().upper()  # 'P','N','B','R','Q','K'
        key = color_prefix + piece_type
        return self.images.get(key)

    def get_evaluation_score(self) -> float:
        """Get the evaluation of the current board position (clamped between -5 and 5)."""
        if self.stockfish:
            try:
                self.stockfish.set_fen_position(self.board.fen())
                evaluation = self.stockfish.get_evaluation()
            except Exception as e:
                print("Error evaluating position:", e)
                return 0.0
            if evaluation["type"] == "cp":
                raw_score = evaluation["value"] / 100.0
            elif evaluation["type"] == "mate":
                raw_score = 5.0 if evaluation["value"] > 0 else -5.0
            else:
                raw_score = 0.0
            return max(-5.0, min(5.0, raw_score))
        else:
            return 0.0

    def highlight_square(self, square: int, color, width=3):
        """Highlight the given board square (0-63) with a colored rectangle outline."""
        col = square % 8
        row = 7 - (square // 8)
        rect = pygame.Rect(col * self.SQUARE_SIZE, row * self.SQUARE_SIZE,
                           self.SQUARE_SIZE, self.SQUARE_SIZE)
        pygame.draw.rect(self.screen, color, rect, width)

    def schedule_ai_move(self, delay_ms=3000):
        """
        Schedule the AI move by setting a timer event.
        This avoids using a blocking sleep call.
        """
        pygame.time.set_timer(AI_MOVE_EVENT, delay_ms)
        self.ai_move_scheduled = True

    def ai_move(self):
        """Let the AI (Stockfish) determine and play its move."""
        if self.stockfish:
            try:
                self.stockfish.set_fen_position(self.board.fen())
                best_uci = self.stockfish.get_best_move()
            except Exception as e:
                print("Error getting AI move:", e)
                best_uci = None
            if best_uci:
                move = chess.Move.from_uci(best_uci)
                if move in self.board.legal_moves:
                    self.board.push(move)
                    self.last_ai_move = move

    def draw_chessboard(self):
        """Draw the chess board squares, highlight selected and AI move squares, and draw all pieces."""
        # Draw board squares.
        for row in range(8):
            for col in range(8):
                square_color = self.WHITE if (row + col) % 2 == 0 else self.GRAY
                pygame.draw.rect(
                    self.screen,
                    square_color,
                    (col * self.SQUARE_SIZE, row * self.SQUARE_SIZE,
                     self.SQUARE_SIZE, self.SQUARE_SIZE)
                )

        # Highlight the user's selected square.
        if self.selected_square is not None:
            self.highlight_square(self.selected_square, self.YELLOW, width=3)

        # Highlight the AI's last move.
        if self.last_ai_move is not None:
            self.highlight_square(self.last_ai_move.from_square, self.ORANGE, width=3)
            self.highlight_square(self.last_ai_move.to_square, self.ORANGE, width=3)

        # Draw pieces on the board.
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece:
                col = sq % 8
                row = 7 - (sq // 8)
                image = self.get_piece_image(piece)
                if image:
                    self.screen.blit(image, (col * self.SQUARE_SIZE, row * self.SQUARE_SIZE))

    def draw_evaluation_bar(self, score: float):
        """Draw the evaluation bar on the right side along with numeric labels."""
        bar_x = self.BOARD_SIZE
        pygame.draw.rect(self.screen, self.BLACK, (bar_x, 0, self.BAR_WIDTH, self.HEIGHT))
        normalized = (score + 5.0) / 10.0  # Normalize score from [-5,5] to [0,1]
        bar_height = int(normalized * self.HEIGHT)
        bar_color = self.GREEN if score >= 0 else self.RED
        bar_y = self.HEIGHT - bar_height
        pygame.draw.rect(self.screen, bar_color, (bar_x + 10, bar_y, self.BAR_WIDTH - 20, bar_height))

        # Draw labels.
        white_label = self.font.render("White", True, self.WHITE)
        black_label = self.font.render("Black", True, self.WHITE)
        self.screen.blit(white_label, (bar_x + 5, 5))
        self.screen.blit(black_label, (bar_x + 5, self.HEIGHT - 25))

        # Draw numeric evaluation.
        score_text = f"{score:+.1f}"
        eval_surf = self.font.render(score_text, True, self.WHITE)
        text_x = bar_x + (self.BAR_WIDTH // 2) - (eval_surf.get_width() // 2)
        text_y = (self.HEIGHT // 2) - (eval_surf.get_height() // 2)
        self.screen.blit(eval_surf, (text_x, text_y))

    def update_display(self):
        """Redraw the board, evaluation bar, and, if the game is over, a game over message."""
        self.screen.fill(self.BLACK)
        self.draw_chessboard()
        self.draw_evaluation_bar(self.current_score)
        if self.board.is_game_over():
            result_text = f"Game Over! Result: {self.board.result()}"
            text_surf = self.font.render(result_text, True, self.WHITE)
            self.screen.blit(text_surf, (10, self.BOARD_SIZE + 10))
        pygame.display.flip()
        pygame.event.pump()

    def run(self):
        """Main loop of the game."""
        running = True
        clock = pygame.time.Clock()
        self.current_score = self.get_evaluation_score()

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN and not self.board.is_game_over():
                    x, y = event.pos
                    # Only process clicks on the board area.
                    if x < self.BOARD_SIZE and y < self.BOARD_SIZE:
                        col = x // self.SQUARE_SIZE
                        row = y // self.SQUARE_SIZE
                        chess_row = 7 - row
                        square_clicked = chess_row * 8 + col

                        # First click: select a piece.
                        if self.selected_square is None:
                            piece = self.board.piece_at(square_clicked)
                            if piece and piece.color == self.board.turn:
                                self.selected_square = square_clicked
                        else:
                            # Second click: attempt to make a move.
                            move = chess.Move(from_square=self.selected_square, to_square=square_clicked)
                            if move in self.board.legal_moves:
                                self.board.push(move)
                                self.selected_square = None
                                self.current_score = self.get_evaluation_score()
                                self.update_display()
                                # Schedule the AI move if the game isn't over.
                                if not self.board.is_game_over():
                                    self.schedule_ai_move(delay_ms=3000)
                            else:
                                # Invalid move feedback.
                                print("Invalid move attempted.")
                                self.selected_square = None

                elif event.type == pygame.KEYDOWN:
                    # Press 'U' to undo a move.
                    if event.key == pygame.K_u:
                        if len(self.board.move_stack) >= 1:
                            self.board.pop()
                            self.current_score = self.get_evaluation_score()
                            self.update_display()
                    # Press 'R' to restart the game.
                    elif event.key == pygame.K_r:
                        self.board.reset()
                        self.selected_square = None
                        self.last_ai_move = None
                        self.current_score = self.get_evaluation_score()
                        self.update_display()

                elif event.type == AI_MOVE_EVENT:
                    # Cancel the timer event.
                    pygame.time.set_timer(AI_MOVE_EVENT, 0)
                    self.ai_move_scheduled = False
                    if not self.board.is_game_over():
                        self.ai_move()
                        self.current_score = self.get_evaluation_score()
                        self.update_display()

            self.update_display()
            clock.tick(30)

        pygame.quit()

if __name__ == "__main__":
    game = ChessGame()
    game.run()
