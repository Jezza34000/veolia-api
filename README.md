<p align=center>
    <img src="https://upload.wikimedia.org/wikipedia/fi/thumb/2/2a/Veolia-logo.svg/250px-Veolia-logo.svg.png"/>
</p>

<p align=center>
    <a href="https://pypi.org/project/veolia-api/"><img src="https://img.shields.io/pypi/v/veolia-api.svg"/></a>
    <a href="https://github.com/Jezza34000/veolia-api/actions"><img src="https://github.com/Jezza34000/veolia-api/workflows/CI/badge.svg"/></a>
    <a href="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white"/></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg"/></a>
    <a href="https://github.com/Jezza34000/veolia-api/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg"/></a>
</p>

Async Python client for the Veolia water portal API (`eau.veolia.fr` and compatible portals).

## Table of contents

- [Installation](#installation)
- [Usage](#usage)
- [Supported portals](#supported-portals)
- [Contributing](#contributing)
- [Credits](#credits)
- [License](#license)

## Installation

```bash
pip install veolia-api
```

For a development environment, install [devbox](https://www.jetify.com/docs/devbox/installing-devbox) then run:

```bash
devbox shell
```

## Usage

```python
import asyncio
from datetime import date

import aiohttp

from veolia_api import VeoliaAPI


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client_api = VeoliaAPI("your@email.com", "password", session)

        # Optional: specify a portal other than the default
        # client_api = VeoliaAPI("your@email.com", "password", session, portal_url="eaudetm.monespace.eau.veolia.fr")

        await client_api.fetch_all_data(date(2025, 1, 1), date(2025, 9, 1))

        print(client_api.account_data.daily_consumption)
        print(client_api.account_data.monthly_consumption)
        print(client_api.account_data.alert_settings.daily_enabled)


if __name__ == "__main__":
    asyncio.run(main())
```

A runnable example with logging is available in [`usage_example.py`](usage_example.py).

## Supported portals

| Portal | Region |
|--------|--------|
| `eau.veolia.fr` | France (national) |
| `eaudetm.monespace.eau.veolia.fr` | Eau de Toulouse Metropole |

Your portal is missing? See [Adding a portal](CONTRIBUTING.md#adding-a-portal) — it only requires editing one file.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on reporting bugs, suggesting features, and submitting pull requests.

## Credits

Inspired by the original work of [@CorentinGrard](https://github.com/CorentinGrard).

## License

MIT — see [LICENSE](LICENSE).
