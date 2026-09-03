try:
    from btm.cli import run_cli
except ImportError:  # running from a source checkout without installing
    from src.btm.cli import run_cli

if __name__ == "__main__":
    run_cli()
