import sys
from PIL import Image

def mouth_display_png(image_absolute_path, threshold=70,
                      invert=False, x=0, y=0):
    """Converts a png image into the appropriate encoding for the
        Arduino Mark I enclosure.

        NOTE: extract this out of api.py when re structuing the
              enclosure folder

        Args:
            image_absolute_path (string): The absolute path of the image
            threshold (int): The value ranges from 0 to 255. The pixel will
                             draw on the faceplate it the value is below a
                             threshold
            invert (bool): inverts the image being drawn.
            x (int): x offset for image
            y (int): y offset for image
        """
    # to understand how this funtion works you need to understand how the
    # Mark I arduino proprietary encoding works to display to the faceplate
    img = Image.open(image_absolute_path).convert("RGBA")
    img2 = Image.new('RGBA', img.size, (255, 255, 255))
    width = img.size[0]
    height = img.size[1]

    # strips out alpha value and blends it with the RGB values
    img = Image.alpha_composite(img2, img)
    img = img.convert("L")

    # crop image to only allow a max width of 16
    if width > 32:
        img = img.crop((0, 0, 32, height))
        width = img.size[0]
        height = img.size[1]

    # crop the image to limit the max height of 8
    if height > 8:
        img = img.crop((0, 0, width, 8))
        width = img.size[0]
        height = img.size[1]

    encode = ""

    # Each char value represents a width number starting with B=1
    # then increment 1 for the next. ie C=2
    width_codes = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
                   'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
                   'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a']

    height_codes = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']

    encode += width_codes[width - 1]
    encode += height_codes[height - 1]

    # Turn the image pixels into binary values 1's and 0's
    # the Mark I face plate encoding uses binary values to
    # binary_values returns a list of 1's and 0s'. ie ['1', '1', '0', ...]
    binary_values = []
    for i in range(width):
        for j in range(height):
            if img.getpixel((i, j)) < threshold:
                if invert is False:
                    binary_values.append('1')
                else:
                    binary_values.append('0')
            else:
                if invert is False:
                    binary_values.append('0')
                else:
                    binary_values.append('1')

    # these values are used to determine how binary values
    # needs to be grouped together
    number_of_top_pixel = 0
    number_of_bottom_pixel = 0

    if height > 4:
        number_of_top_pixel = 4
        number_of_bottom_pixel = height - 4
    else:
        number_of_top_pixel = height

    # this loop will group together the individual binary values
    # ie. binary_list = ['1111', '001', '0101', '100']
    binary_list = []
    binary_code = ''
    increment = 0
    alternate = False
    for val in binary_values:
        binary_code += val
        increment += 1
        if increment == number_of_top_pixel and alternate is False:
            # binary code is reversed for encoding
            binary_list.append(binary_code[::-1])
            increment = 0
            binary_code = ''
            alternate = True
        elif increment == number_of_bottom_pixel and alternate is True:
            binary_list.append(binary_code[::-1])
            increment = 0
            binary_code = ''
            alternate = False

    # Code to let the Makrk I arduino know where to place the
    # pixels on the faceplate
    pixel_codes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                   'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']

    for binary_values in binary_list:
        number = int(binary_values, 2)
        pixel_code = pixel_codes[number]
        encode += pixel_code

    return encode

if __name__ == '__main__':
    print mouth_display_png("/home/user/.mycroft/third_party_skills/mycroft-music-skill/music.png")