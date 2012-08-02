import collections, functools, itertools, random

LINES = [ (0,1,2), (3,4,5), (6,7,8),
          (0,3,6), (1,4,7), (2,5,8),
          (0,4,8), (2,4,6) ]

TOKENS = { 0: 'X', 1: 'O' }

def get_token(turn):
    return TOKENS[turn % 2]

# Utility functions for manipulating tuples
def add_element(tpl, x):
    return tpl + (x,)

def remove_element(tpl, x):
    return tuple(x1 for x1 in tpl if x1 != x)

def set_element(tpl, ix, x):
    return tpl[:ix] + (x,) + tpl[ix + 1:]

# Board logic
def make_empty_board():
    return tuple(() for _ in range(9))

def get_last_turn(board):
    turns = list(itertools.chain(*(board[cell] for cell in get_uncollapsed_cells(board)))) 
    if turns:
        return max(turns)
    else:
        return -1

def get_next_turn(board):
    return 1 + get_last_turn(board)

def get_uncollapsed_cells(board):
    return [cell for cell, contents in enumerate(board) if cell_has_not_collapsed(board, cell)]

def cell_has_collapsed(board, cell):
    return isinstance(board[cell], int)

def cell_has_not_collapsed(board, cell):
    return not(cell_has_collapsed(board, cell))

def find_entangled_cell(board, turn, cell):
    for c, turns in enumerate(board):
        if c != cell and cell_has_not_collapsed(board, c) and turn in turns:
            return c

def find_related(board, turn, cell):
    if cell_has_collapsed(board, cell):
        return []
    else:
        return [(turn1, find_entangled_cell(board, turn1, cell)) for turn1 in board[cell] if turn1 != turn]

def check_for_cycles(board, turn, cell):
    paths = [[(turn, cell)]]

    for path in paths:
        for turn1, cell1 in find_related(board, *path[-1]):
            if cell1 == cell and turn1 == turn:
                return True
            paths.append(path + [(turn1, cell1)])

    return False

def move(board, turn, cell1, cell2):
    board = set_element(board, cell1, add_element(board[cell1], turn))
    board = set_element(board, cell2, add_element(board[cell2], turn))
    return board

def valid_moves(board):
    return get_uncollapsed_cells(board)

def is_valid_move(board, cell1, cell2):
    return cell1 != cell2 and cell1 in valid_moves(board) and cell2 in valid_moves(board)

def collapse(board, turn, cell):
    related = find_related(board, turn, cell)
    cell1 = find_entangled_cell(board, turn, cell)
    if cell1 is not None and cell_has_not_collapsed(board, cell1):
        board = set_element(board, cell1, remove_element(board[cell1], turn))
    board = set_element(board, cell, turn)
    for turn1, cell1 in related:
        board = collapse(board, turn1, cell1)
    return board

def valid_resolutions(board):
    return [cell for cell, contents in enumerate(board) if cell_has_not_collapsed(board, cell) and get_last_turn(board) in contents]

def is_valid_resolution(board, cell):
    return cell in valid_resolutions(board)

def get_points(board):
    winners = []
    for line in LINES:
        turns = [board[cell] for cell in line]
        if all(isinstance(turn, int) for turn in turns):
            if (turns[0] % 2 + 1) * (turns[1] % 2 + 1) * (turns[2] % 2 + 1) in (1, 8):
                winners.append(max(turns))

    winners.sort()
    points = [winner == winners[0] for winner in winners]
    points = [point * 0.5 + 0.5 for point in points]
    return tuple([sum([point for point, winner in zip(points, winners) if winner % 2 == player_ix]) for player_ix in (0, 1)])

# A wrapper around the board data structure
# (...guns don't kill people...)
class Board(object):
    def __init__(self, board=None):
        if board is None:
            self.board = make_empty_board()
        else:
            self.board = board
        self.turn = -1

    def move(self, cell1, cell2):
        self.turn += 1
        self.board = move(self.board, self.turn, cell1, cell2)

    def collapse(self, cell):
        self.board = collapse(self.board, self.turn, cell)

    def set_final_cell(self):
        self.board = set_element(self.board, self.valid_moves()[0], self.get_next_turn())

    def __getattr__(self, attr):
        return functools.partial(globals()[attr], self.board)

    def __getitem__(self, ix):
        return self.board[ix]

# Base class for players
class Player(object):
    def __init__(self, ix):
        self.ix = ix
        self.token = TOKENS[ix]

# Class for human player
class Human(Player):
    def get_move(self, board):
        while True:
            moves = raw_input("Player %s -- choose your move: " % self.token)
            try:
                cell1, cell2 = [int(cell) for cell in moves.split(' ', 1)]
            except ValueError:
                print "Could not parse", moves
                continue

            return cell1, cell2

    def get_resolution(self, board):
        cell1, cell2 = valid_resolutions(board)
        while True:
            cell =raw_input("Player %s -- choose to resolve on %d or %d: " % (self.token, cell1, cell2))
            try:
                cell = int(cell)
            except ValueError:
                print "Could not parse", cell
                continue
            
            return cell

# Base class for AI players.  AI players should override score_move() and score_resolution()
class AI(Player):
    def score_move(self, board, turn, cell1, cell2):
        raise NotImplementedError

    def score_resolution(self, board, turn, cell):
        raise NotImplementedError

    def score(self, points):
        return points[self.ix] - points[1 - self.ix]

    def get_move(self, board):
        scores = self.score_moves(board)
        return self.make_choice(scores)

    def score_moves(self, board):
        turn = get_next_turn(board)
        moves = valid_moves(board)
        return {(cell1, cell2): self.score_move(board, turn, cell1, cell2) for cell1, cell2 in itertools.combinations(moves, 2)}

    def get_resolution(self, board):
        turn = get_last_turn(board)
        cell1, cell2 = valid_resolutions(board)
        scores = self.score_resolutions(board, turn, cell1, cell2)
        return self.make_choice(scores)

    def score_resolutions(self, board, turn, cell1, cell2):
        return {cell: self.score_resolution(board, turn, cell) for cell in (cell1, cell2)}

    def make_choice(self, scores):
        top_score = max(scores.values())
        return random.choice([move for move, score in scores.items() if score == top_score])

# This AI picks moves at random
class RandomAI(AI):
    def score_move(self, board, turn, cell1, cell2):
        return 0

    def score_resolution(self, board, turn, cell):
        return 0

# This AI picks a move if it may lead directly to victory, otherwise it picks at random
class SimpleAI(AI):
    def score_move(self, board, turn, cell1, cell2):
        board1 = move(board, turn, cell1, cell2)
        if check_for_cycles(board1, turn, cell1):
            cell = self.get_resolution(board1)
            return self.score(get_points(collapse(board1, turn, cell)))
        else:
            return 0

    def score_resolution(self, board, turn, cell):
        return self.score(get_points(collapse(board, turn, cell)))

# This AI's behaviour is left as an exercise to the reader
class SmarterAI(AI):
    def score_move(self, board, turn, cell1, cell2):
        board1 = move(board, turn, cell1, cell2)

        if check_for_cycles(board1, turn, cell1):
            boards = [collapse(board1, turn, cell1), collapse(board1, turn, cell2)]
            score = min(self.score(get_points(board2)) for board2 in boards)
            if score > 0:
                return score
        else:
            boards = [board1]

        for board2 in boards:
            for cell3, cell4 in itertools.combinations(valid_moves(board2), 2):
                board3 = move(board2, turn + 1, cell3, cell4)
                if check_for_cycles(board3, turn + 1, cell3):
                    boards1 = [collapse(board3, turn + 1, cell3), collapse(board3, turn + 1, cell4)]
                    score = max(self.score(get_points(board2)) for board2 in boards1)
                    if score < 0:
                        return score

        return 0

    def score_resolution(self, board, turn, cell):
        return self.score(get_points(collapse(board, turn, cell)))

# Play single game between two players.
class Game(object):
    def __init__(self, player_classes, verbose=True):
        self.players = [cls(ix) for ix, cls in enumerate(player_classes)]
        self.verbose = verbose
        self.board = Board()

    def display(self):
        if self.verbose:
            for a in range(3):
                for b in range(3):
                    for c in range(3):
                        for d in range(3):
                            cell = 3 * a + c
                            if self.board.cell_has_collapsed(cell):
                                turn = self.board[cell]
                                if b == d == 1:
                                    print "%s%d" % (get_token(turn), turn),
                                else:
                                    print "  ",
                            else:
                                turn = 3 * b + d
                                if turn in self.board[cell]:
                                    print "%s%d" % (get_token(turn), turn),
                                else:
                                    print ". ",
                        if c < 2:
                            print "|",
                    print
                if a < 2:
                    print "---------+----------+---------"
            print
            print

    def notify(self, message):
        if self.verbose:
            print message

    def play(self):
        self.display()

        for turn in range(9):
            player = self.players[turn % 2]
            other_player = self.players[(turn + 1) % 2]

            if turn == 8 and len(self.board.valid_moves()) == 1:
                self.board.set_final_cell()
                self.notify("Player %s is forced to play in cell %s" % (player.token, cell))
                self.display()

            else:
                while True:
                    cell1, cell2 = player.get_move(self.board.board)
                    if self.board.is_valid_move(cell1, cell2):
                        break

                self.notify("Player %s moves: %s %s" % (player.token, cell1, cell2))
                self.board.move(cell1, cell2)
                self.display()

                if self.board.check_for_cycles(turn, cell1):
                    while True:
                        cell = other_player.get_resolution(self.board.board)
                        if self.board.is_valid_resolution(cell):
                            break

                    self.notify("Player %s collapses on: %s" % (other_player.token, cell))
                    self.board.collapse(cell)
                    self.display()

            points = self.board.get_points()
            if points != (0, 0):
                for player_ix in 0, 1:
                    self.notify("%s scores %s" % (TOKENS[player_ix], points[player_ix]))
                return points

        self.notify("game is a tie")
        return (0, 0)

# Play repeated games between two players
class Tournament(object):
    def __init__(self, player_classes, rounds=100):
        self.player_classes = player_classes
        self.rounds = rounds
        
    def play(self):
        scores = collections.Counter([Game(self.player_classes, verbose=False).play() for _ in range(self.rounds)])
        print scores
        return scores

if __name__ == '__main__':
    import sys

    if len(sys.argv) == 1:
        tournament = False
    elif sys.argv[1] == '-t':
        tournament = True
    else:
        print "Usage:"
        print "  python guantumooxx.py [-t]"
        sys.exit(1)

    # User selects player classes for game or tournament
    all_player_classes = [Human, RandomAI, SimpleAI, SmarterAI]
    player_classes = []
    for ix in 0, 1:
        print("Select player %s" % TOKENS[ix])
        for i, cls in enumerate(all_player_classes):
            print "%2d\t%s" % (i, all_player_classes[i].__name__)
    
        while True:
            try:
                n = int(raw_input("Enter choice: "))
            except ValueError:
                continue
            if n in range(len(all_player_classes)):
                player_classes.append(all_player_classes[n])
                break

    if tournament:
        # Play tournament
        tournament = Tournament(player_classes)
        tournament.play()
    else:
        # Play single game
        game = Game(player_classes)
        game.play()
