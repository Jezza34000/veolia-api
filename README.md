<p align=center>
    <img src="https://upload.wikimedia.org/wikipedia/fi/thumb/2/2a/Veolia-logo.svg/250px-Veolia-logo.svg.png"/>
</p>

<p>
    <a href="https://pypi.org/project/veolia-api/"><img src="https://img.shields.io/pypi/v/veolia-api.svg"/></a>
    <a href="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" /></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" /></a>
    <a href="https://github.com/Jezza34000/veolia-api/actions"><img src="https://github.com/Jezza34000/veolia-api/workflows/CI/badge.svg"/></a>
</p>

Python wrapper for using Veolia API : https://www.eau.veolia.fr/

## Installation

First of all, you need to install [devbox](https://www.jetify.com/docs/devbox/installing-devbox) **if you don't have a python environment**

Once the previous step is done, simply run

```bash
devbox shell
```

That's it !

If you already have a python environment just run

```bash
pip install veolia-api
```

## Usage

```python
"""Example of usage of the Veolia API"""

import asyncio
from datetime import date

import aiohttp

from veolia_api.veolia_api import VeoliaAPI


async def main() -> None:
    """Main function."""

    async with aiohttp.ClientSession() as session:
        client_api = VeoliaAPI("email", "password", session)

        # e.g Fetch data from 2025-1 to 2025-9
        await client_api.fetch_all_data(date(2025, 1, 1), date(2025, 9, 1))

        # Display fetched data
        print(client_api.account_data.daily_consumption)
        print(client_api.account_data.monthly_consumption)
        print(client_api.account_data.alert_settings.daily_enabled)


if __name__ == "__main__":
    asyncio.run(main())

```

You can use usage_example.py

```bash
cp usage_example.py.dist usage_example.py
python usage_example.py
```

## Credits

This repository is inspired by the work done by @CorentinGrard. Thanks to him for his work.
