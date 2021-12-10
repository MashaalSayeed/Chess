import collections

# Game Configurations
STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
FILES = 'abcdefgh'


class Position(collections.namedtuple('Position', ['x', 'y'])):
    def move(self, dx, dy):
        return Position(self.x + dx, self.y + dy)
    
    def symbol(self):
        return FILES[self.x] + str(8 - self.y)
    
    @classmethod
    def from_symbol(cls, symbol):
        x = 'abcdefgh'.index(symbol[0])
        y = int(symbol[1]) - 1
        return cls(x, y)
