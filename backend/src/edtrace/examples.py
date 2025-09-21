import numpy as np
import sympy
import torch
from datetime import datetime
from dataclasses import dataclass
from execute_util import text, image, link, system_text


def main():
    display()
    inspect_values()

def compute():
    x = 0
    for i in range(100):
        x = i * i
    return x


def display():
    text("Hello, world!")
    text("Math: $x^2$")
    text("- Bullet 1")
    text("- Bullet 2: this is a long thing that should wrap at some point because it will keep on going on and on")
    text("# Heading 1")
    text("## Heading 2")
    text("### Heading 3")
    text("**Bold** *italic*")
    text("Multiline text: "
         "wrapped around")  # @hide
    text("One text th"), text("at is made up multi"), text("ple text calls")
    image("https://www.google.com/logos/doodles/2025/labor-day-2025-6753651837110707.4-l.webp", width=200)
    link(title="Google", url="https://www.google.com")
    link("https://arxiv.org/abs/2005.14165")
    system_text(["date"])

    x = compute()  # @inspect x @stepover
    text("Should still show the value of x.")
    text("Let's move on (value of x should not be shown).")  # @clear x


def inspect_values():
    # Numpy arrays of different dtypes
    x = np.array([1, 2, 3])  # @inspect x
    x = np.array([1, 2, 3], dtype=np.int8)  # @inspect x
    x = np.array([1, 2, 3], dtype=np.int16)  # @inspect x
    x = np.array([1, 2, 3], dtype=np.int32)  # @inspect x
    x = np.array([1, 2, 3], dtype=np.int64)  # @inspect x
    x = np.array([1, 2, 3], dtype=np.float16)  # @inspect x
    x = np.array([1, 2, 3], dtype=np.float32)  # @inspect x
    x = np.array([1, 2, 3], dtype=np.float64)  # @inspect x

    # PyTorch tensors of different dtypes
    x = torch.tensor([1, 2, 3])  # @inspect x
    x = torch.tensor([1, 2, 3], dtype=torch.int8)  # @inspect x
    x = torch.tensor([1, 2, 3], dtype=torch.int16)  # @inspect x
    x = torch.tensor([1, 2, 3], dtype=torch.int32)  # @inspect x
    x = torch.tensor([1, 2, 3], dtype=torch.int64)  # @inspect x
    x = torch.tensor([1, 2, 3], dtype=torch.float16)  # @inspect x
    x = torch.tensor([1, 2, 3], dtype=torch.float32)  # @inspect x
    x = torch.tensor([1, 2, 3], dtype=torch.float64)  # @inspect x

    # Different scalars
    x = torch.tensor(1, dtype=torch.int64)  # @inspect x
    x = torch.tensor(1, dtype=torch.float64)  # @inspect x
    x = np.int64(1)  # @inspect x
    x = np.float64(1)  # @inspect x

    # Multi-dimensional arrays
    x = np.zeros((2, 3))  # @inspect x
    x = np.zeros((2, 2, 3))  # @inspect x
    x = torch.zeros((2, 3))  # @inspect x
    x = torch.zeros((2, 2, 3))  # @inspect x

    # Sympy
    x = sympy.symbols('x')  # @inspect x
    x = 0 * sympy.symbols('x')  # @inspect x
    x = 0.5 * sympy.symbols('x')  # @inspect x

    # Lists
    x = []  # @inspect x
    x = [1, 2, 3]  # @inspect x
    x = [[1, 2, 3], [4, 5, "hello"]]  # @inspect x

    # Dicts
    x = {}  # @inspect x
    x = {"a": [1, 2, 3], "b": [4, 5, "hello"]}  # @inspect x

    # Dataclasses
    @dataclass(frozen=True)
    class MyDataclass:
        a: int
        b: list[int]
    x = MyDataclass(a=1, b=[2, 3])  # @inspect x

    # Datetimes
    x = datetime.now()  # @inspect x

if __name__ == "__main__":
    main()