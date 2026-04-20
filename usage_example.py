"""Example of usage of the Veolia API with logging"""

import asyncio
import logging
from datetime import date

import aiohttp

from veolia_api.veolia_api import VeoliaAPI

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("VeoliaExample")


async def main() -> None:
    """Main function with logging."""
    logger.info("Starting Veolia API example script")

    async with aiohttp.ClientSession() as session:
        logger.debug("Creating VeoliaAPI client")
        client_api = VeoliaAPI("email", "password", session)

        start_date = date(2025, 1, 1)
        end_date = date(2025, 9, 1)

        logger.info(f"Fetching data from {start_date} to {end_date}")

        try:
            await client_api.fetch_all_data(start_date, end_date)
            logger.info("Data fetch completed successfully")
        except Exception as e:
            logger.exception("Error while fetching data")
            return
    # Log consumption data
    logger.info(
        f"Daily consumption count: {len(client_api.account_data.daily_consumption)}"
    )
    logger.info(
        f"Monthly consumption count: {len(client_api.account_data.monthly_consumption)}"
    )
    logger.info(
        f"Daily alert enabled: {client_api.account_data.alert_settings.daily_enabled}"
    )
    logger.info("OK")


if __name__ == "__main__":
    asyncio.run(main())
