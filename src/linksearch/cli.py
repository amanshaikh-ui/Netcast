from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
from dotenv import load_dotenv

from linksearch.csv_io import read_products, write_results
from linksearch.pipeline import run_pipeline

load_dotenv()

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


@app.command()
def run(
    input_csv: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Input CSV with columns: Brand, SKU, Product Name (optional).",
    ),
    output_csv: Path = typer.Option(
        Path("output_links.csv"),
        "--output",
        "-o",
        help="Output CSV path (Media, Brand, URL, SKU, Product Name).",
    ),
    no_groq_rerank: bool = typer.Option(
        False,
        "--no-groq-rerank",
        help="Disable Groq relevance reranking (faster, fewer API calls).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    platforms: str | None = typer.Option(
        None,
        "--platforms",
        help=(
            "Comma-separated subset: Youtube, YoutubeShorts, Reddit, Tiktok, Facebook, Instagram. "
            "Omit for all platforms."
        ),
    ),
) -> None:
    """Discover social links for each product row."""
    _setup_logging(verbose)
    products = read_products(input_csv)
    plats: list[str] | None = None
    if platforms is not None and platforms.strip():
        plats = [x.strip() for x in platforms.split(",") if x.strip()]
    result = asyncio.run(
        run_pipeline(
            products,
            use_groq_rerank=not no_groq_rerank,
            platforms=plats,
        )
    )
    write_results(output_csv, result.rows)
    typer.echo(f"Wrote {len(result.rows)} rows to {output_csv}")
    for w in result.warnings:
        typer.echo(f"Note: {w}", err=True)
    if verbose and result.meta:
        import json

        typer.echo(json.dumps(result.meta, indent=2)[:8000])


if __name__ == "__main__":
    app()
