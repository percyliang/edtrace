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

2. Execute the program and record the trace:

```sh
uv add --upgrade edtrace
python -m edtrace.execute -m hello
```
The results are saved in `var/traces/hello.json`.

3. View the trace in a web browser (this part is a bit clunky):

```sh
git clone https://github.com/percyliang/edtrace
```

For development:
```sh
npm --prefix=edtrace/frontend run dev
```
and go to [http://localhost:5173](http://localhost:5173) and type in `var/traces/hello.json`.

For production:
```sh
mkdir dist
(cd dist && ln -s ../var && ln -s ../images)    # Symlink so we don't have to make two copies
export VITE_EDTRACE_BASE_DIR=/`basename $PWD`   # Assume this will be hosted at ???.github.io/$EDTRACE_BASE_DIR
export VITE_EDTRACE_DIST_DIR=$PWD               # Absolute path

npm --prefix=edtrace/frontend run build
```
and this writes to `.`.  Git push `index.html` and `assets` so it will show up publicly
(e.g., on a github.io page).
