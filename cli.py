"""Unified `weather` command: fetch fresh data, then show the dashboard.

Installed by pip/pipx (see pyproject.toml). The individual steps stay
available as separate commands: weather-fetch, weather-dashboard,
weather-notify.

Usage:
    weather                  # fetch (config.py/default location), then display
    weather --city "Cairo"   # fetch for a city name, then display
"""

import argparse
import sys

import dashboard
import weather


def main():
    parser = argparse.ArgumentParser(
        prog="weather",
        description="Fetch the forecast and display the weather dashboard.",
    )
    parser.add_argument(
        "--city",
        help="City name to forecast (e.g. --city 'Cairo'). "
        "Overrides config.py coordinates.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        choices=range(1, 17),
        metavar="1-16",
        help="Forecast days to fetch (default: 7).",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip fetching; just display the existing data.json.",
    )
    args = parser.parse_args()

    if not args.no_fetch:
        fetch_args = []
        if args.city:
            fetch_args += ["--city", args.city]
        fetch_args += ["--days", str(args.days)]
        if not weather.main(fetch_args):
            sys.exit(1)

    dashboard.main()


if __name__ == "__main__":
    main()
