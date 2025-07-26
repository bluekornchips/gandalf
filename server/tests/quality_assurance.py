"""Quality assurance script for running all quality gates in Phase 4."""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class QualityGateRunner:
    """Runs all quality assurance gates for the refactored codebase."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.tests_path = project_root / "tests"
        self.results: dict[str, Any] = {}

    def run_all_gates(self) -> dict[str, Any]:
        """Execute all quality gates and return comprehensive results."""
        print("Starting Phase 4 Quality Assurance Gates...")
        print("=" * 60)

        start_time = time.time()

        # Gate 1: Test Coverage and Pass Rate
        print("\n1. Running Test Coverage and Pass Rate Gate...")
        test_results = self._run_test_gate()
        self.results["tests"] = test_results

        # Gate 2: Linting and Code Style
        print("\n2. Running Linting and Code Style Gate...")
        linting_results = self._run_linting_gate()
        self.results["linting"] = linting_results

        # Gate 3: Type Checking
        print("\n3. Running Type Checking Gate...")
        type_results = self._run_type_checking_gate()
        self.results["type_checking"] = type_results

        # Gate 4: Security Scanning
        print("\n4. Running Security Scanning Gate...")
        security_results = self._run_security_gate()
        self.results["security"] = security_results

        # Gate 5: Documentation Coverage
        print("\n5. Running Documentation Coverage Gate...")
        docs_results = self._run_documentation_gate()
        self.results["documentation"] = docs_results

        # Gate 6: Performance Validation
        print("\n6. Running Performance Validation Gate...")
        performance_results = self._run_performance_gate()
        self.results["performance"] = performance_results

        total_time = time.time() - start_time
        self.results["total_execution_time"] = total_time

        # Generate summary report
        summary = self._generate_summary()
        self.results["summary"] = summary

        print("\n" + "=" * 60)
        print("Quality Assurance Gates Complete")
        print(f"Total execution time: {total_time:.2f} seconds")
        print("=" * 60)

        return self.results

    def _run_test_gate(self) -> dict[str, Any]:
        """Run test coverage and pass rate gate."""
        results = {
            "pass_rate": {"passed": False, "details": ""},
            "coverage": {"passed": False, "details": ""},
            "execution_time": 0,
        }

        start_time = time.time()

        try:
            # Run tests with coverage
            print("  Running pytest with coverage...")
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(self.tests_path),
                f"--cov={self.src_path}",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json",
                "--cov-fail-under=90",
                "-x",
                "--tb=short",
                "-v",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            # Parse test results
            if result.returncode == 0:
                results["pass_rate"]["passed"] = True
                results["pass_rate"]["details"] = "All tests passed"
            else:
                results["pass_rate"]["details"] = f"Tests failed: {result.stderr[:500]}"

            # Parse coverage results
            try:
                with open(self.project_root / "coverage.json") as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data["totals"]["percent_covered"]

                    if total_coverage >= 90:
                        results["coverage"]["passed"] = True
                        results["coverage"]["details"] = (
                            f"Coverage: {total_coverage:.1f}% (≥90% required)"
                        )
                    else:
                        results["coverage"]["details"] = (
                            f"Coverage: {total_coverage:.1f}% (below 90% threshold)"
                        )

            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                results["coverage"]["details"] = "Could not parse coverage data"

        except subprocess.TimeoutExpired:
            results["pass_rate"]["details"] = "Tests timed out after 10 minutes"
        except Exception as e:
            results["pass_rate"]["details"] = f"Test execution error: {str(e)}"

        results["execution_time"] = time.time() - start_time
        return results

    def _run_linting_gate(self) -> dict[str, Any]:
        """Run linting and code style gate."""
        results = {"ruff_check": {"passed": False, "details": ""}, "execution_time": 0}

        start_time = time.time()

        try:
            print("  Running ruff check...")
            cmd = [
                sys.executable,
                "-m",
                "ruff",
                "check",
                str(self.src_path),
                "--no-fix",
            ]

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                results["ruff_check"]["passed"] = True
                results["ruff_check"]["details"] = "No linting errors found"
            else:
                results["ruff_check"]["details"] = (
                    f"Linting errors found:\n{result.stdout[:1000]}"
                )

        except subprocess.TimeoutExpired:
            results["ruff_check"]["details"] = "Linting check timed out"
        except Exception as e:
            results["ruff_check"]["details"] = f"Linting error: {str(e)}"

        results["execution_time"] = time.time() - start_time
        return results

    def _run_type_checking_gate(self) -> dict[str, Any]:
        """Run type checking gate."""
        results = {"mypy_check": {"passed": False, "details": ""}, "execution_time": 0}

        start_time = time.time()

        try:
            print("  Running mypy type checking...")
            cmd = [sys.executable, "-m", "mypy", str(self.src_path), "--strict"]

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=180
            )

            if result.returncode == 0:
                results["mypy_check"]["passed"] = True
                results["mypy_check"]["details"] = "No type checking errors found"
            else:
                results["mypy_check"]["details"] = (
                    f"Type errors found:\n{result.stdout[:1000]}"
                )

        except subprocess.TimeoutExpired:
            results["mypy_check"]["details"] = "Type checking timed out"
        except Exception as e:
            results["mypy_check"]["details"] = f"Type checking error: {str(e)}"

        results["execution_time"] = time.time() - start_time
        return results

    def _run_security_gate(self) -> dict[str, Any]:
        """Run security scanning gate."""
        results = {"bandit_scan": {"passed": False, "details": ""}, "execution_time": 0}

        start_time = time.time()

        try:
            print("  Running bandit security scan...")
            cmd = [
                sys.executable,
                "-m",
                "bandit",
                "-r",
                str(self.src_path),
                "-ll",  # Low confidence and low severity
                "-f",
                "json",
            ]

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=120
            )

            try:
                scan_data = json.loads(result.stdout)
                high_severity_issues = [
                    issue
                    for issue in scan_data.get("results", [])
                    if issue.get("issue_severity") in ["HIGH", "MEDIUM"]
                ]

                if len(high_severity_issues) == 0:
                    results["bandit_scan"]["passed"] = True
                    results["bandit_scan"]["details"] = (
                        "No high/medium severity security issues found"
                    )
                else:
                    results["bandit_scan"]["details"] = (
                        f"Found {len(high_severity_issues)} high/medium security issues"
                    )

            except json.JSONDecodeError:
                if result.returncode == 0:
                    results["bandit_scan"]["passed"] = True
                    results["bandit_scan"]["details"] = "No security issues found"
                else:
                    results["bandit_scan"]["details"] = (
                        "Security scan completed with warnings"
                    )

        except subprocess.TimeoutExpired:
            results["bandit_scan"]["details"] = "Security scan timed out"
        except Exception as e:
            results["bandit_scan"]["details"] = f"Security scan error: {str(e)}"

        results["execution_time"] = time.time() - start_time
        return results

    def _run_documentation_gate(self) -> dict[str, Any]:
        """Run documentation coverage gate."""
        results = {
            "docstring_coverage": {"passed": False, "details": ""},
            "execution_time": 0,
        }

        start_time = time.time()

        try:
            print("  Running documentation coverage check...")
            cmd = [
                sys.executable,
                "-m",
                "interrogate",
                str(self.src_path),
                "--fail-under=80",
                "--quiet",
            ]

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                results["docstring_coverage"]["passed"] = True
                results["docstring_coverage"]["details"] = "Documentation coverage ≥80%"
            else:
                # Parse output to get actual coverage
                output_lines = result.stdout.split("\n")
                coverage_line = next((line for line in output_lines if "%" in line), "")
                results["docstring_coverage"]["details"] = (
                    f"Documentation coverage below 80%: {coverage_line}"
                )

        except subprocess.TimeoutExpired:
            results["docstring_coverage"]["details"] = "Documentation check timed out"
        except Exception as e:
            # If interrogate is not available, do manual check
            results["docstring_coverage"]["details"] = (
                f"Manual docstring check needed: {str(e)}"
            )

            # Fallback: count functions with docstrings
            try:
                total_functions, documented_functions = (
                    self._count_documented_functions()
                )
                coverage_percent = (
                    (documented_functions / total_functions * 100)
                    if total_functions > 0
                    else 0
                )

                if coverage_percent >= 80:
                    results["docstring_coverage"]["passed"] = True
                    results["docstring_coverage"]["details"] = (
                        f"Manual check: {coverage_percent:.1f}% documented (≥80%)"
                    )
                else:
                    results["docstring_coverage"]["details"] = (
                        f"Manual check: {coverage_percent:.1f}% documented (below 80%)"
                    )

            except Exception as manual_error:
                results["docstring_coverage"]["details"] = (
                    f"Documentation check failed: {str(manual_error)}"
                )

        results["execution_time"] = time.time() - start_time
        return results

    def _run_performance_gate(self) -> dict[str, Any]:
        """Run performance validation gate."""
        results = {
            "performance_tests": {"passed": False, "details": ""},
            "execution_time": 0,
        }

        start_time = time.time()

        try:
            print("  Running performance tests...")
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(self.tests_path / "performance"),
                "-v",
                "--tb=short",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for performance tests
            )

            if result.returncode == 0:
                results["performance_tests"]["passed"] = True
                results["performance_tests"]["details"] = "All performance tests passed"
            else:
                results["performance_tests"]["details"] = (
                    f"Performance tests failed:\n{result.stdout[-500:]}"
                )

        except subprocess.TimeoutExpired:
            results["performance_tests"]["details"] = "Performance tests timed out"
        except Exception as e:
            results["performance_tests"]["details"] = (
                f"Performance test error: {str(e)}"
            )

        results["execution_time"] = time.time() - start_time
        return results

    def _count_documented_functions(self) -> tuple[int, int]:
        """Manually count functions with docstrings."""
        total_functions = 0
        documented_functions = 0

        for py_file in self.src_path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Simple regex-based counting (not perfect but functional)
                import re

                # Find function definitions
                func_pattern = r"^\s*def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\("
                functions = re.findall(func_pattern, content, re.MULTILINE)
                total_functions += len(functions)

                # Find functions with docstrings (simplified check)
                func_with_doc_pattern = (
                    r'^\s*def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\):[^"]*"""'
                )
                documented = re.findall(
                    func_with_doc_pattern, content, re.MULTILINE | re.DOTALL
                )
                documented_functions += len(documented)

            except Exception:
                continue

        return total_functions, documented_functions

    def _generate_summary(self) -> dict[str, Any]:
        """Generate summary of all quality gate results."""
        summary = {
            "overall_status": "PASSED",
            "total_gates": 0,
            "passed_gates": 0,
            "failed_gates": [],
            "gate_results": {},
        }

        # Analyze each gate category
        for category, category_results in self.results.items():
            if category in ["total_execution_time", "summary"]:
                continue

            category_passed = True
            gate_details = {}

            for gate_name, gate_result in category_results.items():
                if gate_name == "execution_time":
                    continue

                summary["total_gates"] += 1
                gate_details[gate_name] = {
                    "passed": gate_result.get("passed", False),
                    "details": gate_result.get("details", ""),
                }

                if gate_result.get("passed", False):
                    summary["passed_gates"] += 1
                else:
                    category_passed = False
                    summary["failed_gates"].append(f"{category}.{gate_name}")

            summary["gate_results"][category] = {
                "passed": category_passed,
                "gates": gate_details,
                "execution_time": category_results.get("execution_time", 0),
            }

        # Determine overall status
        if summary["passed_gates"] != summary["total_gates"]:
            summary["overall_status"] = "FAILED"

        return summary

    def print_summary_report(self) -> None:
        """Print a formatted summary report."""
        if "summary" not in self.results:
            print("No summary available")
            return

        summary = self.results["summary"]

        print("\n" + "=" * 60)
        print("QUALITY ASSURANCE SUMMARY REPORT")
        print("=" * 60)

        print(f"Overall Status: {summary['overall_status']}")
        print(f"Gates Passed: {summary['passed_gates']}/{summary['total_gates']}")
        print(
            f"Total Execution Time: {self.results.get('total_execution_time', 0):.2f} seconds"
        )

        if summary["failed_gates"]:
            print(f"\nFailed Gates: {', '.join(summary['failed_gates'])}")

        print("\nDetailed Results:")
        print("-" * 40)

        for category, category_data in summary["gate_results"].items():
            status_icon = "✓" if category_data["passed"] else "✗"
            print(
                f"{status_icon} {category.upper()} ({category_data['execution_time']:.1f}s)"
            )

            for gate_name, gate_data in category_data["gates"].items():
                gate_icon = "  ✓" if gate_data["passed"] else "  ✗"
                print(f"{gate_icon} {gate_name}: {gate_data['details'][:100]}")

        print("=" * 60)


def main():
    """Main entry point for quality assurance script."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Phase 4 Quality Assurance Gates")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to project root directory",
    )
    parser.add_argument("--output-json", type=Path, help="Path to save JSON results")
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first gate failure"
    )

    args = parser.parse_args()

    # Run quality gates
    runner = QualityGateRunner(args.project_root)
    results = runner.run_all_gates()

    # Print summary
    runner.print_summary_report()

    # Save JSON results if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {args.output_json}")

    # Exit with appropriate code
    overall_status = results.get("summary", {}).get("overall_status", "FAILED")
    sys.exit(0 if overall_status == "PASSED" else 1)


if __name__ == "__main__":
    main()
