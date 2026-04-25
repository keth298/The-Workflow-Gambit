"""
Report Generator — produces the final HTML report, summary CSV and JSON.

Uses Jinja2 for the HTML template and Plotly for interactive charts.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, BaseLoader

from evaluator.metrics import AggregatedData, EngineMetrics


# ------------------------------------------------------------------ #
#  HTML Template                                                       #
# ------------------------------------------------------------------ #

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Chess Engine Evaluation Report</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           margin: 0; padding: 0; background: #f8f9fa; color: #212529; }
    .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
    h1 { color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: .5rem; }
    h2 { color: #16213e; margin-top: 2.5rem; border-left: 4px solid #e94560;
         padding-left: .75rem; }
    h3 { color: #0f3460; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem; margin: 1.5rem 0; }
    .card { background: white; border-radius: 8px; padding: 1.25rem;
            box-shadow: 0 2px 8px rgba(0,0,0,.08); }
    .card .label { font-size: .8rem; color: #6c757d; text-transform: uppercase;
                   letter-spacing: .05em; }
    .card .value { font-size: 2rem; font-weight: 700; color: #1a1a2e; margin-top: .25rem; }
    .card .sub { font-size: .85rem; color: #6c757d; }
    table { width: 100%; border-collapse: collapse; background: white;
            border-radius: 8px; overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,.08); margin: 1rem 0; }
    th { background: #1a1a2e; color: white; padding: .75rem 1rem; text-align: left;
         font-weight: 600; font-size: .875rem; }
    td { padding: .625rem 1rem; border-bottom: 1px solid #f0f0f0; font-size: .875rem; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #f8f9fa; }
    .rank-1 td:first-child { color: #f59e0b; font-weight: 700; }
    .rank-2 td:first-child { color: #6b7280; font-weight: 700; }
    .rank-3 td:first-child { color: #92400e; font-weight: 700; }
    .chart-box { background: white; border-radius: 8px;
                 box-shadow: 0 2px 8px rgba(0,0,0,.08);
                 padding: 1rem; margin: 1rem 0; }
    .meta { color: #6c757d; font-size: .85rem; margin-top: 3rem;
            border-top: 1px solid #dee2e6; padding-top: 1rem; }
    .badge { display: inline-block; padding: .2rem .6rem; border-radius: 9999px;
             font-size: .75rem; font-weight: 600; }
    .badge-green { background: #d1fae5; color: #065f46; }
    .badge-yellow { background: #fef3c7; color: #92400e; }
    .badge-red { background: #fee2e2; color: #991b1b; }
  </style>
</head>
<body>
<div class="container">
  <h1>&#9823; Chess Engine Evaluation Report</h1>
  <p style="color:#6c757d">Generated {{ generated_at }} &nbsp;|&nbsp; {{ n_engines }} engines evaluated</p>

  <h2>Executive Summary</h2>
  <div class="summary-grid">
    <div class="card">
      <div class="label">Engines Evaluated</div>
      <div class="value">{{ n_engines }}</div>
    </div>
    <div class="card">
      <div class="label">Overall Winner</div>
      <div class="value" style="font-size:1.2rem">{{ overall_winner }}</div>
      <div class="sub">by overall score</div>
    </div>
    <div class="card">
      <div class="label">Strongest Engine</div>
      <div class="value" style="font-size:1.2rem">{{ strength_winner }}</div>
      <div class="sub">by raw chess strength</div>
    </div>
    <div class="card">
      <div class="label">Most Reliable</div>
      <div class="value" style="font-size:1.2rem">{{ reliability_winner }}</div>
      <div class="sub">by reliability score</div>
    </div>
    <div class="card">
      <div class="label">Most Efficient</div>
      <div class="value" style="font-size:1.2rem">{{ efficiency_winner }}</div>
      <div class="sub">strength per cost / time</div>
    </div>
    <div class="card">
      <div class="label">Most Creative</div>
      <div class="value" style="font-size:1.2rem">{{ creativity_winner }}</div>
      <div class="sub">by creativity rubric</div>
    </div>
  </div>

  <h2>Overall Leaderboard</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Engine</th>
      <th>Overall</th><th>Strength</th><th>Reliability</th>
      <th>Efficiency</th><th>Creativity</th>
    </tr></thead>
    <tbody>
    {% for e in engines_sorted_overall %}
    <tr class="{{ 'rank-' ~ loop.index if loop.index <= 3 else '' }}">
      <td>{{ loop.index }}</td>
      <td><strong>{{ e.engine_name or e.engine_id }}</strong></td>
      <td>{{ "%.3f"|format(e.overall_score) }}</td>
      <td>{{ "%.3f"|format(e.raw_strength_score) }}</td>
      <td>{{ "%.3f"|format(e.reliability_score) }}</td>
      <td>{{ "%.3f"|format(e.engineering_efficiency_score) }}</td>
      <td>{{ "%.3f"|format(e.creativity_score) }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Raw Strength Leaderboard</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Engine</th>
      <th>RR Points</th><th>W/D/L</th>
      <th>Stockfish Score %</th><th>Tactical Accuracy %</th>
    </tr></thead>
    <tbody>
    {% for e in engines_sorted_strength %}
    <tr class="{{ 'rank-' ~ loop.index if loop.index <= 3 else '' }}">
      <td>{{ loop.index }}</td>
      <td><strong>{{ e.engine_name or e.engine_id }}</strong></td>
      <td>{{ "%.1f"|format(e.rr_points) }}</td>
      <td>{{ e.rr_wins }}/{{ e.rr_draws }}/{{ e.rr_losses }}</td>
      <td>{{ "%.1f"|format(e.stockfish_score_pct) }}%</td>
      <td>{{ "%.1f"|format(e.tactical_accuracy_pct) }}%</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Reliability Leaderboard</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Engine</th>
      <th>Score</th><th>Illegal Moves</th><th>Crashes</th>
      <th>Timeouts</th><th>Games Played</th>
    </tr></thead>
    <tbody>
    {% for e in engines_sorted_reliability %}
    <tr class="{{ 'rank-' ~ loop.index if loop.index <= 3 else '' }}">
      <td>{{ loop.index }}</td>
      <td><strong>{{ e.engine_name or e.engine_id }}</strong></td>
      <td>{{ "%.3f"|format(e.reliability_score) }}</td>
      <td>{{ e.illegal_moves }}</td>
      <td>{{ e.crashes }}</td>
      <td>{{ e.timeouts }}</td>
      <td>{{ e.games_played }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Chess Quality Analysis</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Engine</th>
      <th>Avg CP Loss</th><th>Blunder Rate %</th><th>Best Move Agreement %</th>
    </tr></thead>
    <tbody>
    {% for e in engines_sorted_quality %}
    <tr class="{{ 'rank-' ~ loop.index if loop.index <= 3 else '' }}">
      <td>{{ loop.index }}</td>
      <td><strong>{{ e.engine_name or e.engine_id }}</strong></td>
      <td>{{ "%.1f"|format(e.avg_cp_loss) }}</td>
      <td>{{ "%.1f"|format(e.blunder_rate_pct) }}%</td>
      <td>{{ "%.1f"|format(e.best_move_agreement_pct) }}%</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Cost and Human Involvement</h2>
  <table>
    <thead><tr>
      <th>Engine</th>
      <th>Cost (USD)</th><th>Human Time (min)</th>
      <th>Prompts</th><th>Corrections</th>
      <th>Tokens In</th><th>Tokens Out</th>
    </tr></thead>
    <tbody>
    {% for e in engines_sorted_overall %}
    <tr>
      <td><strong>{{ e.engine_name or e.engine_id }}</strong></td>
      <td>{{ "$%.2f"|format(e.estimated_cost_usd) if e.estimated_cost_usd else "—" }}</td>
      <td>{{ e.human_time_minutes if e.human_time_minutes else "—" }}</td>
      <td>{{ e.prompt_count if e.prompt_count else "—" }}</td>
      <td>{{ e.human_correction_count if e.human_correction_count else "—" }}</td>
      <td>{{ "{:,}".format(e.input_tokens) if e.input_tokens else "—" }}</td>
      <td>{{ "{:,}".format(e.output_tokens) if e.output_tokens else "—" }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Engineering Metrics</h2>
  <table>
    <thead><tr>
      <th>Engine</th>
      <th>LOC</th><th>Tests</th><th>Test Pass Rate</th>
      <th>Doc Words</th><th>Frustration</th><th>Multitaskability</th>
    </tr></thead>
    <tbody>
    {% for e in engines_sorted_overall %}
    <tr>
      <td><strong>{{ e.engine_name or e.engine_id }}</strong></td>
      <td>{{ e.loc if e.loc else "—" }}</td>
      <td>{{ e.test_count if e.test_count else "—" }}</td>
      <td>{{ "%.0f%%"|format(e.test_pass_rate) if e.test_pass_rate else "—" }}</td>
      <td>{{ e.doc_word_count if e.doc_word_count else "—" }}</td>
      <td>{{ e.frustration_score ~ "/5" if e.frustration_score else "—" }}</td>
      <td>{{ e.multitaskability_score ~ "/5" if e.multitaskability_score else "—" }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Creativity Scores</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Engine</th>
      <th>Overall</th><th>Novelty</th><th>Strategic</th>
      <th>Workflow</th><th>Risk</th><th>Coherence</th>
    </tr></thead>
    <tbody>
    {% for e in engines_sorted_creativity %}
    <tr class="{{ 'rank-' ~ loop.index if loop.index <= 3 else '' }}">
      <td>{{ loop.index }}</td>
      <td><strong>{{ e.engine_name or e.engine_id }}</strong></td>
      <td>{{ "%.2f"|format(e.creativity_score) }}</td>
      <td>{{ "%.1f"|format(e.novelty) }}/5</td>
      <td>{{ "%.1f"|format(e.strategic_originality) }}/5</td>
      <td>{{ "%.1f"|format(e.agent_workflow_originality) }}/5</td>
      <td>{{ "%.1f"|format(e.risk_taking) }}/5</td>
      <td>{{ "%.1f"|format(e.coherence) }}/5</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <!-- Plotly charts -->
  <h2>Visualizations</h2>

  <div class="chart-box">
    <h3>Overall Scores by Engine</h3>
    <div id="chart-overall"></div>
  </div>

  <div class="chart-box">
    <h3>Strength vs. Estimated Cost</h3>
    <div id="chart-strength-cost"></div>
  </div>

  <div class="chart-box">
    <h3>Strength vs. Human Time</h3>
    <div id="chart-strength-time"></div>
  </div>

  <div class="chart-box">
    <h3>Tactical Accuracy vs. Avg Centipawn Loss</h3>
    <div id="chart-quality"></div>
  </div>

  <script>
  var engines = {{ engine_ids_json }};
  var overall = {{ overall_scores_json }};
  var strength = {{ strength_scores_json }};
  var reliability = {{ reliability_scores_json }};
  var efficiency = {{ efficiency_scores_json }};
  var creativity = {{ creativity_scores_json }};
  var cost = {{ costs_json }};
  var humanTime = {{ human_times_json }};
  var tacticalAcc = {{ tactical_acc_json }};
  var cpLoss = {{ cp_loss_json }};

  Plotly.newPlot('chart-overall', [
    {type: 'bar', x: engines, y: overall, name: 'Overall', marker:{color:'#e94560'}},
    {type: 'bar', x: engines, y: strength, name: 'Raw Strength', marker:{color:'#0f3460'}},
    {type: 'bar', x: engines, y: reliability, name: 'Reliability', marker:{color:'#16213e'}},
  ], {barmode:'group', margin:{t:20}, legend:{orientation:'h'}});

  Plotly.newPlot('chart-strength-cost', [{
    type: 'scatter', mode: 'markers+text',
    x: cost, y: strength,
    text: engines, textposition: 'top center',
    marker: {size:12, color:'#0f3460'}
  }], {
    xaxis:{title:'Estimated Cost (USD)'},
    yaxis:{title:'Raw Strength Score'},
    margin:{t:20}
  });

  Plotly.newPlot('chart-strength-time', [{
    type: 'scatter', mode: 'markers+text',
    x: humanTime, y: strength,
    text: engines, textposition: 'top center',
    marker: {size:12, color:'#e94560'}
  }], {
    xaxis:{title:'Human Time (minutes)'},
    yaxis:{title:'Raw Strength Score'},
    margin:{t:20}
  });

  Plotly.newPlot('chart-quality', [{
    type: 'scatter', mode: 'markers+text',
    x: cpLoss, y: tacticalAcc,
    text: engines, textposition: 'top center',
    marker: {size:12, color:'#16213e'}
  }], {
    xaxis:{title:'Avg Centipawn Loss (lower = better)'},
    yaxis:{title:'Tactical Accuracy %'},
    margin:{t:20}
  });
  </script>

  <div class="meta">
    Chess Engine Evaluation Framework &nbsp;|&nbsp;
    Report generated {{ generated_at }}
  </div>
</div>
</body>
</html>
"""


# ------------------------------------------------------------------ #
#  Report generator                                                    #
# ------------------------------------------------------------------ #

class ReportGenerator:
    """
    Generates the final HTML report plus CSV and JSON summaries.
    """

    def __init__(self, data: AggregatedData, output_path: str):
        self.data = data
        self.output_path = Path(output_path)

    def generate(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        engines = self.data.engines
        if not engines:
            print("No engine data found; report will be empty.")
            engines = []

        def sorted_by(attr: str) -> List[EngineMetrics]:
            return sorted(engines, key=lambda e: getattr(e, attr), reverse=True)

        def winner(attr: str) -> str:
            if not engines:
                return "—"
            best = max(engines, key=lambda e: getattr(e, attr))
            return best.engine_name or best.engine_id

        def to_json(lst) -> str:
            return json.dumps(lst)

        ctx = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "n_engines": len(engines),
            "overall_winner": winner("overall_score"),
            "strength_winner": winner("raw_strength_score"),
            "reliability_winner": winner("reliability_score"),
            "efficiency_winner": winner("engineering_efficiency_score"),
            "creativity_winner": winner("creativity_score"),
            "engines_sorted_overall": sorted_by("overall_score"),
            "engines_sorted_strength": sorted_by("raw_strength_score"),
            "engines_sorted_reliability": sorted_by("reliability_score"),
            "engines_sorted_quality": sorted_by("best_move_agreement_pct"),
            "engines_sorted_creativity": sorted_by("creativity_score"),
            # Chart data
            "engine_ids_json": to_json([e.engine_id for e in sorted_by("overall_score")]),
            "overall_scores_json": to_json(
                [round(e.overall_score, 4) for e in sorted_by("overall_score")]
            ),
            "strength_scores_json": to_json(
                [round(e.raw_strength_score, 4) for e in sorted_by("overall_score")]
            ),
            "reliability_scores_json": to_json(
                [round(e.reliability_score, 4) for e in sorted_by("overall_score")]
            ),
            "efficiency_scores_json": to_json(
                [round(e.engineering_efficiency_score, 4) for e in sorted_by("overall_score")]
            ),
            "creativity_scores_json": to_json(
                [round(e.creativity_score, 4) for e in sorted_by("overall_score")]
            ),
            "costs_json": to_json(
                [round(e.estimated_cost_usd, 2) for e in sorted_by("overall_score")]
            ),
            "human_times_json": to_json(
                [e.human_time_minutes for e in sorted_by("overall_score")]
            ),
            "tactical_acc_json": to_json(
                [round(e.tactical_accuracy_pct, 2) for e in sorted_by("overall_score")]
            ),
            "cp_loss_json": to_json(
                [round(e.avg_cp_loss, 2) for e in sorted_by("overall_score")]
            ),
        }

        env = Environment(loader=BaseLoader())
        tmpl = env.from_string(REPORT_TEMPLATE)
        html = tmpl.render(**ctx)

        with open(self.output_path, "w") as f:
            f.write(html)
        print(f"HTML report → {self.output_path}")

        self._write_csv(sorted_by("overall_score"))
        self._write_json(sorted_by("overall_score"))

    def _write_csv(self, engines: List[EngineMetrics]) -> None:
        csv_path = self.output_path.with_suffix(".csv")
        if not engines:
            return
        fieldnames = list(asdict(engines[0]).keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for e in engines:
                writer.writerow(asdict(e))
        print(f"CSV summary  → {csv_path}")

    def _write_json(self, engines: List[EngineMetrics]) -> None:
        json_path = self.output_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump([asdict(e) for e in engines], f, indent=2)
        print(f"JSON summary → {json_path}")
