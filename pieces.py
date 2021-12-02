import string
import collections
import pygame


# COLORS REQUIRED (RGB)
COLOR1 = WHITE = (255, 255, 255)
COLOR2 = GREEN = (118,150,86)
SELECTED_COLOR = (233, 233, 150)
CHECK_COLOR = (240, 72, 72)
LAST_MOVE_COLOR = (200, 200, 150)

GREY = (211, 211, 211)

# BOARD CONFIGURATIONS
BLOCK_SIZE = 60, 60
PIECE_SIZE = 45, 45


class Position(collections.namedtuple('Position', ['x', 'y'])):
    def move(self, dx, dy):
        return Position(self.x + dx, self.y + dy)
    
    def symbol(self):
        return string.ascii_lowercase[self.x] + str(8 - self.y)
    
    @classmethod
    def from_symbol(cls, symbol):
        x = 'abcdefgh'.index(symbol[0])
        y = int(symbol[1]) - 1
        return cls(x, y)


# Class for a block, usually handles all background changes when selected
class Block(pygame.sprite.Sprite):
    def __init__(self, pos: Position, color):
        super().__init__()
        self.pos = pos

        # Create a rectangle of required size and color
        self.image = pygame.Surface(BLOCK_SIZE)
        self.color = COLOR2 if color else COLOR1
        self.image.fill(self.color)

        self.rect = self.image.get_rect(x=BLOCK_SIZE[0]*pos.x, y=BLOCK_SIZE[1]*pos.y)

        self.selected = self.is_check = False

    def select(self):
        # Change color to yellow when selected and change back to original when unselected
        if not self.selected:
            self.image.fill(SELECTED_COLOR)
        elif self.is_check:
            self.image.fill(CHECK_COLOR)
        self.selected = True
    
    def deselect(self):
        self.selected = False
        if self.is_check:
            self.image.fill(CHECK_COLOR)
        else:
            self.image.fill(self.color)
    
    def last_move(self):
        self.image.fill(LAST_MOVE_COLOR)

    def check(self, isCheck):
        self.image.fill(CHECK_COLOR if isCheck else self.color)
        self.is_check = isCheck

     
class Piece:
    "Base class for all pieces"
    def __init__(self, pos: Position, color, piece):
        super().__init__()
        self.pos = pos
        self.x, self.y = pos.x, pos.y

        # color of the piece, will also determine the team it is in
        self.color = color
        self.piece = piece
        self.symbol = piece[0] if piece != 'KNIGHT' else 'N'
        if self.color == 'BLACK':
            self.symbol = self.symbol.lower()

    def move(self, pos):
        # update the coordinates of piece in square matrix
        self.pos = pos
        self.x, self.y = pos.x, pos.y

    def check_valid(self, board, x, y):
        # Checks whether the move position is valid (not out of board and not occupied by same team pieces)
        return 0 <= x < 8 and 0 <= y < 8 and (not board[y][x] or board[y][x].color != self.color)
            
    def generate_moves(self, board, lst):
        # Get all valid moves based on incremented directions (diagonal, vertical, horizontal)
        valid = []
        for ix, iy in lst:
            curx, cury = self.pos
            while True:
                curx, cury = curx + ix, cury + iy
                if self.check_valid(board, curx, cury):
                    valid.append(Position(curx, cury))
                    if board[cury][curx]:
                        break
                else:
                    break
        return valid

    def diagonal_moves(self, board):
        # Get all possible diagonal moves
        lst = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        return self.generate_moves(board, lst)
        
    def linear_moves(self, board):
        # Get all horizontal and vertical moves
        lst = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        return self.generate_moves(board, lst)

    def __repr__(self):
        return f'[{self.color} {self.piece} {self.x},{self.y}]'


class Pawn(Piece):
    def __init__(self, pos, color):
        super().__init__(pos, color, 'PAWN')
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
    def __init__(self, pos, color):
        super().__init__(pos, color, 'ROOK')

    def moves(self, board):
        return self.linear_moves(board)


class Knight(Piece):
    def __init__(self, pos, color):
        super().__init__(pos, color, 'KNIGHT')

    def moves(self, board):
        # Generates max 8 moves based on increment values
        lst = [(1, 2), (2, 1), (-1, 2), (2, -1), (-1, -2), (-2, -1), (-2, 1), (1, -2)]
        valid = []
        for ix, iy in lst:
            nx, ny = self.x + ix, self.y + iy
            if self.check_valid(board, nx, ny):
                valid.append(Position(nx, ny))
        return valid                    


class Bishop(Piece):
    def __init__(self, pos, color):
        super().__init__(pos, color, 'BISHOP')

    def moves(self, board):
        return self.diagonal_moves(board)


class King(Piece):
    def __init__(self, pos, color):
        super().__init__(pos, color, 'KING')
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

            if self.check_valid(board, nx, ny):
                valid.append(Position(nx, ny))
        return valid


class Queen(Piece):
    def __init__(self, pos, color):
        super().__init__(pos, color, 'QUEEN')

    def moves(self, board):
        return self.diagonal_moves(board) + self.linear_moves(board)

