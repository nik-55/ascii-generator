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
    clr_str = ""

    for row in range(0, 128):
        for col in range(0, 128):
            temp = gray_array[row][col] // 3.7
            ch = gscale[69 - int(temp)]
            st = st + ch
            r, b, g = clr_array[row][col][:3]

            clr_str = clr_str + "\033" + f"[38;2;{r};{g};{b}m{ch}" + "\033[0m"

        st = st + "\n"
        clr_str = clr_str + "\n"

    return st, clr_array, clr_str
