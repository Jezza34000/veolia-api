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
