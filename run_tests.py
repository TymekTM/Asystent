"""Skrypt do uruchamiania testów GAJA Assistant."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_tests(
    test_type="all", verbose=False, coverage=False, parallel=False, markers=None
):
    """Uruchom testy zgodnie z podanymi parametrami.

    Args:
        test_type (str): Typ testów do uruchomienia (all, unit, integration, performance, audio)
        verbose (bool): Czy pokazywać szczegółowe informacje
        coverage (bool): Czy generować raport pokrycia
        parallel (bool): Czy uruchamiać testy równolegle
        markers (str): Dodatkowe markery pytest
    """

    # Przejdź do katalogu głównego projektu
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Podstawowe argumenty pytest
    pytest_args = ["pytest", "tests_pytest/"]

    # Dodaj poziom szczegółowości
    if verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")

    # Dodaj pokrycie kodu
    if coverage:
        pytest_args.extend(
            [
                "--cov=server",
                "--cov=client",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing",
                "--cov-report=xml",
            ]
        )

    # Dodaj równoległe wykonywanie
    if parallel:
        pytest_args.extend(["-n", "auto"])

    # Wybierz typ testów
    if test_type == "unit":
        pytest_args.extend(["-m", "unit"])
    elif test_type == "integration":
        pytest_args.extend(["-m", "integration"])
    elif test_type == "performance":
        pytest_args.extend(["-m", "performance"])
    elif test_type == "audio":
        pytest_args.extend(["-m", "audio"])
    elif test_type == "server":
        pytest_args.extend(["-m", "server"])
    elif test_type == "client":
        pytest_args.extend(["-m", "client"])
    elif test_type == "fast":
        pytest_args.extend(["-m", "not slow"])
    elif test_type == "slow":
        pytest_args.extend(["-m", "slow"])

    # Dodaj dodatkowe markery
    if markers:
        pytest_args.extend(["-m", markers])

    # Dodaj inne przydatne opcje
    pytest_args.extend(["--tb=short", "--strict-markers", "--color=yes"])

    print(f"Uruchamianie testów: {' '.join(pytest_args)}")
    print("-" * 50)

    # Uruchom pytest
    try:
        result = subprocess.run(pytest_args, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Testy zakończone z błędem: {e.returncode}")
        return e.returncode


def install_test_dependencies():
    """Zainstaluj zależności testowe."""
    print("Instalowanie zależności testowych...")

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements_test.txt"],
            check=True,
        )
        print("✓ Zależności testowe zainstalowane")
        return True
    except subprocess.CalledProcessError:
        print("✗ Błąd instalacji zależności testowych")
        return False


def generate_test_report():
    """Wygeneruj raport testów."""
    print("Generowanie raportu testów...")

    pytest_args = [
        "pytest",
        "tests_pytest/",
        "--html=test_report.html",
        "--self-contained-html",
        "--json-report",
        "--json-report-file=test_report.json",
    ]

    try:
        subprocess.run(pytest_args, check=True)
        print("✓ Raport testów wygenerowany:")
        print("  - HTML: test_report.html")
        print("  - JSON: test_report.json")
        return True
    except subprocess.CalledProcessError:
        print("✗ Błąd generowania raportu")
        return False


def run_specific_test_file(test_file, verbose=False):
    """Uruchom konkretny plik testowy."""
    test_path = Path("tests_pytest") / test_file

    if not test_path.exists():
        print(f"✗ Plik testowy nie istnieje: {test_path}")
        return 1

    pytest_args = ["pytest", str(test_path)]

    if verbose:
        pytest_args.append("-v")

    pytest_args.extend(["--tb=short", "--color=yes"])

    print(f"Uruchamianie: {test_file}")
    print("-" * 30)

    try:
        result = subprocess.run(pytest_args, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode


def run_test_discovery():
    """Pokaż dostępne testy."""
    print("Odkrywanie dostępnych testów...")

    pytest_args = ["pytest", "tests_pytest/", "--collect-only", "-q"]

    try:
        subprocess.run(pytest_args, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def check_test_environment():
    """Sprawdź środowisko testowe."""
    print("Sprawdzanie środowiska testowego...")

    # Sprawdź czy pytest jest zainstalowany
    try:
        import pytest

        print(f"✓ pytest {pytest.__version__}")
    except ImportError:
        print("✗ pytest nie jest zainstalowany")
        return False

    # Sprawdź czy wymagane moduły są dostępne
    required_modules = ["asyncio", "json", "unittest.mock", "pathlib"]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            missing_modules.append(module)
            print(f"✗ {module}")

    if missing_modules:
        print(f"Brakujące moduły: {', '.join(missing_modules)}")
        return False

    # Sprawdź strukturę testów
    test_dir = Path("tests_pytest")
    if not test_dir.exists():
        print(f"✗ Katalog testów nie istnieje: {test_dir}")
        return False

    test_files = list(test_dir.glob("test_*.py"))
    print(f"✓ Znaleziono {len(test_files)} plików testowych")

    return True


def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Uruchom testy GAJA Assistant")

    parser.add_argument(
        "command",
        choices=["run", "install", "report", "discover", "check", "file"],
        help="Komenda do wykonania",
    )

    parser.add_argument(
        "--type",
        "-t",
        choices=[
            "all",
            "unit",
            "integration",
            "performance",
            "audio",
            "server",
            "client",
            "fast",
            "slow",
        ],
        default="all",
        help="Typ testów do uruchomienia",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Pokaż szczegółowe informacje"
    )

    parser.add_argument(
        "--coverage", "-c", action="store_true", help="Generuj raport pokrycia kodu"
    )

    parser.add_argument(
        "--parallel", "-p", action="store_true", help="Uruchom testy równolegle"
    )

    parser.add_argument("--markers", "-m", help="Dodatkowe markery pytest")

    parser.add_argument("--file", "-f", help="Konkretny plik testowy do uruchomienia")

    args = parser.parse_args()

    if args.command == "check":
        success = check_test_environment()
        return 0 if success else 1

    elif args.command == "install":
        success = install_test_dependencies()
        return 0 if success else 1

    elif args.command == "discover":
        success = run_test_discovery()
        return 0 if success else 1

    elif args.command == "report":
        success = generate_test_report()
        return 0 if success else 1

    elif args.command == "file":
        if not args.file:
            print("✗ Musisz podać nazwę pliku z opcją --file")
            return 1
        return run_specific_test_file(args.file, args.verbose)

    elif args.command == "run":
        return run_tests(
            test_type=args.type,
            verbose=args.verbose,
            coverage=args.coverage,
            parallel=args.parallel,
            markers=args.markers,
        )

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
