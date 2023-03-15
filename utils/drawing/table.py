# Yoinked from https://github.com/mdiller/MangoByte (MIT Licence)

from PIL import Image, ImageDraw
from utils.drawing.imagetools import *

# cache of table_font based on size
table_font_cache = {}

# if specified, padding should be a 4 element list, or an int
# 4 element list is left, top, right, bottom
def get_padding(kwargs, default=0):
    if isinstance(kwargs, dict):
        padding = kwargs.get("padding", default)
    else:
        padding = kwargs
    if isinstance(padding, int):
        padding = [padding, padding, padding, padding]
    if isinstance(kwargs, int):
        return padding
    if 'padding_top' in kwargs:
        padding[0] = kwargs['padding_top']
    if 'padding_right' in kwargs:
        padding[1] = kwargs['padding_right']
    if 'padding_bottom' in kwargs:
        padding[2] = kwargs['padding_bottom']
    if 'padding_left' in kwargs:
        padding[3] = kwargs['padding_left']
    return padding


def tuplediff(tuple1, tuple2):
    return tuple(map(lambda i, j: i - j, tuple1, tuple2))


class Cell:
    def __init__(self, **kwargs):
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.background = kwargs.get('background')
        self.border_size = kwargs.get('border_size', 0)
        self.border_color = kwargs.get('border_color', "#ffffff")

    def base_render(self, draw, image, x, y, width, height):
        # background
        if self.background:
            draw.rectangle([x, y, x + width - 1, y + height - 1],
                           fill=self.background)

        # draw cell
        image, draw = self.render(draw, image, x, y, width, height)

        # border
        if self.border_size:
            # for now, this only draws the right and bottom lines
            z = self.border_size
            draw.line((x + width - z, y, x + width - z, y +
                      height - z), width=z, fill=self.border_color)
            draw.line((x, y + height - z, x + width - z, y +
                      height - z), width=z, fill=self.border_color)

        return image, draw

    def render(self, draw, image, x, y, width, height):
        return image, draw

# a wrapper class to make the color specifying simpler
class ColorCell(Cell):
    def __init__(self, **kwargs):
        self.color = kwargs.get('color', '#ffffff')
        if "background" not in kwargs:
            kwargs["background"] = self.color
        Cell.__init__(self, **kwargs)


class ImageCell(Cell):
    def __init__(self, **kwargs):
        Cell.__init__(self, **kwargs)
        self.image = kwargs.get('image', kwargs.get('img'))
        if not self.image:
            return  # no image, so this is basically an empty cell
        if isinstance(self.image, str):  # prolly a path to an image
            self.image = Image.open(self.image)

        self.padding = get_padding(kwargs, 0)

        if (not self.width) and (not self.height):
            self.width = self.image.width
            self.height = self.image.height
        elif not self.width:
            self.width = int(self.image.width *
                             (self.height / self.image.height))
        elif not self.height:
            self.height = int(self.image.height *
                              (self.width / self.image.width))
        self.width += self.padding[1] + self.padding[3]
        self.height += self.padding[0] + self.padding[2]
        # else both were set

    def render(self, draw, image, x, y, width, height):
        if not self.image:
            return image, draw  # no image, so this is basically an empty cell
        actual_image = self.image.resize(
            (self.width - (self.padding[1] + self.padding[3]), self.height - (self.padding[0] + self.padding[2])), Image.ANTIALIAS)
        image = paste_image(image, actual_image, x +
                            self.padding[3], y + self.padding[0])
        draw = ImageDraw.Draw(image)
        return image, draw


class Table:
    def __init__(self, background=None, border_size=0):
        self.rows = []
        self.background = background
        self.border_size = get_padding(border_size)

    def add_row(self, row):
        self.rows.append(row)

    def render(self):
        row_height = []
        for row in self.rows:
            height = None
            for cell in row:
                if cell and cell.height:
                    if not height or height < cell.height:
                        height = cell.height
            row_height.append(height)

        column_count = max(map(len, self.rows))
        column_width = []
        for col in range(column_count):
            width = 0
            for row in self.rows:
                if len(row) <= col or row[col] is None:
                    continue
                if row[col].width:
                    if not width or width < row[col].width:
                        width = row[col].width
            column_width.append(width)

        image = Image.new('RGBA', (int(sum(column_width) + (self.border_size[1] + self.border_size[3])), int(
            sum(row_height) + self.border_size[0] + self.border_size[2])))
        draw = ImageDraw.Draw(image)
        if self.background:
            draw.rectangle([0, 0, image.size[0], image.size[1]],
                           fill=self.background)

        y = self.border_size[0]
        for row in range(len(self.rows)):
            x = self.border_size[3]
            for column in range(column_count):
                if len(self.rows[row]) <= column or self.rows[row][column] is None:
                    continue
                image, draw = self.rows[row][column].base_render(
                    draw, image, x, y, column_width[column], row_height[row])
                x += column_width[column]
            y += row_height[row]

        return image
