#!/usr/bin/env python3
import sys
import os
import argparse

# Add current directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def run_cli():
    from brain.main import main
    main()

def run_ui():
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8888, reload=False)

def main():
    parser = argparse.ArgumentParser(description="Orcas: Multi-agent AI Orchestrator")
    parser.add_argument("mode", nargs="?", default="run", choices=["run", "ui", "version"],
                        help="Mode to run Orcas in (default: run)")
    
    args = parser.parse_args()

    if args.mode == "run":
        run_cli()
    elif args.mode == "ui":
        run_ui()
    elif args.mode == "version":
        print("Orcas v0.1.0 - Multi-agent AI Orchestrator")

if __name__ == "__main__":
    main()
