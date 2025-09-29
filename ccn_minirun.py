"""CCN CLI entrypoint for running the minimal EPN cycle."""

import os
import sys
import json
import click
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.traceback import install

from llm_client import LLMClient, LLMError
from template_loader import repo as template_repo
from worker_node import WorkerNode
from mini_ccn import MiniCCN, CCNError
from jsonschema import validate, ValidationError


# Install rich traceback handler
install(show_locals=True)

console = Console()


def validate_environment() -> str:
    """Validate required environment variables and return the provider name.

    Returns:
        str: The provider name ('groq' or 'deepseek')
    """
    from llm_config import get_default_llm_config

    # Get provider from configuration (templates can override)
    config = get_default_llm_config()
    provider = config.get("provider", "groq")

    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            console.print("[red]Error: GROQ_API_KEY environment variable is required for Groq provider[/red]")
            sys.exit(1)
    elif provider == "deepseek":
        if not os.getenv("DEEPSEEK_API_KEY"):
            console.print("[red]Error: DEEPSEEK_API_KEY environment variable is required for DeepSeek provider[/red]")
            sys.exit(1)
    else:
        console.print(f"[red]Error: Unsupported provider '{provider}'. Supported: groq, deepseek[/red]")
        sys.exit(1)

    return provider


def validate_archive(archive_data: list, strict: bool = False) -> bool:
    """Validate archive against schema."""
    try:
        schema_path = os.path.join(os.path.dirname(__file__), 'schemas', 'memory_record.schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        for record in archive_data:
            validate(record, schema)
        
        return True
    except (ValidationError, FileNotFoundError) as e:
        if strict:
            raise
        console.print(f"[yellow]Warning: Archive validation failed: {e}[/yellow]")
        return False


@click.command()
@click.argument('query', required=True)
@click.option('--debug', '-d', is_flag=True,
              help='Enable debug mode with verbose output')
@click.option('--strict', '-s', is_flag=True,
              help='Enable strict mode (fail on validation errors)')
@click.option('--output', '-o', type=click.Path(),
              help='Output file for results')
@click.option('--validate-only', is_flag=True,
              help='Only validate setup without executing')
@click.option('--ccn-dispatch', is_flag=True,
              help='Dispatch built-in steps in CCN using call_plan')
def main(
    query: str,
    debug: bool,
    strict: bool,
    output: Optional[str],
    validate_only: bool,
    ccn_dispatch: bool,
) -> None:
    """Run the CCN minimal EPN cycle with the given query.
    
    QUERY: The input question or task to process through the CCN pipeline.
    
    Example:
        ccn_minirun "What are the key principles of machine learning?"
    """
    
    try:
        # Validate environment and get provider
        provider = validate_environment()

        # Initialize components
        console.print("[bold blue]Initializing CCN Minimal EPN Cycle[/bold blue]")

        # Test LLM connection
        console.print(f"Testing {provider.title()} API connection...")
        llm_client = LLMClient(provider_name=provider)
        if not llm_client.test_connection():
            console.print(f"[red]Failed to connect to {provider.title()} API[/red]")
            sys.exit(1)
        console.print(f"[green]✓ {provider.title()} API connection successful[/green]")
        
        # Initialize worker and CCN
        worker_node = WorkerNode(llm_client)
        ccn = MiniCCN(worker_node, debug=debug, dispatch_in_ccn=ccn_dispatch)
        
        if validate_only:
            console.print("[green]✓ Setup validation successful[/green]")
            return
        
        # Allow prompts.md to override the input query if present
        override_query = template_repo().get_initial_query()
        effective_query = override_query if override_query else query

        # Execute CCN cycle
        console.print(f"\n[bold]Processing query:[/bold] {effective_query}")
        console.print("=" * 50)
        
        try:
            result = ccn.execute(effective_query)
            
            # Display results
            console.print("\n[bold green]✓ Execution completed successfully[/bold green]")
            console.print("\n[bold]Final Synthesis:[/bold]")
            console.print(Panel(result, title="SYNTHESIZER Output", expand=False))
            
            # Show execution summary
            summary = ccn.get_execution_summary()
            metrics = ccn.get_metrics()
            console.print(f"\n[bold]Execution Summary:[/bold]")
            console.print(f"  Roles executed: {', '.join(summary['roles_executed'])}")
            console.print(f"  Archive records: {summary['archive_size']}")
            console.print(f"  Events logged: {summary['events_count']}")
            console.print(f"  Aggregator entries: {summary['aggregator_size']}")

            console.print("\n[bold]Metrics (JSON):[/bold]")
            console.print(json.dumps(metrics))

            console.print("\n[bold]Event Log (JSON lines):[/bold]")
            for event in ccn.memory.run_log:
                console.print(json.dumps(event.to_dict()))
            
            # Validate archive if strict mode
            if strict:
                archive_data = [record.to_dict() for record in ccn.memory.archive]
                if validate_archive(archive_data, strict=True):
                    console.print("[green]✓ Archive validation passed[/green]")
            
            # Save output if requested
            if output:
                output_data = {
                    'query': effective_query,
                    'result': result,
                    'summary': summary,
                    'archive': [record.to_dict() for record in ccn.memory.archive],
                    'events': [event.to_dict() for event in ccn.memory.run_log]
                }
                
                with open(output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                console.print(f"[green]✓ Results saved to {output}[/green]")
            
            # Debug output
            if debug:
                console.print(f"\n[bold yellow]Debug Information:[/bold yellow]")
                console.print("Archive Records:")
                for record in ccn.memory.archive:
                    console.print(JSON(json.dumps(record.to_dict(), indent=2)))
        
        except CCNError as e:
            console.print(f"[red]CCN Execution Error: {e}[/red]")
            if debug:
                console.print_exception()
            sys.exit(1)
        
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            if debug:
                console.print_exception()
            sys.exit(1)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Execution interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


if __name__ == '__main__':
    main()
