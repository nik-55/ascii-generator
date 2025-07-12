from PIL import Image
import numpy as np


def ascii_generator(img_path: str):
    img = Image.open(img_path)

    gry = img.convert("L").resize((128, 128))
    clr = img.resize((128, 128))

    gscale = r"$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

    clr_array = np.array(clr)
    gray_array = np.array(gry)

    st = ""

    for row in range(0, 128):
        for col in range(0, 128):
            temp = gray_array[row][col] // 3.7
            st = st + gscale[69 - int(temp)]

        st = st + "\n"

    return st, clr_array
