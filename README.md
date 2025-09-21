# edtrace

edtrace (Educational Tracer) is a tool that allows you write a Python program,
capture an execution trace of it, and step through the code in a web browser.
Some of the code elements can produce markdown, images, and plots, allowing for
an enhanced multimedia experience.

edtrace was primarily designed to create **executable lectures**, where a
Python program replaces lecture notes or slides, allowing for deep integration
of code and ideas.  Or it can simply be used on any Python program, and allow a
user to explore its execution.

1. Create a simple Python program `hello.py`:

```python
from edtrace import text

def main():
    x = 3  # @inspect x
    text("Welcome!")
    x += 1  # @inspect x
```

2. Execute the program and record the trace (saved in `var/traces/hello.json`):

```sh
uv add --upgrade edtrace
python -m edtrace.execute -m hello
```

3. View the trace in a web browser (this part is a bit clunky):

```sh
git clone https://github.com/percyliang/edtrace
cd edtrace/frontend
npm run dev    # For development
npm run build  # For production
```
