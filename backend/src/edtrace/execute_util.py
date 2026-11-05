"""
Functions such as (e.g., note, image, link) populate the list of renderings,
which will be shown in place of the line of code in the interface.
"""

import os
import sys
import inspect
import re
import subprocess
from dataclasses import dataclass
from .file_util import cached, relativize
from .arxiv_util import is_arxiv_link, arxiv_reference
from .reference import Reference

@dataclass(frozen=True)
class CodeLocation:
    """Refers to a specific line of code."""
    path: str
    line_number: int


@dataclass(frozen=True)
class Rendering:
    """
    Specifies what to display instead of a line of code.  Types:
    - text: plain text (verbatim)
    - markdown: to be rendered as markdown
    - image: an image (data = url)
    - video: a video (data = url)
    - link: an link to internal code or external URL
    - plot: a Vega-Lite chart (data = spec)
    - graph: a graph drawn with Cytoscape.js (data = nodes, edges, layout, width, height)
    """
    type: str
    data: str | None = None
    style: dict | None = None
    external_link: Reference | None = None
    internal_link: CodeLocation | None = None
    animate: bool = False
    """Whether to show the renderings of this line one at a time (from the @animate directive)."""

############################################################

def text(message: str, style: dict | None = None, verbatim: bool = False):
    """Make a note (bullet point) with `message`."""
    style = style or {}
    if verbatim:
        messages = message.split("\n")
        style = {
            "fontFamily": "monospace",
            "whiteSpace": "pre",
            **style
        }
    else:
        messages = [message]

    for message in messages:
        _add_rendering(Rendering(type="markdown", data=message, style=style))


def image(url: str, style: dict | None = None, width: int | str | None = None):
    """Show the image at `url`."""
    style = style or {}
    if width is not None:
        style["width"] = width

    if is_url(url):
        path = cached(url, "image")
    else:
        path = url
        if not os.path.exists(path):
            raise ValueError(f"Image not found: {path}")

    _add_rendering(Rendering(type="image", data=path, style=style))


def video(url: str, style: dict | None = None, width: int | str | None = None):
    """Show the video at `url`."""
    style = style or {}
    if width is not None:
        style["width"] = width

    if is_url(url):
        path = cached(url, "video")
    else:
        path = url
        if not os.path.exists(path):
            raise ValueError(f"Video not found: {path}")

    _add_rendering(Rendering(type="video", data=path, style=style))


def is_url(url: str) -> bool:
    """Check if `url` looks like a URL."""
    return url.startswith("http")


def url_reference(url: str, **kwargs):
    """Makes a reference (but doesn't add it to _current_renderings)."""
    if is_arxiv_link(url):
        return arxiv_reference(url, **kwargs)
    else:
        return Reference(url=url, **kwargs)


def link(arg: type | Reference | str | None = None, style: dict | None = None, **kwargs):
    """
    Shows a link.  There are four possible usages:
    1. link(title="...", url="...") [Creates a new reference]
    2. link(arg: Reference) [Shows an existing reference]
    3. link(arg: type) [Shows a link to the code]
    4. link(arg: str) [Creates a new reference with the given URL]
    """
    style = style or {}

    if arg is None:
        reference = Reference(**kwargs)
        _add_rendering(Rendering(type="link", data=reference.label, style=style, external_link=reference))
    elif isinstance(arg, Reference):
        _add_rendering(Rendering(type="link", data=arg.label, style=style, external_link=arg))
    elif isinstance(arg, type) or callable(arg):
        path = inspect.getfile(arg)
        _, line_number = inspect.getsourcelines(arg)
        anchor = CodeLocation(relativize(path), line_number)
        _add_rendering(Rendering(type="link", data=arg.__name__, style=style, internal_link=anchor))
    elif isinstance(arg, str):
        reference = url_reference(url=arg, **kwargs)
        _add_rendering(Rendering(type="link", data=reference.label, style=style, external_link=reference))
    else:
        raise ValueError(f"Invalid argument: {arg}")


def plot(spec: any):
    """Show a plot given `spec`."""
    _add_rendering(Rendering(type="plot", data=spec))


def graph(spec: dict | None, style: dict | None = None):
    """Show a graph given `spec` (from `make_graph`), drawn (interactively) with Cytoscape.js in the browser (nothing if `spec` is None)."""
    if spec is None:
        return
    _add_rendering(Rendering(type="graph", data=spec, style=style or {}))


def make_graph(nodes: list[dict], edges: list[dict], layout: str | dict = "preset", stylesheet: list[dict] | None = None,
               width: int = 500, height: int = 200) -> dict:
    """
    Return the spec of a graph (to show with `graph`).
    - `nodes`: list of {"id", "label" (defaults to id), "x", "y" (position, for the "preset" layout),
      "classes" (optional), and any other data fields (which `stylesheet` can refer to)}
    - `edges`: list of {"source", "target", "label" (optional), "classes" (optional), and any other data fields}
    - `layout`: name of a Cytoscape layout ("preset" uses the x, y of the nodes; e.g., "breadthfirst", "circle", "grid", "cose")
      or a dict of layout options
    - `stylesheet`: Cytoscape stylesheet ([{"selector", "style"}]), applied after the defaults
    - `width`, `height`: size of the graph in pixels
    """
    def element(item: dict, is_node: bool) -> dict:
        """Convert to Cytoscape's element format: {data, position, classes}."""
        item = dict(item)
        result = {}
        if is_node and "x" in item and "y" in item:
            result["position"] = {"x": item.pop("x"), "y": item.pop("y")}
        if "classes" in item:
            result["classes"] = item.pop("classes")
        for key in ("id", "source", "target"):  # Cytoscape ids must be strings
            if key in item:
                item[key] = str(item[key])
        if is_node:
            item.setdefault("label", item["id"])
        result["data"] = item
        return result
    return {
        "nodes": [element(node, is_node=True) for node in nodes],
        "edges": [element(edge, is_node=False) for edge in edges],
        "layout": {"name": layout} if isinstance(layout, str) else layout,
        "stylesheet": stylesheet or [],
        "width": width,
        "height": height,
    }


def note(message: str):
    """Show a note."""
    _add_rendering(Rendering(type="note", data=message))


############################################################

# Accumulate the renderings during execution (gets flushed).
_current_renderings: list[Rendering] = []
# For each rendering, the ids of the frame that produced it (the caller of `text`, `graph`, etc.) and of its caller
_current_rendering_frame_ids: list[tuple[int, int]] = []

def _add_rendering(rendering: Rendering):
    """Add `rendering`, remembering which frame produced it (frame 0 is this function, 1 is `text`, `graph`, etc.)."""
    frame = sys._getframe(2)
    _current_renderings.append(rendering)
    _current_rendering_frame_ids.append((id(frame), id(frame.f_back)))

def pop_renderings(frame=None) -> list[Rendering]:
    """
    Return the renderings and clear the list.
    If `frame` is given, only return the renderings produced by `frame` or the functions it called directly
    (e.g., a helper that plots), not ones produced deeper (e.g., when stepping over a call that loops over a helper).
    """
    renderings = [
        rendering for rendering, (frame_id, caller_id) in zip(_current_renderings, _current_rendering_frame_ids)
        if frame is None or id(frame) in (frame_id, caller_id)
    ]
    _current_renderings.clear()
    _current_rendering_frame_ids.clear()
    return renderings


def system_text(command: list[str]):
    output = subprocess.check_output(command).decode('utf-8')
    output = remove_ansi_escape_sequences(output)
    text(output, verbatim=True)


def remove_ansi_escape_sequences(text):
    ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape_pattern.sub('', text)
