#!/usr/bin/env python3

"""Write a long string to an image, wrapped to fit the image size
"""

from PIL import Image, ImageFont, ImageDraw

IMG_WIDTH = 800
IMG_HEIGHT = 800
BG_COLOR = "#cceeff"
LINE_COLOR = "#000088"
TEXT_COLOR = "black"

# How much space to leave outside the text (pixels)
BORDER = 10

# Extra spacing between lines (pixels)
LINESPACING = 0

# PIL, unbelievably, has no way to get fonts from the system
# font handler, and no way to specify a font name in a
# cross-platform way; it can only handle filenames.
FONTFILENAME = 'FreeSerifBold.ttf'


def generate_image(width, height, bg_color):
    img = Image.new(mode="RGB", size=(IMG_WIDTH, IMG_HEIGHT))

    imgdraw = ImageDraw.Draw(img)

    # Background
    imgdraw.rectangle([(0, 0), (IMG_WIDTH, IMG_HEIGHT)], fill = BG_COLOR)

    # border = 30
    # imgdraw.rectangle([(border, border),
    #                    (IMG_WIDTH-border, IMG_HEIGHT-border)],
    #                   fill = None, outline=LINE_COLOR, width=6)

    return img, imgdraw


def draw_text_wrapped(text, imgdraw, font, imgsize, init_y, textcolor,
                      border, linespacing=0):
        """Draw text in an image, wrapping as needed.
           Return the total text height drawn.

           text:      a long string, without newlines
           imgdraw:   a PIL ImageDraw object
           font:      a PIL ImageFont object
           init_y:    how high to start the text
           textcolor: a color specifier string
           border:    how many pixels border to leave around text
           linespacing: extra space between lines (default 0)
        """
        if not text.strip():
            return init_y

        # Width of the area available for text
        width = imgsize[0] - border*2

        left, top, right, bottom = font.getbbox(text)

        av_char_width = width / len(text)

        # Find a first line that fits
        line_len = int(width / av_char_width)
        if line_len >= len(text):
            line_len = len(text)
        while True:
            if line_len == len(text) or text[line_len-1].isspace():
                left, top, right, bottom = font.getbbox(text[:line_len])
                if right - left < width:
                    # It fits, hooray!
                    break
            # Doesn't fit yet. Reduce line size by 1 and try again.
            line_len -= 1
            if line_len <= 0:
                # Eventually, figure out how to break words.
                # For now, just break in the middle of the word.
                break

        if line_len <= 0:
            print("couldn't fit", text, file=sys.stderr)

        # Now line_len is the index where we'll break
        left, top, right, bottom = font.getbbox(text[:line_len])
        startx = (width - (right - left))/2 + border
        imgdraw.text((border + startx, init_y), text[:line_len],
                     font=font, fill=textcolor)

        # Skip over space, if there is one
        try:
            if text[line_len].isspace():
                line_len += 1
        except IndexError:
            # using the whole string, no more to get
            pass

        height = draw_text_wrapped(text[line_len:], imgdraw, font, imgsize,
                                   init_y + bottom + LINESPACING,
                                   textcolor, border, linespacing=0)
        return height


if __name__ == '__main__':
    import sys

    img, imgdraw = generate_image(IMG_WIDTH, IMG_HEIGHT, BG_COLOR)

    font = ImageFont.truetype(FONTFILENAME, 80)

    bottom = draw_text_wrapped(' '.join(sys.argv[1:]),
                      imgdraw, font, (IMG_WIDTH, IMG_HEIGHT), 60,
                      TEXT_COLOR, BORDER, LINESPACING)

    font = ImageFont.truetype(FONTFILENAME, 50)

    draw_text_wrapped(' '.join(sys.argv[1:]),
                      imgdraw, font, (IMG_WIDTH, IMG_HEIGHT), bottom + 100,
                      TEXT_COLOR, BORDER, LINESPACING)

    img.show()
