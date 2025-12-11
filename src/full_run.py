#!/usr/bin/env python3

import subprocess
import sys
import argparse
from pathlib import Path
import time


CITY_SCRIPTS = [
    ("Chicago", "chicago.py"),
    ("Los Angeles", "los_angeles.py"),
    ("Memphis", "memphis.py"),
    ("Portland", "portland.py"),
    ("Washington DC", "washington.py"),
]

COMBINER_SCRIPT = "data_combiner.py"
DASHBOARD_SCRIPT = "dashboard.py"


def run_script(script_name: str, city_name: str = None) -> bool:
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"Script not found: {script_name}")
        return False
    
    display_name = city_name if city_name else script_name
    print(f"\n{'='*60}")
    print(f"Running: {display_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=script_path.parent,
            check=False
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n{display_name} completed successfully ({elapsed:.1f}s)")
            return True
        else:
            print(f"\n{display_name} failed with exit code {result.returncode} ({elapsed:.1f}s)")
            return False
            
    except Exception as e:
        print(f"\nError running {display_name}: {e}")
        return False


def run_cities(selected_cities: list = None) -> dict:
    results = {}
    
    for city_name, script_name in CITY_SCRIPTS:
        script_base = script_name.replace('.py', '')
        if selected_cities and script_base not in selected_cities:
            continue
            
        success = run_script(script_name, city_name)
        results[city_name] = success
    
    return results


def run_combiner() -> bool:
    return run_script(COMBINER_SCRIPT, "Data Combiner")


def run_dashboard() -> None:
    script_path = Path(__file__).parent / DASHBOARD_SCRIPT
    
    if not script_path.exists():
        print(f"Dashboard script not found: {DASHBOARD_SCRIPT}")
        return
    
    print(f"\n{'='*60}")
    print("Launching: Streamlit Dashboard")
    print(f"{'='*60}")
    print("\n🚀 Starting dashboard... (Press Ctrl+C to stop)\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(script_path)],
            cwd=script_path.parent,
            check=False
        )
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
    except Exception as e:
        print(f"\nError running dashboard: {e}")


def print_summary(city_results: dict, combiner_result: bool = None):
    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print(f"{'='*60}")
    
    if city_results:
        print("\nCity Extractions:")
        for city, success in city_results.items():
            status = "Success" if success else "Failed"
            print(f"  {city}: {status}")
        
        successful = sum(1 for s in city_results.values() if s)
        total = len(city_results)
        print(f"\n  Total: {successful}/{total} cities completed successfully")
    
    if combiner_result is not None:
        print("\nData Combiner:")
        status = "Success" if combiner_result else "Failed"
        print(f"  {status}")
    
    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Run crime data extraction pipeline for all cities"
    )
    parser.add_argument(
        "--cities", "-c",
        action="store_true",
        help="Run only city extractions (skip combiner)"
    )
    parser.add_argument(
        "--combine", "-C",
        action="store_true",
        help="Run only the data combiner (skip city extractions)"
    )
    parser.add_argument(
        "--city",
        nargs="+",
        metavar="NAME",
        help="Run specific cities only (e.g., --city chicago los_angeles)"
    )
    parser.add_argument(
        "--no-dashboard", "-n",
        action="store_true",
        help="Skip launching the Streamlit dashboard at the end"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'#'*60}")
    print("#  CRIME DATA EXTRACTION PIPELINE")
    print(f"{'#'*60}")
    
    start_time = time.time()
    city_results = {}
    combiner_result = None
    
    run_city_extractions = not args.combine
    run_data_combiner = not args.cities
    
    if run_city_extractions:
        city_results = run_cities(args.city)
    
    if run_data_combiner:
        combiner_result = run_combiner()
    
    print_summary(city_results, combiner_result)
    
    total_time = time.time() - start_time
    print(f"Total pipeline time: {total_time:.1f}s")
    
    all_successful = all(city_results.values()) if city_results else True
    combiner_successful = combiner_result if combiner_result is not None else True
    
    if not (all_successful and combiner_successful):
        sys.exit(1)
    
    if not args.no_dashboard:
        run_dashboard()


if __name__ == "__main__":
    main()
