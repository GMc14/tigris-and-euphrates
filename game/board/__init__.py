from game.models import Board
from game.board.cell import Ground, River
from game.board.piece import SettlementCiv, FarmCiv, TempleCiv, MerchantCiv, SettlementRuler, FarmRuler, TempleRuler, MerchantRuler, GroundMonument, RiverMonument
from game.board.special import Unification, Catastrophe

class StandardBoard:
    rows = 11
    columns = 16
    cells = []

    G, T, R  = 'G','T', 'R'
    default_board = (G, G, G, G, R, R, R, R, R, G, T, G, R, G, G, G,
                     G, T, G, G, R, G, G, G, G, G, G, G, R, G, G, T,
                     G, G, G, R, R, T, G, G, G, G, G, G, R, R, G, G,
                     R, R, R, R, G, G, G, G, G, G, G, G, G, R, R, R,
                     G, G, G, G, G, G, G, G, G, G, G, G, G, T, R, R,
                     G, G, G, G, G, G, G, G, G, G, G, G, G, G, R, G,
                     R, R, R, R, G, G, G, G, T, G, G, G, R, R, R, G,
                     G, T, G, R, R, R, R, G, G, G, G, G, R, G, G, G,
                     G, G, G, G, G, G, R, R, R, R, R, R, R, G, T, G,
                     G, G, G, G, G, T, G, G, G, G, G, G, G, G, G, G,
                     G, G, G, G, G, G, G, G, G, G, T, G, G, G, G, G,)
    default_board_string = '|'.join(default_board)

    def __init__(self, game, turn_no=0):
        self.board = None
        if turn_no:
            self.board = Board.objects.filter(game=game, turn_no=turn_no).get()
            if not self.board:
                # raise
                pass
        else:
            self.board = Board(game=game,
                          turn_no=1,
                          rows=self.rows,
                          columns=self.columns,
                          board=self.default_board_string)
        self._parse_state(self.board.board)

    def _db_form(self):
        return '|'.join([ cell.db_form() for cell in self.cells])

    def _parse_state(self, board_str):
        def convert(cell_str):
            if cell_str.startswith('G'):
                if '!' in cell_str:
                    return Ground(special=Catastrophe())
                elif '?' in cell_str:
                    civ_type = cell_str[2]
                    if civ_type == 's':
                        return Ground(piece=SettlementCiv(), special=Unification())
                    elif civ_type == 't':
                        return Ground(piece=TempleCiv(), special=Unification())
                    elif civ_type == 'm':
                        return Ground(piece=MerchantCiv(), special=Unification())
                else:
                    return Ground()
            elif cell_str.startswith('R'):
                if '!' in cell_str:
                    return River(special=Catastrophe())
                elif '?' in cell_str:
                    return River(piece=FarmCiv(), special=Unification()) 
                else:
                    return River()
            elif cell_str.startswith('s'):
                return Ground(piece=SettlementCiv())
            elif cell_str.startswith('t'):
                return Ground(piece=TempleCiv())
            elif cell_str.startswith('f'):
                return River(piece=FarmCiv())
            elif cell_str.startswith('m'):
                return Ground(piece=MerchantCiv())
            elif cell_str.startswith('T'):
                return Ground(piece=TempleCiv(is_treasure=True))
            elif cell_str.startswith('r'):
                ruler_type = cell_str[2]
                ruler_player_no = cell_str[1]
                if ruler_type == 's':
                    return Ground(piece=SettlementRuler(ruler_player_no))
                elif ruler_type == 't':
                    return Ground(piece=TempleRuler(ruler_player_no))
                elif ruler_type == 'f':
                    return River(piece=FarmRuler(ruler_player_no))
                elif ruler_type == 'm':
                    return Ground(piece=MerchantRuler(ruler_player_no))
            elif cell_str.startswith('M'):
                pass

        self.cells = [ convert(x) for x in board_str.split('|')]

    def get_cell_no_for_civ(self, color):
        cell_nos = []
        for cell_no, cell in enumerate(self.cells):
            if cell.piece and (cell.piece.db_form() == color):
                cell_nos.append(cell_no)
        return cell_nos

    def save(self):
        self.board.board = self._db_form()
        self.board.save()

    def __iter__(self):
        return self.cells.__iter__()

    def __len__(self):
        return self.cells.__len__()

    def __getitem__(self, x):
        return self.cells.__getitem__(x)

    def __setitem__(self, x, y):
        return self.cells.__setitem__(x, y)

    def add_civ(self, cell_no, civ):
        self.cells[cell_no].piece = civ

def identify_regions(board):
    """Give a board
    Return an array where array[cell_no] is cell's region_no
    Where region_no = 0 means uncolonized
"""
    main_stack = [(cell, cell_no) for cell_no, cell in enumerate(board)]
    cell_no_visited = [ 0 for x in main_stack ]
    
    for cell, cell_no in main_stack:
        cell_no_visited[cell_no] = 0
    
    def _label_all_neighbors(cell_no, region_count):
        if cell_no_visited[cell_no]:
            return
        cell_no_visited[cell_no] = region_count
     
        unvisited = lambda index: board[index].has_piece() and not cell_no_visited[index]
        recursive_label = lambda index: _label_all_neighbors(index, region_count)
        do_on_adjacent_cells(cell_no, board, pred=unvisited, func=recursive_label)

    region_count = 1
    while main_stack:
        cell, cell_no = main_stack.pop()
        if not cell_no_visited[cell_no] and cell.has_piece():
            _label_all_neighbors(cell_no, region_count)
            region_count += 1

    return cell_no_visited

def identify_kingdoms(region_list, board):
    assert(len(region_list) == len(board))
    
    regions = set()
    for region_no, cell in zip(region_list, board):
        if cell.has_ruler():
            regions.add(region_no)

    return [ x in regions and x or -x for x in region_list ]


def get_legal_moves(board):
    return get_legal_civ_moves(board)

# def get_legal_ruler_moves(board):
#     legal_spots = { 'temple':[], 'settlement':[], 'farm':[], 'merchant':[] }
#     kingdoms = identify_kingdoms(identify_regions(board), board)
#     assert(len(kingdoms) == len(board))
    
#     legal_spots = legal_ruler_cells(board, kingdoms, 1)

#     placed_rulers_by_kingdom_id = {}
#     for kingdom_no in range(1, max(kingdoms) + 1):
#         for cell_no, kingdom_id in enumerate(kingdoms):
#             if kingdom_id == kingdom_no:
#                 if board[cell_no].piece and board[cell_no].piece.is_ruler:
#                     if kingdom_id in placed_rulers_by_kingdom_id:
#                         placed_rulers_by_kingdom_id[kingdom_id].append(board[cell_no].db_form()[-1])
#                     else:
#                         placed_rulers_by_kingdom_id[kingdom_id] = [ board[cell_no].db_form()[-1] ]

    
#     print 'legal spots:', legal_spots
#     print 'kingdoms:', kingdoms
#     print 'placed rulers:', placed_rulers_by_kingdom_id
#     return legal_spots

def get_legal_civ_moves(board):
    kingdoms = identify_kingdoms(identify_regions(board), board)
    print kingdoms
    assert(len(kingdoms) == len(board))
    
    legal_spots = legal_ruler_cells(board, kingdoms, 1)
    return legal_spots

def do_on_adjacent_cells(cell_no, board, pred, func):
    cur_row = cell_no / board.columns
    cur_col = cell_no % board.columns
    
    top_index = cell_no - board.columns
    bottom_index = cell_no + board.columns
    left_index = cell_no - 1
    right_index = cell_no + 1

    if cur_row - 1 >= 0 and pred(top_index):
        func(top_index)
    if cur_row + 1 < board.rows and pred(bottom_index):
        func(bottom_index)
    if cur_col - 1 >= 0 and pred(left_index):
        func(left_index)
    if cur_col + 1 < board.columns and pred(right_index):
        func(right_index)
    
def pieces_by_region(board, regions):
    """Takes a board, and a list where list[cell_no] = region_no.
Returns an list indexed by cell_no where 
list[region_no] = { 'rulers': [ ruler objects ],
                    'temples': [ temple indices ],
                    'settlements': [], etc
                  }
"""
    pieces_by_region = [ { 
            'rulers': [],
            'temple': [],
            'settlement': [],
            'farm': [],
            'merchant': []
          } for x in range(max(regions) + 1) ]

    for cur_region in range(1, max(regions) + 1):
        for cell_no, (cell, region_no) in enumerate(zip(board, regions)):
            if region_no is not cur_region or not cell.has_piece():
                continue
            name = cell.piece.name()

            if cell.piece.is_ruler:
                pieces_by_region[cur_region]['rulers'].append((name, cell.piece.player_no, cell_no))
            else:
                pieces_by_region[cur_region][name[4:]].append(cell_no)

    return pieces_by_region

def legal_ruler_cells(board, kingdoms):
    """Takes a board, and a list where list[cell_no] = kingdom_no.
Return a list of all legal moves for a ruler.
NOTE: Moves could still cause internal conflict
"""
    legal_spots = []

    adjacent_kingdoms_board = adjacent_kingdoms_by_cell_no(board, kingdoms)
    for cell_no, adjacent_kingdoms in enumerate(adjacent_kingdoms_board):
        if board[cell_no].has_piece() or board[cell_no].has_special() or not board[cell_no].is_ground:
            continue

        # use a list for ... mutability?
        # true/false doesn't work
        is_touching_temple = [] 

        pred = lambda index: board[index].has_piece() and board[index].db_form().lower() == 't'
        def set_touching_temple(index):
            is_touching_temple.append(1)
            
        do_on_adjacent_cells(cell_no, board, pred=pred, func=set_touching_temple)

        if len(adjacent_kingdoms) <= 1 and is_touching_temple:
            legal_spots.append(cell_no)

    return legal_spots

def adjacent_kingdoms_by_cell_no(board, kingdoms):
    """Take a board and a list where list[cell_no] = kingdom_no.
Return a list where list[cell_no] = [ adjacent kingdom nos ]
NOTE: list[cell_no] = [] cell_no is already part of a region!
"""
    adjacent_kingdoms_list = [ [] for x in board ]

    for cell_no, (cell, kingdom_id) in enumerate(zip(board, kingdoms)):
        if kingdom_id == 0:
            adjacent_kindoms = set()

            pred = lambda index: kingdoms[index] > 0
            add_adjacent_kingdom = lambda index: adjacent_kindoms.add(kingdoms[index])
            do_on_adjacent_cells(cell_no, board, pred=pred, func=add_adjacent_kingdom)

            adjacent_kingdoms_list[cell_no] = adjacent_kindoms
    return [ list(x) for x in adjacent_kingdoms_list ]

def split_legal_moves_by_type(board):
    legal_moves = get_legal_civ_moves(board)
    legal_ground = []
    legal_river = []

    for cell_no in legal_moves:
        if board[cell_no].is_ground:
            legal_ground.append(cell_no)
        else:
            legal_river.append(cell_no)

    return { 'ground': legal_ground,
             'river': legal_river }
