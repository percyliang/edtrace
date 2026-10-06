import { useEffect, useRef } from 'react';

// Neutral defaults; specific styling comes from `data.stylesheet` (appended, so it takes precedence)
const defaultStylesheet = [
  {
    selector: "node",
    style: {
      "label": "data(label)",
      "background-color": "white",
      "border-width": 2,
      "border-color": "#555",
      "color": "#333",
      "font-family": "Helvetica, Arial, sans-serif",
      "font-size": 14,
      "text-valign": "center",
      "text-halign": "center",
    },
  },
  {
    selector: "edge",
    style: {
      "width": 2,
      "line-color": "#999",
      "target-arrow-color": "#999",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "color": "#555",
      "font-family": "Helvetica, Arial, sans-serif",
      "font-size": 12,
      "text-background-color": "white",
      "text-background-opacity": 1,
      "text-background-padding": 2,
    },
  },
  {selector: "edge[label]", style: {"label": "data(label)"}},
];

// Highlight selected (clicked) elements with a bright halo (keeping their own colors);
// applied last so that it takes precedence over `data.stylesheet`
const SELECTED = "#ff8c00";
const selectionStylesheet = [
  {selector: "node:selected", style: {"underlay-color": SELECTED, "underlay-opacity": 0.6, "underlay-padding": 8, "underlay-shape": "ellipse"}},
  {selector: "edge:selected", style: {"underlay-color": SELECTED, "underlay-opacity": 0.6, "underlay-padding": 6, "z-index": 20}},
];

/**
 * Lightweight wrapper around Cytoscape.js.
 * `data` = {nodes, edges, layout, stylesheet, width, height}, where each node/edge is
 * {data, position?, classes?} (Cytoscape's element format).
 * Cytoscape is loaded on demand so that traces without graphs don't pay for it.
 */
export default function CytoscapeGraph({ data, style }) {
  const ref = useRef(null);

  useEffect(() => {
    let cy = null;
    let cancelled = false;
    import('cytoscape').then(({ default: cytoscape }) => {
      if (cancelled || !ref.current) {
        return;
      }
      cy = cytoscape({
        container: ref.current,
        elements: [...data.nodes, ...data.edges],
        style: [...defaultStylesheet, ...(data.stylesheet || []), ...selectionStylesheet],
        layout: {padding: 20, ...data.layout},
        // Clicking an element toggles whether it's selected (so multiple elements can be selected)
        selectionType: "additive",
        // Nodes stay where they are (no dragging), and no zooming in or out
        autoungrabify: true,
        userZoomingEnabled: false,
      });
    });
    return () => {
      cancelled = true;
      if (cy) {
        cy.destroy();
      }
    };
  }, [data]);

  return <div ref={ref} style={{width: data.width || 500, height: data.height || 200, ...style}} />;
}
