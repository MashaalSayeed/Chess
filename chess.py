import pygame

from pieces import Pawn, Piece, Rook, Knight, Bishop, Queen, King, Block, Position
from pieces import BLOCK_SIZE, GREY


# BASIC CONFIGURATIONS
SCREENX, SCREENY = 800, 530
FONT = 'Arial'
FPS = 30

BOARD_RECT = 25, 25, 480, 480
FILES = 'abcdefgh'
WHITE = (255, 255, 255)

PIECE_SYMBOLS = {
    'P': Pawn,
    'R': Rook,
    'N': Knight,
    'B': Bishop,
    'Q': Queen,
    'K': King
}


def resolve_position(notation):
    x = FILES.index(notation[0])
    y = int(notation[1]) - 1
    return Position(x, y)


class Move:
    def __init__(self, piece, newpos):
        self.oldpos = piece.pos
        self.newpos = newpos
        self.piece = piece


class Board:
    def __init__(self, fen_notation='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        # Current player color
        self.turn = 'WHITE'
        self.in_check = False
        self.in_mate = False
        self.board: list[list[Piece]] = []
        # Number of moves without capture / pawn movement (Tie)
        self.move50 = 0
        self.fullmoves = 0

        # En Passant
        self.ep_square: Position = None

        # Sprite groups one for all pieces and one for all sprites
        self.all_sprites = pygame.sprite.Group()
        self.piece_sprites = pygame.sprite.Group()

        # 2 seperate lists for the board and their respective blocks (Block class)
        self.create_blocks()
        self.create_board(fen_notation)

        self.history: list[Move] = []

    def get_piece(self, pos):
        return self.board[pos.y][pos.x]
    
    def find_piece(self, piece=None, color=None, pos=None):
        "Finds a piece with the given conditions"
        return [p for p in self.piece_sprites if ((not piece or p.piece == piece) and (not color or p.color == color))]
    
    def get_block(self, pos):
        return self.blocks[pos.y][pos.x]

    def get_move_notation(
        self, piece, oldpos, newpos, captured=False, castling=False,
        promotion=None
    ):
        "Incomplete algebraic move notation"
        if castling:
            return 'O-O' if oldpos.x < newpos.x else 'O-O-O'

        destination = newpos.symbol()
        if piece.piece == 'PAWN':
            piece_symbol = FILES[oldpos.x]
            if not captured:
                return destination
        else:
            piece_symbol = piece.symbol.upper()

        capture = "x" if captured else ""
        promotion_suffix = f"={promotion.symbol.upper()}" if promotion else ""
        check_suffix = ""
        if self.in_check and self.in_mate:
            check_suffix = "#"
        elif self.in_check:
            check_suffix = "+"

        return f"{piece_symbol}{capture}{destination}{check_suffix}{promotion_suffix}"

    def copy_board(self):
        "Returs a copy of the 2d board"
        return [[c for c in r] for r in self.board]

    def get_moves(self, piece):
        moves = piece.moves(self.board)
        # Check if castling is possible
        is_king = piece.piece == 'KING'
        if is_king and not self.in_check:
            rook1, rook2 = self.rooks[self.turn]
            moves += piece.check_castling(self.board, rook1, rook2)
        elif piece.piece == 'PAWN' and self.ep_square and piece.check_en_passant(self.ep_square):
            moves += [self.ep_square]
        
        # validate every move
        valid_moves = []
        for move in moves:
            boardcpy = self.copy_board()
            boardcpy[piece.y][piece.x] = None
            boardcpy[move.y][move.x] = piece
            if not self.is_check(boardcpy, pos=move, is_king=is_king):
                valid_moves.append(move)
        return valid_moves
    
    def create_blocks(self):
        self.blocks = [[] for _ in range(8)]
        for i in range(8):
            for j in range(8):
                self.blocks[i].append(Block(j, i, (i+j)%2 == 0))

    def create_board(self, fen):
        "Create the board UI and place chess pieces on the board"
        fields = fen.split()
        ranks = fields[0].split('/')
        for y, rank in enumerate(ranks):
            self.board.append([])
            x = 0
            for square in rank:
                if square.isdigit():
                    x += int(square)
                    self.board[y].extend([None for _ in range(int(square))])
                else:
                    piece = PIECE_SYMBOLS[square.upper()]
                    color = 'WHITE' if square.isupper() else 'BLACK'
                    self.board[y].append(piece(Position(x, y), color))
                    x += 1
        
        self.piece_sprites.add(self.board[0:2], self.board[6:8])
        self.all_sprites.add(self.blocks, self.piece_sprites)
        
        # Store kings for both players, useful for checks and castling
        self.kings = {
            'WHITE': self.find_piece('KING', 'WHITE')[0], 
            'BLACK': self.find_piece('KING', 'BLACK')[0]
        }
        self.rooks = {
            'WHITE': (self.get_piece(Position(0, 7)), self.get_piece(Position(7, 7))),
            'BLACK': (self.get_piece(Position(0, 0)), self.get_piece(Position(7, 0)))
        }

        self.turn = 'WHITE' if fields[1] == 'w' else 'BLACK'
        self.set_fen_castling(fields[2])
        self.ep_square = resolve_position(fields[3]) if fields[3] != '-' else None
        self.move50 = int(fields[4])
        self.fullmoves = int(fields[5])
        self.print_board(self.board)

    def set_fen_castling(self, castling):
        self.kings['WHITE'].castling = ['Q' in castling, 'K' in castling]
        self.kings['BLACK'].castling = ['q' in castling, 'k' in castling]

    def _move_piece(self, piece, newpos):
        self.board[piece.y][piece.x] = None
        piece.move(newpos)
        self.board[newpos.y][newpos.x] = piece

    def remove_piece(self, piece):
        piece.kill()
        self.board[piece.y][piece.x] = None

    def move_piece(self, piece, newpos):
        "Move a chess piece in the board"
        # Deselect last move
        if self.history:
            last_move = self.history[-1]
            self.get_block(last_move.oldpos).deselect()
            self.get_block(last_move.newpos).deselect()

        # Get the original piece on the board
        capture_piece = self.board[newpos.y][newpos.x]
        if isinstance(piece, Pawn) and newpos == self.ep_square:
            capture_piece = self.board[newpos.y - piece.increment][newpos.x]

        if isinstance(piece, Pawn) or capture_piece:
            self.move50 = 0
            if capture_piece:
                self.remove_piece(capture_piece)
        else:
            self.move50 += 1

        # Store original positions for future reference
        oldpos = piece.pos
        self.get_block(oldpos).select()
        self.get_block(newpos).select()
        self.history.append(Move(piece, newpos))

        # assume the king is not in check (validating moves was done above)
        king = self.kings[self.turn]
        self.get_block(king.pos).check(False)

        castling = False
        self.ep_square = None
        promotion = None
        if piece.piece == 'KING':
            piece.castling = [False, False]
            if abs(newpos.x - oldpos.x) == 2:
                castling = True
                rook = self.board[piece.y][7 if (newpos.x - oldpos.x) > 0 else 0]
                diff = 1 if rook.x == 0 else -1
                self._move_piece(rook, newpos.move(diff, 0))
        elif piece.piece == 'ROOK':
            side = self.rooks[self.turn].index(piece)
            king.castling[side] = False
        elif piece.piece == 'PAWN':
            # Moved 2 spaces, check en 
            if abs(newpos.y - oldpos.y) == 2:
                self.ep_square = Position(newpos.x, newpos.y - piece.increment)

            # Pawn Promotion...
            if newpos.y in (0, 7):
                # Just gonna promote it to queen cuz... why not
                # First kill the original pawn
                self.remove_piece(piece)
                # Create the queen and add it to sprite groups and board
                promotion = Queen(newpos, self.turn)
                self.add_piece(promotion)
                self.board[newpos.y][newpos.x] = promotion
        
        # Change coordinates of the moving piece
        self._move_piece(piece, newpos)

        self.turn = 'BLACK' if self.turn == 'WHITE' else 'WHITE'
        self.in_check = self.is_check(self.board)
        self.in_mate = self.is_mate()
        notation = self.get_move_notation(
            piece, oldpos, newpos, captured=capture_piece, 
            castling=castling, promotion=promotion
        )
        print(notation)

        king = self.kings[self.turn]
        self.get_block(king.pos).check(self.in_check)
        self.print_board(self.board)

    def is_check(self, board, pos=None, is_king=False):
        "Look for a check, return True if it is a checkmate"
        # Get all enemy pieces that do not occupy x,y (place we are going to put our piece)
        enemies = [e for e in self.piece_sprites if e.color != self.turn and e.pos != pos]
        king = self.kings[self.turn]

        for e in enemies:
            # Loop through all enemy moves and see if the king's position lies in it
            moves = e.moves(board)
            if not is_king and king.pos in moves:
                return True
            if is_king and pos in moves:
                return True
        return False

    def add_piece(self, sprite):
        "Add the sprite back to sprite groups"
        self.all_sprites.add(sprite)
        self.piece_sprites.add(sprite)

    def is_mate(self):
        "Look for a mate, see if player has any other possible moves"
        mate = True
        pieces = [p for p in self.piece_sprites if p.color == self.turn]

        for p in pieces:
            # Once we have found it is not a mate break
            if not mate:
                break

            for move in p.moves(self.board):
                # Simulate all posible moves and see if any are valid
                boardcpy = self.copy_board()
                boardcpy[move.y][move.x] = p
                boardcpy[p.y][p.x] = None

                if not self.is_check(boardcpy, pos=move, is_king=isinstance(p, King)):
                    mate = False
                    break
        return mate
    
    def print_board(self, board):
        string = '=======================\n'
        string += '  +-----------------+\n'
        for i, row in enumerate(board):
            string += f'{str(8 - i)} | '
            for piece in row:
                string += f'{piece.symbol} ' if piece else '. '
            string += '|\n'
        string += '  +-----------------+\n'
        string += '    a b c d e f g h \n'
        string += '======================='
        print(string)


class Game:
    def __init__(self):
        # Initialize pygame stuff
        pygame.init()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((SCREENX, SCREENY))
        self.board_surface = pygame.Surface(BOARD_RECT[2:])
        self.font = pygame.font.SysFont(FONT, 15, True)
        self.running = True

        self.create_ui()
        self.run()
    
    def create_ui(self):
        for i in range(1, 9):
            text_surf = self.font.render(str(9-i), 1, WHITE)
            text_rect = text_surf.get_rect(centerx=BOARD_RECT[0]/2, centery=BLOCK_SIZE[1]*i)
            self.screen.blit(text_surf, text_rect)

            text_surf = self.font.render(FILES[i-1], 1, WHITE)
            text_rect = text_surf.get_rect(centerx=BLOCK_SIZE[0]*i, centery=SCREENY-BOARD_RECT[1]/2)
            self.screen.blit(text_surf, text_rect)

        board_width = BOARD_RECT[3] + BOARD_RECT[0] * 2
        self.side_screen = pygame.Surface((SCREENX - board_width, SCREENY))
        self.side_screen.fill('grey')
        self.screen.blit(self.side_screen, (board_width, 0))

    def select_piece(self):
        "Get the selected piece, unselect if already selected, get all valid moves"
        pos = pygame.mouse.get_pos()
        clicked_sprites = [s for s in self.board.piece_sprites if s.rect.move(*BOARD_RECT[:2]).collidepoint(pos)]

        if len(clicked_sprites) == 1 and clicked_sprites[0].color == self.board.turn:
            # unselect previously selected piece
            if self.selected:
                self.board.get_block(self.selected).deselect()

            self.selected = clicked_sprites[0]
            self.valid_moves = self.board.get_moves(self.selected)
            self.board.get_block(self.selected).select()
    
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and not self.selected:
            # If no piece is selected, select a piece
            self.select_piece()
        elif event.type == pygame.MOUSEBUTTONDOWN and self.selected:
            # else move the piece if the position is valid
            # calculate square matrix coordinates of mouse
            x, y = pygame.mouse.get_pos()
            x = int((x - BOARD_RECT[0]) // BLOCK_SIZE[0])
            y = int((y - BOARD_RECT[1]) // BLOCK_SIZE[1])

            if (x, y) in self.valid_moves:
                self.board.get_block(self.selected).deselect()
                self.board.move_piece(self.selected, Position(x, y))
                self.valid_moves = []
                self.selected = None

                # Mate: No move possible
                if self.board.in_mate:
                    self.running = False
                    if self.board.in_check:
                        print("Checkmate:", self.board.turn, "has lost")
                    else:
                        print("Stalemate: It's a tie!")

                if self.board.move50 >= 50:
                    self.running = False
                    print("Tie: 50 moves without a capture or a pawn movement")
            else:
                self.select_piece()

    def run(self):
        "Main game loop"
        self.board = Board()
        self.selected = None
        self.valid_moves = []

        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)

            # Draw everything
            #self.board.piece_sprites.update()
            self.board.all_sprites.draw(self.board_surface)
            # Show all possible move sets as circle dots
            for mx, my in self.valid_moves:
                cx = int(BLOCK_SIZE[0] * (mx + 0.5))
                cy = int(BLOCK_SIZE[1] * (my + 0.5))

                pygame.draw.circle(self.board_surface, GREY, (cx, cy), 10)
            
            self.screen.blit(self.board_surface, BOARD_RECT)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    game = Game()
