import random
import copy
from math import ceil

from console import CLS
from colors import colorStr
from data import world_gen, blocks


def move_map(map_, edges):

    # Create subset of slices from map_ between edges
    slices = {}
    for pos in range(*edges):
        slices[pos] = map_[str(pos)]
    return slices


def render_map(map_, objects, inv, blocks):
    """
        Prints out a frame of the game.

        Takes:
        - map_: a 2D list of blocks.
        - objects: a list of dictionaries:
            {'x': int, 'y': int, 'char': block}
        - inv: a 2D list of chars to make up the inventory on
            the right of the game.
        - blocks: the main dictionary describing the blocks in the game.
    """

    # Sorts the dict as a list by pos
    map_ = list(map_.items())
    map_.sort(key=lambda item: int(item[0]))

    # Seperates the pos and data
    map_ = tuple(zip(*map_))[1]

    # Orientates the data
    map_ = tuple(zip(*map_))

    # Output the map
    out = ''
    for y, row in enumerate(map_):
        for x, pixel in enumerate(row):

            char = pixel

            # Add any objects
            for object_ in objects:
                if object_['x'] == x and object_['y'] == y:
                    pixel = object_['char']

            try:
                out += blocks[pixel]['char'](pixel, char, blocks)
            except TypeError:
                out += blocks[pixel]['char']

        try:
            out += ' ' + inv[y]
        except IndexError:
            pass

        out += '\n'

    print(CLS + out, end='')


def slice_height(pos, meta):

    slice_height_ = world_gen['ground_height']

    # Check surrounding slices for a hill
    for x in range(pos - world_gen['max_hill'] * 2,
                   pos + world_gen['max_hill'] * 2):
        # Set seed for random numbers based on position
        random.seed(str(meta['seed']) + str(x) + 'hill')

        # Generate a hill with a 5% chance
        if random.random() <= 0.05:
            # Make top of hill flat
            # Set height to height of hill minus distance from hill
            hill_height = (world_gen['ground_height'] +
                random.randint(0, world_gen['max_hill']) - abs(pos-x)/2)
            hill_height -= 1 if pos == x else 0

            if hill_height > slice_height_:
                slice_height_ = hill_height

    return int(slice_height_)


def add_tree(slice_, pos, meta, blocks):
    # Maximum width of half a tree
    max_half_tree = int(len(max(world_gen['trees'], key=lambda tree: len(tree))) / 2)

    for x in range(pos - max_half_tree, pos + max_half_tree + 1):
        # Set seed for random numbers based on position
        random.seed(str(meta['seed']) + str(x) + 'tree')

        # Generate a tree with a 5% chance
        if random.random() <= 0.05:
            tree = random.choice(world_gen['trees'])

            # Get height above ground
            air_height = world_gen['height'] - slice_height(x, meta)

            # Centre tree slice (contains trunk)
            center_leaves = tree[int(len(tree)/2)]
            trunk_depth = next(i for i, leaf in enumerate(center_leaves[::-1])
                               if leaf)
            tree_height = random.randint(2, air_height
                          - len(center_leaves) + trunk_depth)

            # Find leaves of current tree
            for i, leaf_slice in enumerate(tree):
                leaf_pos = x + (i - int(len(tree) / 2))
                if leaf_pos == pos:
                    leaf_height = air_height - tree_height - (len(leaf_slice) - trunk_depth)

                    # Add leaves to slice
                    for j, leaf in enumerate(leaf_slice):
                        if leaf:
                            sy = leaf_height + j
                            slice_[sy] = spawn_hierarchy(blocks, ('@', slice_[sy]))

            if x == pos:
                # Add trunk to slice
                for i in range(air_height - tree_height,
                               air_height):
                    slice_[i] = spawn_hierarchy(blocks, ('|', slice_[i]))

    return slice_


def add_ores(slice_, pos, meta, blocks):
    for ore in world_gen['ores'].values():
        for x in range(pos - int(ore['vain_size'] / 2),
                       pos + ceil(ore['vain_size'] / 2)):
            # Set seed for random numbers based on position and ore
            random.seed(str(meta['seed']) + str(x) + ore['char'])

            # Gernerate a ore with a probability
            if random.random() <= ore['chance']:
                root_ore_height = random.randint(ore['lower'], ore['upper'])

                # Generates ore at random position around root ore
                random.seed(str(meta['seed']) + str(pos) + ore['char'])
                ore_height = (root_ore_height +
                              random.randint(-int(ore['vain_size'] / 2),
                                             ceil(ore['vain_size'] / 2)))

                # Won't allow ore above surface
                if ore['lower'] < ore_height < min(ore['upper'], slice_height(pos, meta)):
                    sy = world_gen['height'] - ore_height
                    slice_[sy] = spawn_hierarchy(blocks, (ore['char'], slice_[sy]))

    return slice_


def gen_slice(pos, meta, blocks):

    slice_height_ = slice_height(pos, meta)

    # Form slice of sky - ground - stone layers
    slice_ = (
        [' '] * (world_gen['height'] - slice_height_) +
        ['-'] +
        ['#'] * (slice_height_ - 2) + # 2 for grass and bedrock
        ['_']
    )

    slice_ = add_tree(slice_, pos, meta, blocks)
    slice_ = add_ores(slice_, pos, meta, blocks)

    return slice_


def detect_edges(map_, edges):

    slices = []
    for pos in range(*edges):
        try:
            # If it doesn't exist add the pos to the list
            map_[str(pos)]
        except KeyError:
            slices.append(pos)

    return slices


def spawn_hierarchy(blocks, tests):
    return max(tests, key=lambda block: blocks[block]['hierarchy'])


def is_solid(blocks, block):
    return blocks[block]['solid']


def ground_height(slice_, blocks):
    return next(i for i, block in enumerate(slice_) if blocks[block]['solid'])


def gen_blocks():

    # Convert the characters to their coloured form
    for key, block in blocks.items():
        try:
            # Make sure it is a string
            blocks[key]['char'] + ''
            string = True
        except TypeError:
            string = False

        if string:
            blocks[key]['char'] = colorStr(
                block['char'],
                block['colors']['fg'],
                block['colors']['bg'],
                block['colors']['style']
            )

    return blocks
