"""Example of usage of the Veolia API with logging"""

import asyncio
import logging
import os
import sys
from datetime import date

import aiohttp
from dotenv import load_dotenv

from veolia_api.veolia_api import VeoliaAPI

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("VeoliaExample")


async def main() -> None:
    """Main function with logging."""
    load_dotenv()

    email = os.getenv("VEOLIA_EMAIL", "")
    password = os.getenv("VEOLIA_PASSWORD", "")

    if not email or not password:
        logger.error("VEOLIA_EMAIL and VEOLIA_PASSWORD must be set in .env file")
        logger.error("Copy .env.example to .env and fill in your credentials")
        sys.exit(1)

    logger.info("Starting Veolia API example script")

    async with aiohttp.ClientSession() as session:
        logger.debug("Creating VeoliaAPI client")
        client_api = VeoliaAPI(email, password, session)

        start_date = date(2025, 1, 1)
        end_date = date(2025, 9, 1)

        logger.info("Fetching data from %s to %s", start_date, end_date)

        try:
            await client_api.fetch_all_data(start_date, end_date)
            logger.info("Data fetch completed successfully")
        except Exception:
            logger.exception("Error while fetching data")
            return

    logger.info(
        "Daily consumption count: %d", len(client_api.account_data.daily_consumption)
    )
    logger.info(
        "Monthly consumption count: %d",
        len(client_api.account_data.monthly_consumption),
    )
    logger.info(
        "Daily alert enabled: %s", client_api.account_data.alert_settings.daily_enabled
    )
    logger.info("OK")


if __name__ == "__main__":
    asyncio.run(main())
