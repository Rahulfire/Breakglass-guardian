#!/usr/bin/env python3
"""
BreakGlass Guardian - Test Runner
Executes all security tests and generates report
"""
import subprocess
import sys
from datetime import datetime


def print_header(title):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def run_test_suite(name, test_file):
    """Run a test suite and return results"""
    print(f"Running {name}...")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"✅ {name} PASSED")
            return True
        else:
            print(f"❌ {name} FAILED")
            print(result.stdout)
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {name} TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {name} ERROR: {e}")
        return False


def main():
    """Run all security tests"""
    print_header("BREAKGLASS GUARDIAN - SECURITY TEST SUITE")
    print(f"Test Run: {datetime.utcnow().isoformat()}")
    
    test_suites = [
        ("Prompt Injection Defense", "backend/tests/test_prompt_injection.py"),
        ("Approval Validation", "backend/tests/test_approval_validation.py"),
    ]
    
    results = {}
    
    for name, test_file in test_suites:
        print_header(name)
        results[name] = run_test_suite(name, test_file)
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for r in results.values() if r)
    failed = len(results) - passed
    
    print(f"Total Test Suites: {len(results)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print()
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print("\n" + "="*70 + "\n")
    
    if failed > 0:
        print("⚠️  SECURITY TESTS FAILED - DO NOT DEPLOY")
        sys.exit(1)
    else:
        print("✅ ALL SECURITY TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
