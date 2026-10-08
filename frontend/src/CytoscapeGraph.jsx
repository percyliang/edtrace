import { useEffect, useRef, useState } from 'react';

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
 * Each Cytoscape instance runs a render loop every frame (even when idle), so an instance only exists
 * while the graph is on (or near) the screen; the selection and pan are kept across instances.
 */
export default function CytoscapeGraph({ data, style }) {
  const ref = useRef(null);
  const [nearScreen, setNearScreen] = useState(false);
  const saved = useRef({selected: [], pan: null, zoom: null});  // State to restore when recreating the instance

  // Forget the saved state when showing a different graph
  useEffect(() => {
    saved.current = {selected: [], pan: null, zoom: null};
  }, [data]);

  // Track whether the graph is on (or near) the screen
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => setNearScreen(entry.isIntersecting), {rootMargin: "300px"});
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!nearScreen) {
      return;
    }
    let cy = null;
    let cancelled = false;
    import('cytoscape').then(({ default: cytoscape }) => {
      if (cancelled || !ref.current) {
        return;
      }
      cy = cytoscape({
        container: ref.current,
        // Give edges stable ids (so that their selection can be restored)
        elements: [...data.nodes, ...data.edges.map((edge, i) => ({...edge, data: {id: `edge-${i}`, ...edge.data}}))],
        style: [...defaultStylesheet, ...(data.stylesheet || []), ...selectionStylesheet],
        layout: {padding: 20, ...data.layout},
        // Clicking an element toggles whether it's selected (so multiple elements can be selected)
        selectionType: "additive",
        // Nodes stay where they are (no dragging), and no zooming in or out
        autoungrabify: true,
        userZoomingEnabled: false,
      });
      // Restore what was selected and where we panned to
      const {selected, pan, zoom} = saved.current;
      selected.forEach((id) => cy.getElementById(id).select());
      if (pan) {
        cy.viewport({pan, zoom});
      }
    });
    return () => {
      cancelled = true;
      if (cy) {
        saved.current = {selected: cy.$(":selected").map((element) => element.id()), pan: cy.pan(), zoom: cy.zoom()};
        cy.destroy();
      }
    };
  }, [data, nearScreen]);

  return <div ref={ref} style={{width: data.width || 500, height: data.height || 200, ...style}} />;
}
