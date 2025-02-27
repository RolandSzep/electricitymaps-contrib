import logging
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from requests import Session
from requests_mock import ANY, GET, Adapter
from snapshottest import TestCase

from electricitymap.contrib.lib.types import ZoneKey
from parsers import ENTSOE

base_path_to_mock = Path("parsers/test/mocks/ENTSOE")


class TestENTSOE(TestCase):
    def setUp(self) -> None:
        super().setUp()
        os.environ["ENTSOE_TOKEN"] = "token"
        self.session = Session()
        self.adapter = Adapter()
        self.session.mount("https://", self.adapter)


class TestFetchConsumption(TestENTSOE):
    def test_fetch_consumption(self):
        data = Path(base_path_to_mock, "DK-DK1_consumption.xml")
        self.adapter.register_uri(
            GET,
            ANY,
            content=data.read_bytes(),
        )

        consumption = ENTSOE.fetch_consumption(ZoneKey("DK-DK1"), self.session)

        self.assertMatchSnapshot(
            [
                {
                    "datetime": element["datetime"].isoformat(),
                    "consumption": element["consumption"],
                    "source": element["source"],
                    "zoneKey": element["zoneKey"],
                    "sourceType": element["sourceType"].value,
                }
                for element in consumption
            ]
        )


class TestFetchConsumptionForecast(TestENTSOE):
    def test_fetch_consumption_forecast(self):
        data = Path(base_path_to_mock, "DK-DK2_consumption_forecast.xml")
        self.adapter.register_uri(
            GET,
            ANY,
            content=data.read_bytes(),
        )

        consumption_forecast = ENTSOE.fetch_consumption_forecast(
            ZoneKey("DK-DK2"), self.session
        )

        self.assertMatchSnapshot(
            [
                {
                    "datetime": element["datetime"].isoformat(),
                    "consumption": element["consumption"],
                    "source": element["source"],
                    "zoneKey": element["zoneKey"],
                    "sourceType": element["sourceType"].value,
                }
                for element in consumption_forecast
            ]
        )


class TestFetchGenerationForecast(TestENTSOE):
    def test_fetch_generation_forecast(self):
        data = Path(base_path_to_mock, "SE-SE3_generation_forecast.xml")
        self.adapter.register_uri(
            GET,
            ANY,
            content=data.read_bytes(),
        )

        generation_forecast = ENTSOE.fetch_generation_forecast(
            ZoneKey("SE-SE3"), self.session
        )

        self.assertMatchSnapshot(
            [
                {
                    "datetime": element["datetime"].isoformat(),
                    "generation": element["generation"],
                    "source": element["source"],
                    "zoneKey": element["zoneKey"],
                    "sourceType": element["sourceType"].value,
                }
                for element in generation_forecast
            ]
        )


class TestFetchPrices(TestENTSOE):
    def test_fetch_prices(self):
        with open("parsers/test/mocks/ENTSOE/FR_prices.xml", "rb") as price_fr_data:
            self.adapter.register_uri(
                GET,
                ANY,
                content=price_fr_data.read(),
            )
            prices = ENTSOE.fetch_price(ZoneKey("FR"), self.session)
            self.assertEqual(len(prices), 48)
            self.assertEqual(prices[0]["price"], 106.78)
            self.assertEqual(prices[0]["source"], "entsoe.eu")
            self.assertEqual(prices[0]["currency"], "EUR")
            self.assertEqual(
                prices[0]["datetime"], datetime(2023, 5, 6, 22, 0, tzinfo=timezone.utc)
            )

    def test_fetch_prices_integrated_zone(self):
        with open("parsers/test/mocks/ENTSOE/FR_prices.xml", "rb") as price_fr_data:
            self.adapter.register_uri(
                GET,
                ANY,
                content=price_fr_data.read(),
            )
            prices = ENTSOE.fetch_price(ZoneKey("DK-BHM"), self.session)
            self.assertEqual(len(prices), 48)
            self.assertEqual(prices[0]["price"], 106.78)
            self.assertEqual(prices[0]["source"], "entsoe.eu")
            self.assertEqual(prices[0]["currency"], "EUR")
            self.assertEqual(
                prices[0]["datetime"], datetime(2023, 5, 6, 22, 0, tzinfo=timezone.utc)
            )


class TestFetchProduction(TestENTSOE):
    def test_fetch_production(self):
        with open(
            "parsers/test/mocks/ENTSOE/FI_production.xml", "rb"
        ) as production_fi_data:
            self.adapter.register_uri(
                GET,
                ANY,
                content=production_fi_data.read(),
            )
            production = ENTSOE.fetch_production(ZoneKey("FI"), self.session)
            self.assertEqual(len(production), 48)
            self.assertEqual(production[0]["zoneKey"], "FI")
            self.assertEqual(production[0]["source"], "entsoe.eu")
            self.assertEqual(
                production[0]["datetime"],
                datetime(2023, 5, 8, 7, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(production[0]["production"]["biomass"], 543 + 7)
            self.assertEqual(production[0]["production"]["coal"], 154 + 180)
            self.assertEqual(production[0]["production"]["gas"], 254)
            self.assertEqual(production[0]["production"]["hydro"], 2360)
            self.assertEqual(production[0]["production"]["nuclear"], 3466)
            self.assertEqual(production[0]["production"]["oil"], 51)
            self.assertEqual(production[0]["production"]["wind"], 750)
            self.assertEqual(production[0]["production"]["unknown"], 51 + 3)

            self.assertEqual(production[1]["source"], "entsoe.eu")
            self.assertEqual(
                production[1]["datetime"],
                datetime(2023, 5, 8, 8, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(production[1]["production"]["biomass"], 558 + 7)
            self.assertEqual(production[1]["production"]["coal"], 155 + 158)
            self.assertEqual(production[1]["production"]["gas"], 263)
            self.assertEqual(production[1]["production"]["hydro"], 2319)
            self.assertEqual(production[1]["production"]["nuclear"], 3466)
            self.assertEqual(production[1]["production"]["oil"], 0)
            self.assertEqual(production[1]["production"]["wind"], 915)
            self.assertEqual(production[1]["production"]["unknown"], 46 + 3)

            self.assertEqual(production[-1]["source"], "entsoe.eu")
            self.assertEqual(
                production[-1]["datetime"],
                datetime(2023, 5, 10, 6, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(production[-1]["production"]["biomass"], 515 + 20)
            self.assertEqual(production[-1]["production"]["coal"], 111 + 124)
            self.assertEqual(production[-1]["production"]["gas"], 198)

    def test_fetch_production_with_storage(self):
        with open(
            "parsers/test/mocks/ENTSOE/NO-NO5_production.xml", "rb"
        ) as production_no_data:
            self.adapter.register_uri(
                GET,
                ANY,
                content=production_no_data.read(),
            )
            production = ENTSOE.fetch_production(ZoneKey("NO-NO5"), self.session)
            self.assertEqual(len(production), 47)
            self.assertEqual(production[0]["zoneKey"], "NO-NO5")
            self.assertEqual(production[0]["source"], "entsoe.eu")
            self.assertEqual(
                production[0]["datetime"],
                datetime(2023, 5, 9, 9, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(production[0]["storage"]["hydro"], -61)
            self.assertEqual(production[0]["production"]["gas"], 0)
            self.assertEqual(production[0]["production"]["hydro"], 1065)

    def test_fetch_with_negative_values(self):
        with open(
            "parsers/test/mocks/ENTSOE/NO-NO5_production-negatives.xml", "rb"
        ) as production_no_data:
            self.adapter.register_uri(
                GET,
                ANY,
                content=production_no_data.read(),
            )
            logger = logging.Logger("test")
            with patch.object(logger, "info") as mock_warning:
                production = ENTSOE.fetch_production(
                    ZoneKey("NO-NO5"), self.session, logger=logger
                )
                self.assertEqual(len(production), 47)
                self.assertEqual(production[0]["zoneKey"], "NO-NO5")
                self.assertEqual(production[0]["source"], "entsoe.eu")
                self.assertEqual(
                    production[0]["datetime"],
                    datetime(2023, 5, 9, 9, 0, tzinfo=timezone.utc),
                )
                # Small negative values have been set to 0.
                self.assertEqual(production[0]["production"]["gas"], 0)
                self.assertEqual(production[1]["production"]["gas"], 0)

                # Large negative values have been set to None.
                self.assertEqual(
                    production[-1]["datetime"],
                    datetime(2023, 5, 11, 7, 0, tzinfo=timezone.utc),
                )
                self.assertEqual(production[-1]["production"]["gas"], None)
                # A warning has been logged for this.
                mock_warning.assert_called()


class TestFetchExchange(TestENTSOE):
    def test_fetch_exchange(self):
        imports = Path(base_path_to_mock, "DK-DK1_GB_exchange_imports.xml")
        exports = Path(base_path_to_mock, "DK-DK1_GB_exchange_exports.xml")

        self.adapter.register_uri(
            GET,
            "?documentType=A11&in_Domain=10YDK-1--------W&out_Domain=10YGB----------A",
            content=imports.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A11&in_Domain=10YGB----------A&out_Domain=10YDK-1--------W",
            content=exports.read_bytes(),
        )
        exchange = ENTSOE.fetch_exchange(
            zone_key1=ZoneKey("DK-DK1"), zone_key2=ZoneKey("GB"), session=self.session
        )
        exchange.sort(key=lambda x: x["datetime"])
        self.assertMatchSnapshot(
            [
                {
                    "datetime": element["datetime"].isoformat(),
                    "netFlow": element["netFlow"],
                    "source": element["source"],
                    "sortedZoneKeys": element["sortedZoneKeys"],
                    "sourceType": element["sourceType"].value,
                }
                for element in exchange
            ]
        )

    def test_fetch_exchange_with_aggregated_exchanges(self):
        imports_AC = Path(base_path_to_mock, "FR-COR_IT-SAR_AC_exchange_imports.xml")
        exports_AC = Path(base_path_to_mock, "FR-COR_IT-SAR_AC_exchange_exports.xml")
        imports_DC = Path(base_path_to_mock, "FR-COR_IT-SAR_DC_exchange_imports.xml")
        exports_DC = Path(base_path_to_mock, "FR-COR_IT-SAR_DC_exchange_exports.xml")

        self.adapter.register_uri(
            GET,
            "?documentType=A11&in_Domain=10Y1001A1001A885&out_Domain=10Y1001A1001A74G",
            content=imports_AC.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A11&in_Domain=10Y1001A1001A74G&out_Domain=10Y1001A1001A885",
            content=exports_AC.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A11&in_Domain=10Y1001A1001A893&out_Domain=10Y1001A1001A74G",
            content=imports_DC.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A11&in_Domain=10Y1001A1001A74G&out_Domain=10Y1001A1001A893",
            content=exports_DC.read_bytes(),
        )

        exchange = ENTSOE.fetch_exchange(
            zone_key1=ZoneKey("FR-COR"),
            zone_key2=ZoneKey("IT-SAR"),
            session=self.session,
        )

        self.assert_match_snapshot(
            [
                {
                    "datetime": element["datetime"].isoformat(),
                    "netFlow": element["netFlow"],
                    "source": element["source"],
                    "sortedZoneKeys": element["sortedZoneKeys"],
                    "sourceType": element["sourceType"].value,
                }
                for element in exchange
            ]
        )


class TestFetchExchangeForecast(TestENTSOE):
    def test_fetch_exchange_forecast(self):
        imports = Path(base_path_to_mock, "DK-DK2_SE-SE4_exchange_forecast_imports.xml")
        exports = Path(base_path_to_mock, "DK-DK2_SE-SE4_exchange_forecast_exports.xml")

        self.adapter.register_uri(
            GET,
            "?documentType=A09&in_Domain=10YDK-2--------M&out_Domain=10Y1001A1001A47J",
            content=imports.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A09&in_Domain=10Y1001A1001A47J&out_Domain=10YDK-2--------M",
            content=exports.read_bytes(),
        )
        exchange_forecast = ENTSOE.fetch_exchange_forecast(
            zone_key1=ZoneKey("DK-DK2"),
            zone_key2=ZoneKey("SE-SE4"),
            session=self.session,
        )
        exchange_forecast.sort(key=lambda x: x["datetime"])
        self.assertMatchSnapshot(
            [
                {
                    "datetime": element["datetime"].isoformat(),
                    "netFlow": element["netFlow"],
                    "source": element["source"],
                    "sortedZoneKeys": element["sortedZoneKeys"],
                    "sourceType": element["sourceType"].value,
                }
                for element in exchange_forecast
            ]
        )

    def test_fetch_exchange_forecast_with_aggregated_exchanges(self):
        imports_AC = Path(
            base_path_to_mock, "FR-COR_IT-SAR_AC_exchange_forecast_imports.xml"
        )
        exports_AC = Path(
            base_path_to_mock, "FR-COR_IT-SAR_AC_exchange_forecast_exports.xml"
        )
        imports_DC = Path(
            base_path_to_mock, "FR-COR_IT-SAR_DC_exchange_forecast_imports.xml"
        )
        exports_DC = Path(
            base_path_to_mock, "FR-COR_IT-SAR_DC_exchange_forecast_exports.xml"
        )

        self.adapter.register_uri(
            GET,
            "?documentType=A09&in_Domain=10Y1001A1001A885&out_Domain=10Y1001A1001A74G",
            content=imports_AC.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A09&in_Domain=10Y1001A1001A74G&out_Domain=10Y1001A1001A885",
            content=exports_AC.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A09&in_Domain=10Y1001A1001A893&out_Domain=10Y1001A1001A74G",
            content=imports_DC.read_bytes(),
        )
        self.adapter.register_uri(
            GET,
            "?documentType=A09&in_Domain=10Y1001A1001A74G&out_Domain=10Y1001A1001A893",
            content=exports_DC.read_bytes(),
        )

        exchange_forecast = ENTSOE.fetch_exchange_forecast(
            zone_key1=ZoneKey("FR-COR"),
            zone_key2=ZoneKey("IT-SAR"),
            session=self.session,
        )

        self.assert_match_snapshot(
            [
                {
                    "datetime": element["datetime"].isoformat(),
                    "netFlow": element["netFlow"],
                    "source": element["source"],
                    "sortedZoneKeys": element["sortedZoneKeys"],
                    "sourceType": element["sourceType"].value,
                }
                for element in exchange_forecast
            ]
        )


class TestENTSOE_Refetch(unittest.TestCase):
    def test_fetch_uses_normal_url(self):
        os.environ["ENTSOE_TOKEN"] = "proxy"
        self.session = Session()
        self.adapter = Adapter()
        self.session.mount("https://", self.adapter)
        with open("parsers/test/mocks/ENTSOE/FR_prices.xml", "rb") as price_fr_data:
            self.adapter.register_uri(
                GET,
                ENTSOE.ENTSOE_URL,
                content=price_fr_data.read(),
            )
            _ = ENTSOE.fetch_price(ZoneKey("DE"), self.session)
