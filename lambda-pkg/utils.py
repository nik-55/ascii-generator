from PIL import Image
import numpy as np


def ascii_generator(img_path: str):
    img = Image.open(img_path)

    gray_img = img.convert("L").resize((128, 128))
    colored_img = img.resize((128, 128))

    gscale = r"$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

    gray_array = np.array(gray_img)
    colored_array = np.array(colored_img)
    colored_array = colored_array.tolist()

    gray_str = ""
    color_str = ""

    for row in range(0, 128):
        for col in range(0, 128):
            temp = gray_array[row][col] // 3.7
            ch = gscale[69 - int(temp)]
            gray_str = gray_str + ch
            r, b, g = colored_array[row][col][:3]

            color_str = color_str + "\033" + f"[38;2;{r};{g};{b}m{ch}" + "\033[0m"

        gray_str = gray_str + "\n"
        color_str = color_str + "\n"

    return gray_str, colored_array, color_str
