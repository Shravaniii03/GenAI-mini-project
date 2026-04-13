"""
diagram_renderer.py — Dynamic Activity Diagram Generator
Reads actual pipeline output JSON and generates diagrams.
Handles all key variations from Agent1.py output.
"""
import os, sys, json, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

C_BG="#FFFFFF"; C_BOX_FILL="#FFFFFF"; C_BOX_BORDER="#000000"
C_BORDER_VIOL="#CC0000"; C_TEXT="#000000"; C_TEXT_VIOL="#CC0000"
C_ARROW="#000000"; C_YES_NO="#555555"

def draw_box(ax, x, y, w, h, label, violation=False, fontsize=8.5):
    b = C_BORDER_VIOL if violation else C_BOX_BORDER
    lw = 2.5 if violation else 1.2
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h,
        boxstyle="round,pad=0.04", linewidth=lw,
        edgecolor=b, facecolor=C_BOX_FILL, zorder=4))
    ax.text(x, y, label, ha="center", va="center", fontsize=fontsize,
        color=C_TEXT_VIOL if violation else C_TEXT,
        fontweight="bold" if violation else "normal",
        zorder=5, multialignment="center")

def draw_diamond(ax, x, y, w, h, label, violation=False, fontsize=7.5):
    col = C_BORDER_VIOL if violation else C_BOX_BORDER
    ax.add_patch(plt.Polygon(
        [[x, y+h/2],[x+w/2, y],[x, y-h/2],[x-w/2, y]],
        closed=True, linewidth=2.5 if violation else 1.2,
        edgecolor=col, facecolor=C_BOX_FILL, zorder=4))
    ax.text(x, y, label, ha="center", va="center", fontsize=fontsize,
        color=C_TEXT_VIOL if violation else C_TEXT,
        fontweight="bold" if violation else "normal",
        zorder=5, multialignment="center")

def arr(ax, x1, y1, x2, y2, label="", side="right"):
    ax.annotate("", xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=1.2), zorder=3)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        dx = 0.12 if side=="right" else -0.12
        ax.text(mx+dx, my, label, ha="left" if side=="right" else "right",
            va="center", fontsize=7, color=C_YES_NO, style="italic", zorder=6)

def draw_start(ax, x, y):
    ax.add_patch(plt.Circle((x,y), 0.14, color=C_BOX_BORDER, zorder=5))

def draw_end(ax, x, y):
    ax.add_patch(plt.Circle((x,y), 0.19, color=C_BOX_BORDER, zorder=5))
    ax.add_patch(plt.Circle((x,y), 0.11, color=C_BG, zorder=6))


def extract_scenario_fields(s):
    """
    Safely extract fields from scenario dict.
    Handles both Agent1.py output format and test formats.
    """
    # delay_ms — try multiple keys
    delay = (s.get("delay_ms") or
             s.get("actual_delay_ms") or
             s.get("actual_delay") or 0)

    # risk_score
    risk = (s.get("risk_score") or
            s.get("risk") or 0)

    # violation
    violation = bool(s.get("violation", False))

    # road_condition — may be nested in parameters
    road = (s.get("road_condition") or
            s.get("parameters", {}).get("road_condition") or
            "unknown")

    # severity
    severity = s.get("severity", "UNKNOWN")

    # attack_chain
    attack_chain = s.get("attack_chain", [])
    if isinstance(attack_chain, str):
        attack_chain = [attack_chain]

    # event_chain_timing
    chain_timing = s.get("event_chain_timing", [])

    # type
    stype = s.get("type", "unknown")

    return delay, risk, violation, road, severity, attack_chain, chain_timing, stype


def draw_dynamic_scenario(ax, scenario_data, event_chain, max_delay_ms):
    """Draw one scenario diagram from actual pipeline output."""

    delay, risk, violation, road, severity, attack_chain, chain_timing, stype = \
        extract_scenario_fields(scenario_data)

    timing_map = {t.get("step",""): t.get("time_ms",0) for t in chain_timing}

    n = len(event_chain)
    step_h = 1.4
    total_h = n * step_h + 5
    ax.set_xlim(0, 8)
    ax.set_ylim(0, total_h)
    ax.set_facecolor(C_BG)
    ax.axis("off")

    # Title
    verdict_txt = "VIOLATION" if violation else "PASS"
    color = "#CC0000" if violation else "#006633"
    ax.set_title(
        f"{stype.upper()} Scenario — {verdict_txt}\n"
        f"Delay: {delay}ms / {max_delay_ms}ms  |  Risk: {round(risk,2)}  |  Road: {road}  |  {severity}",
        fontsize=9, color=color, fontweight="bold", pad=6
    )

    cx = 4.0
    y = total_h - 0.7
    draw_start(ax, cx, y)
    y -= 0.35

    for i, step in enumerate(event_chain):
        step_label = step.replace("_", " ").title()
        t_ms = timing_map.get(step, 0)
        if t_ms:
            step_label += f"\n[{t_ms}ms]"

        y -= 0.45
        arr(ax, cx, y+0.3, cx, y+0.05)

        # Is this step a decision/detect step?
        is_dec = any(k in step.lower() for k in
                     ["detect","decide","check","fuse","found","pedestrian","obstacle"])

        # Is this step violated?
        is_viol = False
        if violation:
            # Mark last step if total delay exceeded
            if i == len(event_chain) - 1 and delay > max_delay_ms:
                is_viol = True
            # Mark steps matching attack chain
            if attack_chain:
                is_viol = any(a.lower() in step.lower() or step.lower() in a.lower()
                             for a in attack_chain[:2])

        if is_dec:
            draw_diamond(ax, cx, y-0.18, 3.6, 0.75,
                        step_label, violation=is_viol, fontsize=7.5)
            arr(ax, cx, y-0.56, cx, y-0.88, label="yes", side="right")
            y -= 0.88
        else:
            draw_box(ax, cx, y-0.18, 3.6, 0.65,
                    step_label, violation=is_viol, fontsize=8.5)
            y -= 0.65

    arr(ax, cx, y-0.1, cx, y-0.45)
    draw_end(ax, cx, y-0.62)

    # Timing progress bar at bottom
    if max_delay_ms > 0 and delay > 0:
        bar_y  = 0.6
        bar_w  = 6.0
        ratio  = delay / max_delay_ms
        fill_w = bar_w * min(ratio, 1.0)
        over_w = bar_w * max(ratio - 1.0, 0)
        fc = "#CC0000" if violation else "#006633"

        ax.add_patch(mpatches.FancyBboxPatch((1.0, bar_y-0.13), bar_w, 0.26,
            boxstyle="square,pad=0", facecolor="#EEEEEE",
            edgecolor="#AAAAAA", linewidth=0.8, zorder=2))
        ax.add_patch(mpatches.FancyBboxPatch((1.0, bar_y-0.13), fill_w, 0.26,
            boxstyle="square,pad=0", facecolor=fc, edgecolor="none", zorder=3))
        if over_w > 0:
            ax.add_patch(mpatches.FancyBboxPatch((1.0+fill_w, bar_y-0.13), over_w, 0.26,
                boxstyle="square,pad=0", facecolor="#FF6600", edgecolor="none", zorder=3))
        ax.axvline(x=1.0+bar_w, color="#FF6600", lw=1.5, ls="--", zorder=4)
        ax.text(4.0, bar_y-0.35, f"{delay}ms / {max_delay_ms}ms max",
            ha="center", va="top", fontsize=7.5, color=color)
    elif delay == 0:
        ax.text(4.0, 0.5, "Note: Run pipeline again to get actual timing data",
            ha="center", va="center", fontsize=7, color="#999999", style="italic")


def render_from_pipeline_json(json_path: str, output_dir="outputs/diagrams"):
    """Main function: reads JSON and generates all diagrams."""
    print(f"\n[DiagramRenderer] Loading: {json_path}")
    with open(json_path) as f:
        data = json.load(f)

    agent_out   = data.get("agent_output", {})
    scenarios   = agent_out.get("scenarios", [])
    max_delay   = agent_out.get("max_delay_ms", 100)
    event       = agent_out.get("event", "brake").title()
    event_chain = agent_out.get("event_chain", [])
    requirement = data.get("requirement", "SDV Safety Requirement")

    if not scenarios:
        print("  No scenarios found in JSON.")
        return []

    if not event_chain:
        event_chain = ["Sense", "Detect", "Decide", "Actuate"]

    print(f"  Found {len(scenarios)} scenarios")
    print(f"  Event chain: {event_chain}")
    print(f"  Max delay: {max_delay}ms")

    # Debug: show what data we have
    for i, s in enumerate(scenarios):
        delay, risk, violation, road, severity, _, _, stype = extract_scenario_fields(s)
        print(f"  Scenario {i+1}: type={stype} delay={delay}ms risk={risk} violation={violation} road={road}")

    os.makedirs(output_dir, exist_ok=True)
    saved = []

    # Individual diagrams
    for i, s in enumerate(scenarios):
        _, _, _, _, _, _, _, stype = extract_scenario_fields(s)
        fig, ax = plt.subplots(figsize=(6, max(9, len(event_chain)*1.6+5)))
        fig.patch.set_facecolor(C_BG)
        fig.suptitle(f"SDV {event} Safety Analysis\n\"{requirement[:65]}\"",
                     fontsize=9, color="#333333", y=0.99)
        draw_dynamic_scenario(ax, s, event_chain, max_delay)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        path = os.path.join(output_dir, f"scenario_{stype}_{i+1}.png")
        plt.savefig(path, dpi=160, bbox_inches="tight", facecolor=C_BG)
        plt.close()
        print(f"  [PNG] Saved: {path}")
        saved.append(path)

    # Combined diagram
    n = len(scenarios)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols*6, rows*(max(9, len(event_chain)*1.6+5))))
    fig.patch.set_facecolor(C_BG)
    fig.suptitle(f"SDV {event} Safety Analysis — All Scenarios\n\"{requirement[:80]}\"",
                 fontsize=11, fontweight="bold", y=0.99)
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
    for i, s in enumerate(scenarios):
        draw_dynamic_scenario(axes_flat[i], s, event_chain, max_delay)
    for j in range(len(scenarios), len(axes_flat)):
        axes_flat[j].set_visible(False)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    combined = os.path.join(output_dir, "all_scenarios_combined.png")
    plt.savefig(combined, dpi=150, bbox_inches="tight", facecolor=C_BG)
    plt.close()
    print(f"  [PNG] Saved combined: {combined}")
    saved.append(combined)

    # Summary bar chart
    fig, ax = plt.subplots(figsize=(max(8, n*1.5), 5))
    fig.patch.set_facecolor(C_BG)
    labels, delays, risks, colors_bar = [], [], [], []
    for i, s in enumerate(scenarios):
        delay, risk, violation, road, severity, _, _, stype = extract_scenario_fields(s)
        labels.append(f"{stype.upper()} #{i+1}\nroad={road}")
        delays.append(delay)
        risks.append(risk)
        colors_bar.append("#CC0000" if violation else "#006633")

    bars = ax.bar(labels, delays, color=colors_bar, edgecolor="#333",
                  linewidth=1.2, width=0.5, zorder=3)
    ax.axhline(y=max_delay, color="#FF6600", linestyle="--", linewidth=2,
               label=f"ISO 26262 Max: {max_delay}ms", zorder=4)

    for bar, d, r, s in zip(bars, delays, risks, scenarios):
        _, _, violation, _, _, _, _, _ = extract_scenario_fields(s)
        v = "VIOLATION" if violation else "PASS"
        ax.text(bar.get_x()+bar.get_width()/2, d+1.5,
                f"{d}ms\nrisk={round(r,2)}\n{v}",
                ha="center", va="bottom", fontsize=7.5,
                color="#CC0000" if violation else "#006633", fontweight="bold")

    ax.set_title(f"SDV {event} — Scenario Delay Summary\n{requirement[:70]}",
                 fontsize=11, fontweight="bold")
    ax.set_ylabel("Actual Delay (ms)", fontsize=10)
    ax.set_ylim(0, max(delays+[max_delay])*1.4 if any(d>0 for d in delays) else max_delay*1.5)
    ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=9)
    ax.spines[["top","right"]].set_visible(False)
    plt.tight_layout()
    summary = os.path.join(output_dir, "scenario_summary_chart.png")
    plt.savefig(summary, dpi=160, bbox_inches="tight", facecolor=C_BG)
    plt.close()
    print(f"  [PNG] Saved summary: {summary}")
    saved.append(summary)

    return saved


def find_latest_json(folder="outputs"):
    files = glob.glob(os.path.join(folder, "requirement_pipeline_*.json"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        json_path = find_latest_json()
        if not json_path:
            print("No pipeline output JSON found in outputs/ folder.")
            print("Run: python main_pipeline.py first")
            sys.exit(1)
        print(f"Using latest output: {json_path}")

    saved = render_from_pipeline_json(json_path)
    print(f"\nDone! {len(saved)} diagram(s) saved to outputs/diagrams/")
    for p in saved:
        print(f"   {p}")