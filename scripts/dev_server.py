"""Compatibility launcher. Uses the installed native Hermes CLI and its PluginContext."""
import subprocess
import sys

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "hermes_cli.main", "repager", *sys.argv[1:]]))
