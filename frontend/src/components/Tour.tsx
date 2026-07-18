import { CSSProperties, useCallback, useEffect, useState } from "react";

export interface TourStep {
  /** CSS selector of the element to highlight (e.g. '[data-tour="new-task"]'). */
  selector: string;
  title: string;
  description: string;
}

interface TourProps {
  steps: TourStep[];
  /** Called when the tour finishes or is skipped. */
  onClose: () => void;
}

interface Spotlight {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PAD = 8; // padding around the highlighted element
const TOOLTIP_WIDTH = 320;
const TOOLTIP_HEIGHT_ESTIMATE = 190;

/**
 * Hand-rolled onboarding tour: a semi-transparent overlay with a spotlight
 * hole over the target element (via a giant box-shadow) plus a tooltip bubble.
 * Steps whose selector matches nothing in the DOM are skipped.
 */
export default function Tour({ steps, onClose }: TourProps) {
  const [index, setIndex] = useState(0);
  const [spot, setSpot] = useState<Spotlight | null>(null);

  // Keep only steps whose target element currently exists in the DOM.
  const validSteps = steps.filter((s) => document.querySelector(s.selector));
  const step = validSteps[index];

  const measure = useCallback(() => {
    if (!step) return;
    const el = document.querySelector(step.selector);
    if (!el) return;
    const r = el.getBoundingClientRect();
    setSpot({
      top: r.top - PAD,
      left: r.left - PAD,
      width: r.width + PAD * 2,
      height: r.height + PAD * 2,
    });
  }, [step]);

  useEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [measure]);

  // No highlightable steps at all: nothing to show.
  useEffect(() => {
    if (validSteps.length === 0) onClose();
  }, [validSteps.length, onClose]);

  if (!step || !spot) return null;

  const isFirst = index === 0;
  const isLast = index === validSteps.length - 1;

  // Prefer placing the tooltip below the spotlight; flip above if there is
  // not enough room, and clamp it inside the viewport horizontally.
  const below = spot.top + spot.height + 12;
  const placeAbove =
    below + TOOLTIP_HEIGHT_ESTIMATE > window.innerHeight && spot.top > TOOLTIP_HEIGHT_ESTIMATE;
  const tooltipTop = placeAbove ? spot.top - 12 : below;
  const tooltipLeft = Math.min(
    Math.max(12, spot.left),
    window.innerWidth - TOOLTIP_WIDTH - 12
  );

  const overlayStyle: CSSProperties = {
    position: "fixed",
    inset: 0,
    zIndex: 1000,
  };

  const spotlightStyle: CSSProperties = {
    position: "fixed",
    top: spot.top,
    left: spot.left,
    width: spot.width,
    height: spot.height,
    borderRadius: 8,
    // The huge spread creates the dimmed overlay with a "hole" over the target.
    boxShadow: "0 0 0 9999px rgba(15, 23, 42, 0.65)",
    outline: "2px solid #3b82f6",
    pointerEvents: "none",
    transition: "all 0.2s ease",
  };

  const tooltipStyle: CSSProperties = {
    position: "fixed",
    top: tooltipTop,
    left: tooltipLeft,
    transform: placeAbove ? "translateY(-100%)" : "none",
    width: TOOLTIP_WIDTH,
    background: "#fff",
    color: "#0f172a",
    borderRadius: 10,
    padding: 16,
    boxShadow: "0 8px 30px rgba(0,0,0,0.35)",
    fontFamily: "system-ui, sans-serif",
  };

  const btnStyle: CSSProperties = {
    padding: "6px 14px",
    fontSize: 13,
    borderRadius: 6,
    border: "1px solid #cbd5e1",
    background: "#fff",
    cursor: "pointer",
  };

  return (
    <div style={overlayStyle}>
      <div style={spotlightStyle} />
      <div style={tooltipStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
          }}
        >
          <strong style={{ fontSize: 15 }}>{step.title}</strong>
          <span style={{ fontSize: 12, color: "#64748b" }}>
            {index + 1} / {validSteps.length}
          </span>
        </div>
        <p style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>
          {step.description}
        </p>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <button onClick={onClose} style={{ ...btnStyle, border: "none", color: "#64748b" }}>
            Skip
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            {!isFirst && (
              <button onClick={() => setIndex((i) => i - 1)} style={btnStyle}>
                Back
              </button>
            )}
            <button
              onClick={() => (isLast ? onClose() : setIndex((i) => i + 1))}
              style={{
                ...btnStyle,
                background: "#3b82f6",
                border: "none",
                color: "#fff",
                fontWeight: 600,
              }}
            >
              {isLast ? "Finish" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
