from colours import *
from render import blocks
from terrain import is_solid, world_gen


cursor_x = {0:  0, 1:  1, 2: 1, 3: 0, 4: -1, 5: -1}
cursor_y = {0: -2, 1: -1, 2: 0, 3: 1, 4:  0, 5: -1}

INV_TITLE = 'Inventory'
CRAFT_TITLE = 'Crafting'

HAND_STRENGTH = 20


def get_pos_delta(char, map_, x, y, jump, flight):

    left_slice = map_[x - 1]
    player_slice = map_[x]
    right_slice = map_[x + 1]

    feet_y = y
    head_y = y - 1
    below_y = y + 1
    above_y = y - 2

    dy = 0
    dx = 0

    # Calculate change in x pos for left and right movement
    for test_char, dir_, next_slice in (('a', -1, left_slice), ('d', 1, right_slice)):
        if ( char in test_char
             and not is_solid( next_slice[head_y] )):

            if is_solid( next_slice[feet_y] ):
                if ( not is_solid( next_slice[above_y] )
                     and not is_solid( player_slice[above_y] )):

                    dy = -1
                    dx = dir_
            else:
                dx = dir_

    # Jumps if up pressed, block below, no block above
    if ( char in 'w' and y > 1
         and (not is_solid( player_slice[above_y] )
              and ( is_solid( player_slice[below_y] )
                    or player_slice[feet_y] == '=' )
              or flight)):

        dy = -1
        jump = 5

    if (flight and char in 's' and head_y < world_gen['height']
         and (not is_solid(player_slice[below_y]))):
        dy = 1

    return dx, dy, jump


def can_place(map_, block_x, block_y, inv_block):

    placed_on = blocks[inv_block].get('placed_on')
    placed_on_solid = blocks[inv_block].get('placed_on_solid')
    placed_on_wall = blocks[inv_block].get('placed_on_wall')

    if all(x is None for x in (placed_on, placed_on_solid, placed_on_wall)):
        can_place = True
    else:
        block_below = map_[block_x][block_y+1]
        wall_blocks = (map_[block_x-1][block_y], map_[block_x+1][block_y])

        can_place = (placed_on is not None and block_below in placed_on or
                     placed_on_solid and blocks[block_below]['solid'] or
                     placed_on_wall and any(blocks[b]['solid'] for b in wall_blocks))

    return can_place


def cursor_func(inp, map_, x, y, cursor, inv_sel, inv):
    block_x = x + cursor_x[cursor]
    block_y = y + cursor_y[cursor]
    block = map_[block_x][block_y]
    inv_block = inv[inv_sel]['block'] if len(inv) else None
    dinv = False
    events = []

    slices = {}

    if inp in 'k' and block_y >= 0 and block_y < world_gen['height']:

        # If pressing k and block is air and can place
        if (block == ' ' and len(inv) and
                blocks[inv_block]['breakable'] and
                can_place(map_, block_x, block_y, inv_block)):

            # Place block in world from selected inv slot
            slices[block_x] = {}
            slices[block_x][block_y] = inv_block
            inv, inv_sel = rem_inv(inv, inv_sel)
            dinv = True

            if inv_block == '?':
                events.append({
                    'pos': (block_x, block_y),
                    'time_remaining': 10
                })

        # If pressing k and block is not air and breakable
        elif can_inv_tool_break(block, inv, inv_sel):

            # Destroy block
            block = map_[block_x][block_y]
            slices[block_x] = {}
            slices[block_x][block_y] = ' '
            inv = add_inv(inv, block)
            dinv = True

    return slices, inv, inv_sel, events, dinv


def move_cursor(inp):
    return {'j': -1, 'l': 1}.get(inp, 0)


def move_sel(inp):
    return {'u': -1, 'o': 1}.get(inp, 0)


def can_strength_break(block_target, strength):
    return blocks[block_target]['breakable'] and strength >= blocks[block_target]['hierarchy']


def can_inv_tool_break(block_target, inv, inv_sel):
    try:
        tool = inv[inv_sel]['block']
    except IndexError:
        strength = HAND_STRENGTH
    else:
        strength = blocks[tool].get('strength', HAND_STRENGTH)

    return can_strength_break(block_target, strength)


def cursor_colour(x, y, cursor, map_, inv, inv_sel):
    x, y = x + cursor_x[cursor], y + cursor_y[cursor]

    if (x in map_ and y >= 0 and y < len(map_[x]) and
            can_inv_tool_break(map_[x][y], inv, inv_sel)):
        colour = WHITE
    else:
        colour = RED

    return colour


def assemble_players(players, x, y, offset, edges):
    objects = []

    for player in players.values():
        player_x = player['player_x']
        player_y = player['player_y']
        x_offset = player_x - x + offset

        if player_x in range(*edges):
            objects.append({
                'x': x_offset,
                'y': player_y - 1,
                'char': '*'
            })
            objects.append({
                'x': x_offset,
                'y': player_y,
                'char': '^'
            })

    return objects


def assemble_cursor(x, y, cursor, colour):
    return {
        'x': x + cursor_x[cursor],
        'y': y + cursor_y[cursor],
        'char': 'X',
        'colour': colour
    }


def get_crafting(inv, crafting_list, crafting_sel, reset=False):
    """ Makes a list of blocks you can craft """

    inv = dict(map(lambda a: (a['block'], a['num']), inv))

    def old_n(recipe):
        if not reset:
            # Gets the old num, if exists
            for old in crafting_list:
                if old['block'] == recipe['block']:
                    recipe['num'] = old['num']
                    break
        return recipe

    crafting = []
    for char, block in blocks.items():
        if 'recipe' in block:
            can_craft = True
            for ingredient, n in block['recipe'].items():
                if not (ingredient in inv and n <= inv[ingredient]):
                    can_craft = False
            if can_craft:
                crafting.append(old_n({
                    'block': char,
                    'num': block.get('crafts', 1)
                }))

    return crafting, max(min(crafting_sel, len(crafting) - 1), 0)


def craft_num(inp, inv, crafting_list, crafting_sel):
    dcraft = False

    if inp in '-=':
        dn = '-='.find(inp)*2 - 1

        inv = dict(map(lambda a: (a['block'], a['num']), inv))

        craft = crafting_list[crafting_sel]
        block = blocks[craft['block']]

        n_crafts = max(1, dn + int(craft['num'] / block.get('crafts', 1)))
        can_craft = all(ingredient in inv and (n * n_crafts) <= inv[ingredient]
                        for ingredient, n in block['recipe'].items())

        if can_craft:
            crafting_list[crafting_sel]['num'] = n_crafts * block.get('crafts', 1)
            dcraft = True

    return crafting_list, dcraft


def crafting(inp, inv, inv_sel, crafting_list, crafting_sel):
    """ Crafts the selected item in crafting_list """

    dcraft = False

    if inp in 'i' and len(crafting_list):
        dcraft = True
        craft = crafting_list[crafting_sel]

        block = blocks[craft['block']]
        for ingredient, n in block['recipe'].items():
            for i, b in enumerate(inv):
                if b['block'] == ingredient:
                    inv, _ = rem_inv(inv, i, n * int(craft['num'] / block.get('crafts', 1)))

                    # Decrements inv_sel if you're at the end of the list
                    #   or an item is removed below you in the list.
                    inv_sel -= inv_sel > i or len(inv) == inv_sel

        add_inv(inv, craft['block'], craft['num'])

    return inv, max(inv_sel, 0), crafting_list, dcraft


def label(list, sel):
    try:
        return blocks[list[sel]['block']]['name']
    except IndexError:
        return ''


def add_inv(inv, block, n=1):
    placed = False

    for i, slot in enumerate(inv):
        if slot['block'] == block:
            inv[i]['num'] += n
            placed = True
            break

    if placed is False:
        inv.append({'block': block, 'num': n})

    return inv


def rem_inv(inv, inv_sel, n=1):
    if inv[inv_sel]['num'] == n:
        inv.remove(inv[inv_sel])

        if inv_sel == len(inv):
            inv_sel -= 1
    else:
        inv[inv_sel]['num'] -= n

    return inv, inv_sel
