import random
import sys


def colorize(input_string, foreground_color, background_color=""):
    reset_code = "\033[0m"

    foreground_colors = {
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37"
    }

    background_colors = {
        "black": "49",
        "red": "41",
        "green": "42",
        "yellow": "43",
        "blue": "44",
        "magenta": "45",
        "cyan": "46",
        "white": "47"
    }

    if background_color == "":
        new_string = "\033[" + foreground_colors[foreground_color.lower()]
        new_string += "m" + str(input_string) + reset_code
    else:
        new_string = "\033[" + foreground_colors[foreground_color.lower()]
        new_string += ";" + background_colors[background_color.lower()]
        new_string += "m" + str(input_string) + reset_code

    return new_string


def colorize_and_print(input_string, foreground_color, background_color=""):
    new_string = colorize(input_string, foreground_color, background_color)

    print(new_string)


def randomize_color():
    random_number = random.randint(0, 7)

    correspondence_dict = {
        0: "black",
        1: "red",
        2: "green",
        3: "yellow",
        4: "blue",
        5: "magenta",
        6: "cyan",
        7: "white"
    }

    return correspondence_dict[random_number]


def move_cursor(line, offset=0):
    print(f"\033[{line};{offset}H", end='', flush=True)


def scroll_up(number_of_lines):
    sys.stdout.write("\033[F" * number_of_lines)
    sys.stdout.flush()


class progress_bar:
    def __init__(self, steps):
        if steps < 1:
            raise Exception("Invalid number of steps.")

        self.progress = 0
        self.printed = 0
        self.steps = steps

    def start(self):
        print("Patiente... ", end='')

    def step(self):
        default_width = 9*3
        self.progress += 1
        if self.progress == self.steps:
            return

        iterator = default_width//self.steps

        if self.steps == self.progress + 1:
            iterator = default_width - self.printed

        for i in range(iterator):
            print("◼", end='')
            self.printed += 1
            if self.printed == default_width:
                print()
