import pygame

from pieces import Pawn, Piece, Rook, Knight, Bishop, Queen, King, Block, Position
from pieces import BLOCK_SIZE, GREY


# BASIC CONFIGURATIONS
SCREENX, SCREENY = 530, 530
FONT = 'Arial'
FPS = 30

BOARD_RECT = 25, 25, 480, 480
BLOCK_SIZE = 60, 60
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

STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

# Credits: https://www.pygame.org/wiki/Spritesheet
class Spritesheet:
    def __init__(self, filename):
        self.sheet = pygame.image.load(filename)
        self.sprites = {}

    def image_at(self, rect: pygame.Rect, colorkey=None):
        "Loads image from a pygame.Rect"
        image = pygame.Surface(rect.size).convert_alpha()
        image.blit(self.sheet, (0, 0), rect)
        if colorkey is not None:
            if colorkey == -1:
                colorkey = image.get_at((0,0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)
        return image

    def load_spritemap(self, filename, colorkey=None):
        with open(filename) as map:
            for line in map.readlines():
                name, x, y, w, h = line.strip().split(',')
                rect = pygame.Rect(int(x), int(y), int(w), int(h))
                self.sprites[name] = self.image_at(rect, colorkey=colorkey)


class Move:
    def __init__(self, piece: Piece, newpos: Position):
        self.oldpos = piece.pos
        self.newpos = newpos
        self.piece = piece

    def to_uci(self):
        return self.oldpos.symbol() + self.newpos.symbol()


class Board:
    def __init__(self, fen_notation=STARTING_FEN):
        # Current player color
        self.turn = 'WHITE'
        self.in_check = False
        self.in_mate = False
        self.board: list[list[Piece]] = [[None for _ in range(8)] for _ in range(8)]
        
        # Number of moves without capture / pawn movement (Tie)
        self.move50 = 0
        self.fullmoves = 1

        # En Passant
        self.ep_square: Position = None

        # Sprite group for all pieces
        self.pieces = set() #_sprites = pygame.sprite.Group()
        self.create_board(fen_notation)

        self.history: list[Move] = []

    def get_piece(self, pos: Position):
        return self.board[pos.y][pos.x]
    
    def get_current_king(self):
        return self.kings[self.turn]
    
    def find_piece(self, piece=None, color=None, pos=None):
        "Finds a piece with the given conditions"
        return [p for p in self.pieces if ((not piece or p.piece == piece) and (not color or p.color == color))]

    def create_board(self, fen: str):
        "Create the board UI and place chess pieces on the board"
        fields = fen.split()
        ranks = fields[0].split('/')
        for y, rank in enumerate(ranks):
            x = 0
            for square in rank:
                if square.isdigit():
                    x += int(square)
                else:
                    piece = PIECE_SYMBOLS[square.upper()]
                    color = 'WHITE' if square.isupper() else 'BLACK'
                    self.add_piece(piece(Position(x, y), color))
                    x += 1

        # Store kings for both players, useful for checks and castling
        self.kings = {
            'WHITE': self.find_piece('KING', 'WHITE')[0], 
            'BLACK': self.find_piece('KING', 'BLACK')[0]
        }

        self.turn = 'WHITE' if fields[1] == 'w' else 'BLACK'
        self.set_fen_castling(fields[2])
        self.ep_square = Position.from_symbol(fields[3]) if fields[3] != '-' else None
        self.move50 = int(fields[4])
        self.fullmoves = int(fields[5])
        self.all_valid_moves = self.get_all_moves()
        self.print_board()
    
    def set_fen_castling(self, fen):
        white_king, black_king = self.kings['WHITE'], self.kings['BLACK']
        if 'Q' in fen:
            white_king.castling[0] = self.get_piece(Position(0, 7))
        if 'K' in fen:
            white_king.castling[1] = self.get_piece(Position(7, 7))
        if 'q' in fen:
            black_king.castling[0] = self.get_piece(Position(0, 0))
        if 'k' in fen:
            black_king.castling[1] = self.get_piece(Position(7, 0))

    def get_fen_notation(self):
        board_fen = ''
        for i in range(8):
            empty = 0
            for j in range(8):
                if self.board[i][j]:
                    board_fen += str(empty) if empty else ""
                    board_fen += self.board[i][j].symbol
                else:
                    empty += 1
            board_fen += "/"
        
        turn_fen = 'w' if self.turn == 'WHITE' else 'b'
        castling_fen = self.get_fen_castling()
        ep_fen = self.ep_square.symbol() if self.ep_square else '-'
        hm_clock = str(self.move50)
        fullmove_clock = str(self.fullmoves)
        return ' '.join((board_fen, turn_fen, castling_fen, ep_fen, hm_clock, fullmove_clock))

    def get_fen_castling(self):
        white_king, black_king = self.kings['WHITE'], self.kings['BLACK']
        castling_fen = ''
        if white_king.castling[1]:
            castling_fen += 'K'
        if white_king.castling[0]:
            castling_fen += 'Q'
        if black_king.castling[1]:
            castling_fen += 'k'
        if black_king.castling[0]:
            castling_fen += 'q'

        return castling_fen or '-'

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

    def get_all_moves(self):
        pieces = [p for p in self.pieces if p.color == self.turn]
        moves = {}
        for p in pieces:
           moves[p.pos] = self.get_piece_moves(p)
        return moves

    def get_piece_moves(self, piece):
        moves = piece.moves(self.board)
        # Check if castling is possible
        is_king = piece.piece == 'KING'
        if is_king and not self.in_check:
            moves += piece.check_castling(self.board)
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

    def _move_piece(self, piece: Piece, newpos: Position):
        self.board[piece.y][piece.x] = None
        piece.move(newpos)
        self.board[newpos.y][newpos.x] = piece

    def add_piece(self, piece: Piece):
        "Add the sprite to sprite groups"
        self.board[piece.pos.y][piece.pos.x] = piece
        self.pieces.add(piece)

    def remove_piece(self, piece: Piece):
        "Kills the piece and removes it from the board"
        self.pieces.remove(piece)
        self.board[piece.y][piece.x] = None

    def move_piece(self, piece: Piece, newpos: Position):
        "Move a chess piece in the board"
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
        self.history.append(Move(piece, newpos))
        self.ep_square = None
        king = self.get_current_king()
        oldpos = piece.pos
        castling = False
        promotion = None
        if piece.piece == 'KING':
            piece.castling = [None, None]
            if abs(newpos.x - oldpos.x) == 2:
                castling = True
                rook = self.board[piece.y][7 if (newpos.x - oldpos.x) > 0 else 0]
                diff = 1 if rook.x == 0 else -1
                self._move_piece(rook, newpos.move(diff, 0))
        elif piece.piece == 'ROOK' and piece in king.castling:
            side = king.castling.index(piece)
            king.castling[side] = None
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
        
        # Change coordinates of the moving piece
        self._move_piece(piece, newpos)
        if self.turn == 'BLACK':
            self.fullmoves += 1

        self.turn = 'BLACK' if self.turn == 'WHITE' else 'WHITE'
        self.in_check = self.is_check(self.board)
        self.all_valid_moves = self.get_all_moves()
        self.in_mate = not any(self.all_valid_moves.values())
        return self.get_move_notation(
            piece, oldpos, newpos, captured=capture_piece, 
            castling=castling, promotion=promotion
        )

    def is_check(self, board, pos=None, is_king=False):
        "Look for a check, return True if it is a checkmate"
        # Get all enemy pieces that do not occupy x,y (place we are going to put our piece)
        enemies = [e for e in self.pieces if e.color != self.turn and e.pos != pos]
        king = self.kings[self.turn]

        for e in enemies:
            # Loop through all enemy moves and see if the king's position lies in it
            moves = e.moves(board)
            if not is_king and king.pos in moves:
                return True
            if is_king and pos in moves:
                return True
        return False
    
    def print_board(self):
        string = '  +-----------------+\n'
        for i, row in enumerate(self.board):
            string += f'{str(8 - i)} | '
            for piece in row:
                string += f'{piece.symbol} ' if piece else '. '
            string += '|\n'
        string += '  +-----------------+\n'
        string += '    a b c d e f g h\n'
        print(string)


class UI:
    def __init__(self, board: Board):
        self.board = board
    
        self.spritesheet = Spritesheet('./images/spritesheet.png')
        self.spritesheet.load_spritemap('./images/spritemap.txt')
        self.font = pygame.font.SysFont(FONT, 15, True)

        self.board_surface = pygame.Surface(BOARD_RECT[2:])
        self.blocks = pygame.sprite.Group()

    def get_block(self, pos: Position) -> Block:
        return [b for b in self.blocks if b.pos == pos][0]

    def create(self, screen):
        for i in range(8):
            for j in range(8):
                self.blocks.add(Block(Position(i, j), (i+j)%2 == 0))

        for i in range(1, 9):
            text_surf = self.font.render(str(9-i), 0, WHITE)
            text_rect = text_surf.get_rect(centerx=BOARD_RECT[0]/2, centery=BLOCK_SIZE[1]*i)
            screen.blit(text_surf, text_rect)

            text_surf = self.font.render(FILES[i-1], 0, WHITE)
            text_rect = text_surf.get_rect(centerx=BLOCK_SIZE[0]*i, centery=SCREENY-BOARD_RECT[1]/2)
            screen.blit(text_surf, text_rect)

        board_width = BOARD_RECT[3] + BOARD_RECT[0] * 2
        self.side_screen = pygame.Surface((SCREENX - board_width, SCREENY))
        self.side_screen.fill('grey')
        screen.blit(self.side_screen, (board_width, 0))

    def select_piece(self):
        pos = pygame.mouse.get_pos()
        clicked_block = [b for b in self.blocks if b.rect.move(*BOARD_RECT[:2]).collidepoint(pos)]
        if clicked_block:
            return self.board.get_piece(clicked_block[0].pos)
    
    def draw_pieces(self, surface):
        for p in self.board.pieces:
            img = self.spritesheet.sprites[p.symbol]
            rect = img.get_rect(center=(BLOCK_SIZE[0] * (p.x + 0.5), BLOCK_SIZE[1] * (p.y + 0.5)))
            surface.blit(self.spritesheet.sprites[p.symbol], rect)

    def show_valid_moves(self, moves):
        "Show all possible move sets as circle dots"
        for mx, my in moves:
            cx = int(BLOCK_SIZE[0] * (mx + 0.5))
            cy = int(BLOCK_SIZE[1] * (my + 0.5))
            pygame.draw.circle(self.board_surface, GREY, (cx, cy), 10)

    def update(self):
        self.blocks.draw(self.board_surface)
        self.draw_pieces(self.board_surface)
    
    def draw(self, surface):
        surface.blit(self.board_surface, BOARD_RECT)



class Game:
    def __init__(self):
        # Initialize pygame stuff
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((SCREENX, SCREENY))
        self.running = True

        self.board = Board()
        self.selected = None
        self.piece_moves = []

        self.ui = UI(self.board)
        self.run()

    def select_piece(self):
        "Get the selected piece, unselect if already selected, get all valid moves"
        piece = self.ui.select_piece()
        if piece and piece.color == self.board.turn:
            # unselect previously selected piece
            if self.selected:
                self.ui.get_block(self.selected.pos).deselect()

            self.selected = piece
            self.piece_moves = self.board.all_valid_moves.get(self.selected.pos, [])
            self.ui.get_block(self.selected.pos).select()
    
    def move_selected(self, newpos: Position):
        # Deselect last move
        try:
            last_move = self.board.history[-1]
            self.ui.get_block(last_move.oldpos).deselect()
            self.ui.get_block(last_move.newpos).deselect()
        except IndexError:
            pass

        # Select current move
        self.ui.get_block(self.selected.pos).last_move()
        self.ui.get_block(newpos).last_move()

        # assume the king is not in check (validating moves was done above)
        king = self.board.get_current_king()
        self.ui.get_block(king.pos).check(False)

        move = self.board.move_piece(self.selected, newpos)
        print(f"{self.board.turn}'s move: {move}\n")
        self.board.print_board()

        king = self.board.get_current_king()
        self.ui.get_block(king.pos).check(self.board.in_check)

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

            if (x, y) in self.piece_moves:
                self.move_selected(Position(x, y))
                self.piece_moves = []
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
        self.ui.create(self.screen)
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)

            # Draw everything
            self.ui.update()
            self.ui.show_valid_moves(self.piece_moves)
            self.ui.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    pygame.init()
    game = Game()
