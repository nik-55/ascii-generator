from PIL import Image
import numpy as np


def ascii_generator(img_path: str):
    img = Image.open(img_path)

    gry = img.convert("L").resize((128, 128))
    clr = img.resize((128, 128))

    gscale = r"$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

    clr_array = np.array(clr)
    gray_array = np.array(gry)

    for row in range(0, 128):
        for col in range(0, 128):
            temp = gray_array[row][col] // 3.7
            gray_array[row][col] = 69 - temp

    st = ""
    for row in range(0, 128):
        for col in range(0, 128):
            st = st + gscale[gray_array[row][col]]
        st = st + "\n"

    return st, clr_array
