import argparse
import json
from .checks import check


def main():
    parser = argparse.ArgumentParser(description="Check supported Gaussian Splatting asset profiles")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    reports = [check(path) for path in args.files]
    if args.format == "json":
        print(json.dumps({"schema_version": 1, "results": reports}, indent=2))
    else:
        for r in reports:
            print(f"{r['status'].upper()}: {r['file']}")
            for f in r["findings"]:
                print(f"  {f['code']}: {f['message']}")
    return 0 if all(r["status"] == "pass" for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
