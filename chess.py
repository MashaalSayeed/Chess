from constants import Position, STARTING_FEN, FILES


BoardList = list[list['Piece']]

class Piece:
    "Base class for all pieces"
    piece = ''
    def __init__(self, pos: Position, color: str):
        self.pos = pos
        self.x, self.y = pos.x, pos.y

        # color of the piece, will also determine the team it is in
        self.color = color
        self.symbol = self.piece[0] if self.piece != 'KNIGHT' else 'N'
        if self.color == 'BLACK':
            self.symbol = self.symbol.lower()

    def move(self, pos: Position):
        # update the coordinates of piece in square matrix
        self.pos = pos
        self.x, self.y = pos.x, pos.y

    def _check_valid(self, board: BoardList, x, y):
        # Checks whether the move position is valid (not out of board and not occupied by same team pieces)
        return 0 <= x < 8 and 0 <= y < 8 and (not board[y][x] or board[y][x].color != self.color)

    def _generate_moves(self, board: BoardList, lst: list[tuple[int, int]]):
        # Get all valid moves based on incremented directions (diagonal, vertical, horizontal)
        valid = []
        for ix, iy in lst:
            curx, cury = self.pos
            while True:
                curx, cury = curx + ix, cury + iy
                if self._check_valid(board, curx, cury):
                    valid.append(Position(curx, cury))
                    if board[cury][curx]:
                        break
                else:
                    break
        return valid

    def diagonal_moves(self, board):
        # Get all possible diagonal moves
        lst = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        return self._generate_moves(board, lst)
        
    def linear_moves(self, board):
        # Get all horizontal and vertical moves
        lst = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        return self._generate_moves(board, lst)

    def __repr__(self):
        return f'[{self.color} {self.piece} {self.x},{self.y}]'


class Move:
    def __init__(self, piece: Piece, newpos: Position):
        self.oldpos = piece.pos
        self.newpos = newpos
        self.piece = piece

    def to_uci(self):
        return self.oldpos.symbol() + self.newpos.symbol()


class Pawn(Piece):
    piece = 'PAWN'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.increment = -1 if self.color == 'WHITE' else 1
    
    def check_en_passant(self, ep_square):
        return abs(ep_square[1] - self.x) == 1 and self.y + self.increment == ep_square.y

    def moves(self, board):
        nposy = self.y + self.increment
        valid = []
        
        if 0 <= nposy <= 7:
            # Diagonal attack
            if 0 <= self.x+1 <= 7 and board[nposy][self.x+1] and board[nposy][self.x+1].color != self.color:
                valid.append(Position(self.x+1, nposy))
                
            if 0 <= self.x-1 <= 7 and board[nposy][self.x-1] and board[nposy][self.x-1].color != self.color:
                valid.append(Position(self.x-1, nposy))

        # Forward Movement
        if 0 <= nposy <= 7 and board[nposy][self.x] == None:
            valid.append(Position(self.x, nposy))
                
            # Double Forward
            if (self.color == 'WHITE' and self.y == 6) or (self.color == 'BLACK' and self.y == 1):
                nposy += self.increment
                if board[nposy][self.x] == None:
                    valid.append(Position(self.x, nposy))
        return valid


class Rook(Piece):
    piece = 'ROOK'
    def moves(self, board):
        return self.linear_moves(board)


class Knight(Piece):
    piece = 'KNIGHT'
    def moves(self, board):
        # Generates max 8 moves based on increment values
        lst = [(1, 2), (2, 1), (-1, 2), (2, -1), (-1, -2), (-2, -1), (-2, 1), (1, -2)]
        valid = []
        for ix, iy in lst:
            nx, ny = self.x + ix, self.y + iy
            if self._check_valid(board, nx, ny):
                valid.append(Position(nx, ny))
        return valid                    


class Bishop(Piece):
    piece = 'BISHOP'
    def moves(self, board):
        return self.diagonal_moves(board)


class King(Piece):
    piece = 'KING'
    def __init__(self, pos, color):
        super().__init__(pos, color)
        self.castling = [None, None] # [Queen side, King side]

    def check_castling(self, board):
        valid_moves = []
        if self.castling[0] and not any((board[self.y][self.x-1], board[self.y][self.x-2], board[self.y][self.x-3])):
            valid_moves.append(Position(self.x-2, self.y))

        if self.castling[1] and not any((board[self.y][self.x+1], board[self.y][self.x+2])):
            valid_moves.append(Position(self.x+2, self.y))
        return valid_moves

    def moves(self, board):
        # Generates max 8 moves based on increment values (Similar to horse)
        lst = [(1,1), (0,1), (1,0), (-1,-1), (0,-1), (-1,0), (-1,1), (1,-1)]
        valid = []
        for ix, iy in lst:
            nx, ny = self.x + ix, self.y + iy

            if self._check_valid(board, nx, ny):
                valid.append(Position(nx, ny))
        return valid


class Queen(Piece):
    piece = 'QUEEN'
    def moves(self, board):
        return self.diagonal_moves(board) + self.linear_moves(board)


PIECE_SYMBOLS = {
    'P': Pawn,
    'R': Rook,
    'N': Knight,
    'B': Bishop,
    'Q': Queen,
    'K': King
}


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
        self.pieces = set()
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
