import pygame

from constants import FILES, Position
from chess import Board


SCREENX, SCREENY = 530, 530
FPS = 30
FONT = 'Arial'

# BOARD CONFIGURATIONS
BOARD_RECT = 25, 25, 480, 480
BLOCK_SIZE = 60, 60

# COLORS REQUIRED (RGB)
COLOR1 = WHITE = (255, 255, 255)
COLOR2 = GREEN = (118,150,86)
WHITE = (255, 255, 255)
GREY = (211, 211, 211)
SELECTED_COLOR = (233, 233, 150)
CHECK_COLOR = (240, 72, 72)
LAST_MOVE_COLOR = (200, 200, 150)


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


# Class for a block, usually handles all background changes when selected
class Block(pygame.sprite.Sprite):
    def __init__(self, pos: Position, color: bool):
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
        self.image.fill(SELECTED_COLOR)
        if self.is_check:
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



class UIManager:
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
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((SCREENX, SCREENY))
        pygame.display.set_caption('Pygame Chess')

        self.board = Board()
        self.selected = None
        self.running = True
        self.piece_moves = []

        self.ui = UIManager(self.board)
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