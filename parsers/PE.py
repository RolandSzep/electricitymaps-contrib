#!/usr/bin/env python3

from datetime import datetime
from logging import Logger, getLogger

import arrow
import dateutil
from requests import Session

from .lib.validation import validate

tz = "America/Lima"

MAP_GENERATION = {
    "DIESEL": "oil",
    "RESIDUAL": "biomass",
    "CARBÓN": "coal",
    "GAS": "gas",
    "HÍDRICO": "hydro",
    "BIOGÁS": "unknown",
    "BAGAZO": "biomass",
    "SOLAR": "solar",
    "EÓLICA": "wind",
}


def parse_date(item):
    return arrow.get(item["Nombre"], "YYYY/MM/DD hh:mm:ss").replace(
        tzinfo=dateutil.tz.gettz(tz)
    )


def fetch_production(
    zone_key: str = "PE",
    session: Session | None = None,
    target_datetime: datetime | None = None,
    logger: Logger = getLogger(__name__),
) -> list:
    """Requests the last known production mix (in MW) of a given country."""
    if target_datetime:
        raise NotImplementedError("This parser is not yet able to parse past dates")

    r = session or Session()
    url = "https://www.coes.org.pe/Portal/portalinformacion/generacion"

    current_date = arrow.now(tz=tz)

    today = current_date.format("DD/MM/YYYY")
    yesterday = current_date.shift(days=-1).format("DD/MM/YYYY")
    end_date = current_date.shift(days=+1).format("DD/MM/YYYY")

    # To guarantee a full 24 hours of data we must make 2 requests.

    response_today = r.post(
        url, data={"fechaInicial": today, "fechaFinal": end_date, "indicador": 0}
    )

    response_yesterday = r.post(
        url, data={"fechaInicial": yesterday, "fechaFinal": today, "indicador": 0}
    )

    data_today = response_today.json()["GraficoTipoCombustible"]["Series"]
    data_yesterday = response_yesterday.json()["GraficoTipoCombustible"]["Series"]
    raw_data = data_today + data_yesterday

    # Note: We receive MWh values between two intervals!
    interval_hours = (
        parse_date(raw_data[0]["Data"][1]) - parse_date(raw_data[0]["Data"][0])
    ).total_seconds() / 3600

    data = []
    datetimes = []

    for series in raw_data:
        k = series["Name"]
        if k not in MAP_GENERATION:
            logger.warning(f'Unknown production type "{k}" for Peru')
            continue
        for v in series["Data"]:
            dt = parse_date(v)
            try:
                i = datetimes.index(dt)
            except ValueError:
                i = len(datetimes)
                datetimes.append(dt)
                data.append(
                    {
                        "zoneKey": zone_key,
                        "datetime": dt.datetime,
                        "production": {},
                        "source": "coes.org.pe",
                    }
                )

            data[i]["production"][MAP_GENERATION[k]] = (
                data[i]["production"].get(MAP_GENERATION[k], 0)
                + v["Valor"] / interval_hours
            )

    # Drop last datapoints if it "looks" incomplete.
    # The last hour often only contains data from some power plants
    # which results in the last datapoint being significantly lower than expected.
    # This is a hacky check, but since we are only potentially discarding the last hour
    # it will be included when the next datapoint comes in anyway.
    # We only run this check when target_datetime is None, as to not affect refetches
    # TODO: remove this in the future, when this is automatically detected by QA layer
    data = sorted(data, key=lambda d: d["datetime"])
    total_production_per_datapoint = [sum(d["production"].values()) for d in data]
    mean_production = sum(total_production_per_datapoint) / len(
        total_production_per_datapoint
    )
    if (
        total_production_per_datapoint[-1] < mean_production * 0.9
        and target_datetime is None
    ):
        logger.warning(
            "Dropping last datapoint as it is probably incomplete. Total production is less than 90% of the mean."
        )
        data = data[:-1]

    return list(
        filter(
            lambda x: validate(
                x,
                logger,
                required=["gas"],
                expected_range={
                    "gas": (100, 6000),
                },
                floor=0.0,
            )
            is not None,
            data,
        )
    )


if __name__ == "__main__":
    print(fetch_production())
