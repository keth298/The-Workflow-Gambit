"""
Chess Engine Evaluation Framework — CLI entry point.

Usage:
    python -m evaluator <command> [options]
"""

import click

from evaluator.engine_registry import EngineRegistry
from evaluator.round_robin import RoundRobin
from evaluator.double_elim import DoubleElimination
from evaluator.stockfish_eval import StockfishEvaluator
from evaluator.tactics_eval import TacticsEvaluator
from evaluator.blunder_eval import BlunderEvaluator
from evaluator.metrics import Metrics
from evaluator.report_generator import ReportGenerator


@click.group()
def cli():
    """Chess Engine Evaluation Framework."""


@cli.command("validate-engines")
@click.option("--config", default="configs/engines.yaml", show_default=True,
              help="Path to engines YAML config.")
def validate_engines(config: str):
    """Validate that all registered engines pass the UCI health check."""
    registry = EngineRegistry.from_yaml(config)
    all_ok = True
    for engine in registry.enabled_engines():
        click.echo(f"Checking {engine.engine_id} ... ", nl=False)
        ok, msg = engine.health_check()
        if ok:
            click.secho("OK", fg="green")
        else:
            click.secho(f"FAILED — {msg}", fg="red")
            all_ok = False
    if not all_ok:
        raise SystemExit(1)


@cli.command("run-round-robin")
@click.option("--config", default="configs/tournament.yaml", show_default=True,
              help="Path to tournament config.")
def run_round_robin(config: str):
    """Run a round-robin tournament among all enabled engines."""
    import yaml
    with open(config) as f:
        cfg = yaml.safe_load(f)
    registry = EngineRegistry.from_yaml(cfg["tournament"]["engines_config"])
    rr = RoundRobin.from_config(cfg["tournament"], registry)
    rr.run()
    click.secho("Round-robin complete.", fg="green")


@cli.command("run-double-elim")
@click.option("--config", default="configs/tournament.yaml", show_default=True,
              help="Path to tournament config.")
@click.option("--seed-from", default=None,
              help="Path to round-robin results JSON to seed bracket.")
def run_double_elim(config: str, seed_from: str):
    """Run a double-elimination tournament."""
    import yaml
    with open(config) as f:
        cfg = yaml.safe_load(f)
    registry = EngineRegistry.from_yaml(cfg["tournament"]["engines_config"])
    de = DoubleElimination.from_config(cfg["tournament"], registry,
                                       seed_results_path=seed_from)
    de.run()
    click.secho("Double-elimination complete.", fg="green")


@cli.command("eval-stockfish")
@click.option("--config", default="configs/tournament.yaml", show_default=True)
@click.option("--scoring", default="configs/scoring.yaml", show_default=True)
def eval_stockfish(config: str, scoring: str):
    """Benchmark all engines against Stockfish at multiple skill levels."""
    import yaml
    with open(config) as f:
        tcfg = yaml.safe_load(f)["tournament"]
    with open(scoring) as f:
        scfg = yaml.safe_load(f)
    registry = EngineRegistry.from_yaml(tcfg["engines_config"])
    ev = StockfishEvaluator(registry, tcfg, scfg)
    ev.run()
    click.secho("Stockfish evaluation complete.", fg="green")


@cli.command("eval-tactics")
@click.option("--config", default="configs/tournament.yaml", show_default=True)
@click.option("--dataset", default="datasets/tactics.yaml", show_default=True)
def eval_tactics(config: str, dataset: str):
    """Evaluate all engines on the tactical puzzle set."""
    import yaml
    with open(config) as f:
        tcfg = yaml.safe_load(f)["tournament"]
    registry = EngineRegistry.from_yaml(tcfg["engines_config"])
    ev = TacticsEvaluator(registry, dataset, results_dir=tcfg["results_dir"])
    ev.run()
    click.secho("Tactics evaluation complete.", fg="green")


@cli.command("eval-blunders")
@click.option("--config", default="configs/tournament.yaml", show_default=True)
@click.option("--dataset", default="datasets/curated_positions.yaml",
              show_default=True)
def eval_blunders(config: str, dataset: str):
    """Evaluate blunder rate from curated positions using Stockfish centipawn loss."""
    import yaml
    with open(config) as f:
        tcfg = yaml.safe_load(f)["tournament"]
    registry = EngineRegistry.from_yaml(tcfg["engines_config"])
    ev = BlunderEvaluator(registry, dataset, results_dir=tcfg["results_dir"])
    ev.run()
    click.secho("Blunder evaluation complete.", fg="green")


@cli.command("generate-report")
@click.option("--results", default="results/", show_default=True,
              help="Root results directory.")
@click.option("--scoring", default="configs/scoring.yaml", show_default=True)
@click.option("--out", default="results/reports/final_report.html",
              show_default=True)
def generate_report(results: str, scoring: str, out: str):
    """Aggregate all results and generate the final HTML + CSV report."""
    import yaml
    with open(scoring) as f:
        scfg = yaml.safe_load(f)
    metrics = Metrics(results_dir=results, scoring_config=scfg)
    data = metrics.aggregate()
    rg = ReportGenerator(data, output_path=out)
    rg.generate()
    click.secho(f"Report written to {out}", fg="green")


@cli.command("run-full-eval")
@click.option("--config", default="configs/tournament.yaml", show_default=True)
@click.option("--scoring", default="configs/scoring.yaml", show_default=True)
@click.option("--tactics-dataset", default="datasets/tactics.yaml",
              show_default=True)
@click.option("--blunder-dataset", default="datasets/curated_positions.yaml",
              show_default=True)
@click.pass_context
def run_full_eval(ctx, config, scoring, tactics_dataset, blunder_dataset):
    """Run the complete evaluation pipeline end to end."""
    import yaml
    with open(config) as f:
        tcfg = yaml.safe_load(f)["tournament"]
    ctx.invoke(validate_engines, config=tcfg["engines_config"])
    ctx.invoke(run_round_robin, config=config)
    rr_results = f"{tcfg['results_dir']}tournaments/round_robin_main.json"
    ctx.invoke(run_double_elim, config=config, seed_from=rr_results)
    ctx.invoke(eval_stockfish, config=config, scoring=scoring)
    ctx.invoke(eval_tactics, config=config, dataset=tactics_dataset)
    ctx.invoke(eval_blunders, config=config, dataset=blunder_dataset)
    ctx.invoke(generate_report, results=tcfg["results_dir"],
               scoring=scoring,
               out=f"{tcfg['results_dir']}reports/final_report.html")


if __name__ == "__main__":
    cli()
