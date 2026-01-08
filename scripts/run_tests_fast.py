"""Fast test runner with progress indicators and timeout enforcement"""

import sys
import subprocess
import time
from pathlib import Path

def run_tests():
    """Run tests with progress indicators"""
    project_root = Path(__file__).parent.parent
    
    print("="*70)
    print("Running Tests with 45s SLA per test")
    print("="*70)
    print()
    
    # Run pytest with progress and timeout
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--timeout=45",
        "--timeout-method=thread",
        "--durations=10",
        "--no-cov",  # Skip coverage for speed
        "-x",  # Stop on first failure for quick feedback
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print()
    print("Starting tests...")
    print("-"*70)
    
    start_time = time.time()
    
    try:
        # Run with real-time output
        process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        for line in process.stdout:
            print(line, end='', flush=True)
        
        process.wait()
        exit_code = process.returncode
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Tests cancelled by user")
        exit_code = 130
    except Exception as e:
        print(f"\n[ERROR] Failed to run tests: {e}")
        exit_code = 1
    
    elapsed = time.time() - start_time
    
    print()
    print("-"*70)
    print(f"Tests completed in {elapsed:.2f} seconds")
    
    if exit_code == 0:
        print("[SUCCESS] All tests passed!")
    else:
        print(f"[FAILED] Tests failed with exit code {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(run_tests())

