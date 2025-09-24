import argparse
import math
import importlib
import inspect
import sys
import json
import traceback
import numpy as np
import torch
import sympy
import os
from dataclasses import dataclass, asdict, field, is_dataclass, fields
from .execute_util import Rendering, pop_renderings
from .file_util import relativize


@dataclass(frozen=True)
class StackElement:
    path: str
    """The path to the file containing the code."""

    line_number: int
    """The line number of the code."""

    function_name: str
    """The name of the function that we're in."""

    code: str
    """The source code that is executed."""


@dataclass(frozen=True)
class Value:
    """Represents the value of an environment variable."""
    type: str
    """The type of the value."""

    contents: any
    """The contents itself."""

    dtype: str | None = None
    """If `contents` is a tensor/array, then this is its dtype (e.g., "float32")."""

    shape: list[int] | None = None
    """If `contents` is a tensor/array, then this is its shape (e.g., [2, 3] for a 2x3 matrix)."""


@dataclass
class Step:
    """Not frozen because the renderings need to be updated."""
    stack: list[StackElement]
    """The stack of function calls."""

    env: dict[str, Value]
    """The local variables including function arguments(that we're @inspect-ing)."""

    renderings: list[Rendering] = field(default_factory=list)
    """The output of the code (see execute_util.py)."""


@dataclass(frozen=True)
class Trace:
    files: dict[str, str]
    """Mapping from file path to file contents."""

    hidden_line_numbers: dict[str, list[int]]
    """Mapping from file path to list of line numbers to hide."""

    steps: list[Step]
    """The steps of the trace."""


DIRECTIVE_INSPECT = "@inspect"  # Show (and update) the value of a variable
DIRECTIVE_CLEAR = "@clear"  # Stop showing the value of a variable
DIRECTIVE_STEPOVER = "@stepover"  # Don't trace into the current line
DIRECTIVE_HIDE = "@hide"  # Don't show this line at all
ACCEPTED_DIRECTIVES = [DIRECTIVE_INSPECT, DIRECTIVE_CLEAR, DIRECTIVE_STEPOVER, DIRECTIVE_HIDE]


@dataclass(frozen=True)
class Directive:
    name: str
    """The name of the directive."""
    args: list[str]
    """The arguments of the directive."""


def parse_directives(line: str) -> list[Directive]:
    """
    Parse the directives from the line.
    Examples:
        "... # @inspect x y @hide" -> [Directive(name="@inspect", args=["x", "y"]), Directive(name="@hide", args=[])]
    """
    # Get tokens after the "#"
    if "#" not in line:
        return []
    tokens = line.split("#")[1].split()
    directives: list[Directive] = []
    for token in tokens:
        if token.startswith("@"):
            if token not in ACCEPTED_DIRECTIVES:
                print(f"WARNING: {token} is not a valid directive.")
            name = token
            args = []
            directives.append(Directive(name=name, args=args))
        else:
            if len(directives) > 0:
                directives[-1].args.append(token)
    return directives


def get_inspect_expressions(directives: list[Directive]) -> list[str]:
    """
    If code contains "@inspect <variable>" (as a comment), return those variables.
    Example code:
        x, y = str.split("a,b")  # @inspect x @inspect y
    We would return ["x", "y"]
    """
    variables = []
    for directive in directives:
        if directive.name == DIRECTIVE_INSPECT:
            variables.extend(directive.args)
    return variables


def get_clear_expressions(directives: list[Directive]) -> list[str]:
    """
    If code contains "@clear <variable>" (as a comment), return the variables to clear.
    Example code:
        y = np.array([1, 2, 3])  # @clear y
    We would return ["y"]
    """
    variables = []
    for directive in directives:
        if directive.name == DIRECTIVE_CLEAR:
            variables.extend(directive.args)
    return variables


def to_primitive(value: any) -> any:
    if isinstance(value, (int, float, str, bool)):
        return value
    # Force it to be a primitive
    return str(value)


def to_serializable_value(value: any) -> Value:
    """Convert `value` to something that's serializable to JSON."""
    value_type = get_type_str(value)

    # Primitive types
    if isinstance(value, (bool, int, float, str)):
        # Serialize inf and nan values specially since JSON doesn't support it
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return Value(type=value_type, contents=str(value))
        return Value(type=value_type, contents=value)

    # Tensors
    if isinstance(value, (np.int64,)):
        return Value(type=value_type, contents=int(value))  # Hope no rounding issues
    if isinstance(value, (np.float64,)):
        return Value(type=value_type, contents=float(value))  # Hope no rounding issues
    if isinstance(value, np.ndarray):
        return Value(type=value_type, dtype=str(value.dtype), shape=list(value.shape), contents=value.tolist())
    if isinstance(value, torch.Tensor):
        return Value(type=value_type, dtype=str(value.dtype), shape=list(value.shape), contents=value.tolist())

    # Symbols
    if value_type.startswith("sympy.core."):
        if isinstance(value, sympy.core.numbers.Integer):
            return Value(type=value_type, contents=int(value))
        if isinstance(value, sympy.core.numbers.Float):
            return Value(type=value_type, contents=float(value))
        return Value(type=value_type, contents=str(value))

    # Recursive types
    if isinstance(value, (tuple, list)):
        return Value(type=value_type, contents=[to_serializable_value(item) for item in value])
    if isinstance(value, dict):
        return Value(type=value_type, contents={to_primitive(k): to_serializable_value(v) for k, v in value.items()})
    if is_dataclass(value):
        return Value(type=value_type, contents={
            field.name: to_serializable_value(getattr(value, field.name))
            for field in fields(value)
        })

    # If the class has a designated asdict method, use it
    if hasattr(value, "asdict"):
        return Value(type=value_type, contents=value.asdict())

    # Force contents to be a string to avoid serialization errors
    return Value(type=value_type, contents=str(value))


def get_type_str(value: any) -> str:
    """Return the string representation of the type of `value`."""
    value_type = type(value)
    if value_type.__module__ == "builtins":  # e.g., int, float, str, bool
        return value_type.__name__
    return value_type.__module__ + "." + value_type.__name__


def execute(module_name: str, inspect_all_variables: bool) -> Trace:
    """
    Execute the module and return a trace of the execution.
    """
    steps: list[Step] = []

    # Figure out which files we're actually tracing
    visible_paths = []

    # Stack of locations that we're stepping over
    stepovers = []

    def get_stack() -> list[StackElement]:
        """Return the last element of `stack`, but skip over items where local_trace_func is active."""
        stack = []
        # stack looks like this:
        #   _run_module_as_main _run_code <module> execute [good stuff to return] local_trace_func trace_func get_stack
        items = traceback.extract_stack()
        for item in traceback.extract_stack():
            if item.name in ("_run_module_as_main", "_run_code", "<module>", "execute", "local_trace_func", "trace_func", "get_stack"):
                continue
            stack.append(StackElement(
                path=relativize(item.filename),
                line_number=item.lineno,
                function_name=item.name,
                code=item.line,
            ))
        return stack

    def trace_func(frame, event, arg):
        """
        trace_func and local_trace_func are called on various lines of code when executed.
        - trace_func is called *before* a line of code is executed.
        - local_trace_func is called *after* a line of code has been executed
          and will have the values of the variables.
        We generally keep the local_trace_func version.  However, when you have
        a function call that you're tracing through, you want to keep both
        versions.

        We don't care about all the events, so here are the rules:
        - In local_trace_func, if the previous event was the same line (presumably the trace_func)
        - Remove all trace_func(return)
        """

        # Get the current file path from the frame and skip if not in visible paths
        # to avoid tracing deep into imports (which would be slow and irrelevant)
        current_path = frame.f_code.co_filename
        if current_path not in visible_paths:
            return trace_func

        stack = get_stack()

        if event == "return":
            return trace_func

        # Print the current line of code
        item = stack[-1]

        # Don't step into comprehensions since they're redundant and just stay on the line
        if item.function_name == "<listcomp>":
            return trace_func

        # Handle @stepover (don't recurse)
        directives = parse_directives(item.code)
        if any(directive.name == DIRECTIVE_STEPOVER for directive in directives):
            # If stepping over this line
            if len(stepovers) > 0 and stepovers[-1] == (item.path, item.line_number):
                # Stop skipping since we're back to this line
                stepovers.pop()
            else:
                # Just starting to skip starting here
                stepovers.append((item.path, item.line_number))
        
        # Skip everything that is strictly under stepovers
        if any(stepover[0] == item.path and stepover[1] == item.line_number for stepover in stepovers for item in stack[:-1]):
            return trace_func

        print(f"  [{len(steps)} {os.path.basename(item.path)}:{item.line_number}] {item.code}")

        open_step = Step(
            stack=stack,
            env={},
        )
        if len(steps) == 0 or open_step.stack != steps[-1].stack:  # Only add a step if it's not redundant
            steps.append(open_step)
        open_step_index = len(steps) - 1

        def local_trace_func(frame, event, arg):
            """This is called *after* a line of code has been executed."""
            # If the last step was the same line, then just use the same one
            # Otherwise, create a new step (e.g., returning from a function)
            if open_step_index == len(steps) - 1:
                close_step = steps[-1]
            else:
                print(f"  [{len(steps)} {os.path.basename(item.path)}:{item.line_number}] {item.code}")

                close_step = Step(
                    stack=stack,
                    env={},
                )
                steps.append(close_step)

            # Update the environment with the actual values
            locals = frame.f_locals
            if inspect_all_variables:
                exprs = locals.keys()
            else:
                exprs = get_inspect_expressions(directives)
            for expr in exprs:
                if "." in expr:  # e.g., node.name
                    var, attr = expr.split(".", 1)
                else:
                    var = expr
                    attr = None
                if var in locals:
                    # Follow the attribute chain
                    value = locals[var]
                    if attr:
                        for attr in attr.split("."):
                            value = getattr(value, attr)
                    close_step.env[expr] = to_serializable_value(value)
                else:
                    print(f"WARNING: variable {var} not found in locals")
                print(f"    env: {expr} = {close_step.env.get(expr)}")
        
            clear_exprs = get_clear_expressions(directives)
            for expr in clear_exprs:
                if expr in locals:
                    close_step.env[expr] = None

            # Capture the renderings of the last line
            close_step.renderings = pop_renderings()

            # Pass control back to the global trace function
            return trace_func(frame, event, arg)

        # Pass control to local_trace_func to update the environment
        return local_trace_func
    
    # Run the module
    module = importlib.import_module(module_name)
    visible_paths.append(inspect.getfile(module))
    sys.settrace(trace_func)
    module.main()
    sys.settrace(None)

    files = {relativize(path): open(path).read() for path in visible_paths}
    hidden_line_numbers = compute_hidden_line_numbers(files)
    trace = Trace(steps=steps, files=files, hidden_line_numbers=hidden_line_numbers)
    return trace


def compute_hidden_line_numbers(files: dict[str, str]) -> dict[str, list[int]]:
    """Compute the line numbers to hide based on the @hide comments."""
    hidden_line_numbers = {}
    for path, contents in files.items():
        hidden_line_numbers[path] = []
        for index, line in enumerate(contents.split("\n")):
            directives = parse_directives(line)
            if any(directive.name == DIRECTIVE_HIDE for directive in directives):
                line_number = index + 1
                hidden_line_numbers[path].append(line_number)
    return hidden_line_numbers



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--module", help="List of modules to execute (e.g., lecture_01)", type=str, nargs="+")
    parser.add_argument("-o", "--output_path", help="Path to save the trace", type=str, default="var/traces")
    parser.add_argument("-I", "--inspect-all-variables", help="Inspect all variables (default: only inspect variables mentioned in @inspect comments)", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.output_path, exist_ok=True)

    for module in args.module:
        module = module.replace(".py", "")  # Just in case
        print(f"Executing {module}...")
        trace = execute(module_name=module, inspect_all_variables=args.inspect_all_variables)
        print(f"{len(trace.steps)} steps")
        output_path = os.path.join(args.output_path, f"{module}.json")
        print(f"Saving trace to {output_path}...")
        with open(output_path, "w") as f:
            json.dump(asdict(trace), f, indent=2)
