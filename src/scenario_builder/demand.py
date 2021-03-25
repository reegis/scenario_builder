"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""


import calendar
import logging
import os

import pandas as pd
from reegis import config as cfg
from reegis import demand_elec
from reegis import demand_heat


def get_heat_profiles_deflex(
    deflex_geo, year, time_index=None, weather_year=None, keep_unit=False
):
    """

    Parameters
    ----------
    year
    deflex_geo
    time_index
    weather_year
    keep_unit

    Returns
    -------

    """
    # separate_regions=keep all demand connected to the region
    separate_regions = cfg.get_list("creator", "separate_heat_regions")
    # Add lower and upper cases to be not case sensitive
    separate_regions = [x.upper() for x in separate_regions] + [
        x.lower() for x in separate_regions
    ]

    # add second fuel to first
    # combine_fuels = cfg.get_dict("combine_heat_fuels")
    combine_fuels = {"natural gas": "gas"}

    # fuels to be dissolved per region
    region_fuels = cfg.get_list("creator", "local_fuels")

    fn = os.path.join(
        cfg.get("paths", "demand"),
        "heat_profiles_{year}_{map}".format(year=year, map=deflex_geo.name),
    )

    demand_region = (
        demand_heat.get_heat_profiles_by_region(
            deflex_geo, year, to_csv=fn, weather_year=weather_year
        )
        .groupby(level=[0, 1], axis=1)
        .sum()
    )

    # Decentralised demand is combined to a nation-wide demand if not part
    # of region_fuels.
    regions = list(
        set(demand_region.columns.get_level_values(0).unique())
        - set(separate_regions)
    )

    # If region_fuels is 'all' fetch all fuels to be local.
    if "all" in region_fuels:
        region_fuels = demand_region.columns.get_level_values(1).unique()

    for fuel in demand_region.columns.get_level_values(1).unique():
        demand_region["DE", fuel] = 0

    for region in regions:
        for f1, f2 in combine_fuels.items():
            demand_region[region, f1] += demand_region[region, f2]
            demand_region.drop((region, f2), axis=1, inplace=True)
        cols = list(set(demand_region[region].columns) - set(region_fuels))
        for col in cols:
            demand_region["DE", col] += demand_region[region, col]
            demand_region.drop((region, col), axis=1, inplace=True)

    if time_index is not None:
        demand_region.index = time_index

    if not keep_unit:
        msg = (
            "The unit of the source is 'TJ'. "
            "Will be divided by {0} to get 'MWh'."
        )
        converter = 0.0036
        demand_region = demand_region.div(converter)
        logging.debug(msg.format(converter))

    demand_region.sort_index(1, inplace=True)

    for c in demand_region.columns:
        if demand_region[c].sum() == 0:
            demand_region.drop(c, axis=1, inplace=True)

    return demand_region


def scenario_demand(regions, year, name, opsd_version=None, weather_year=None):
    """

    Parameters
    ----------
    regions
    year
    name
    opsd_version
    weather_year

    Returns
    -------

    Examples
    --------
    >>> from reegis import geometries  # doctest: +SKIP
    >>> fs=geometries.get_federal_states_polygon()  # doctest: +SKIP
    >>> my_demand=scenario_demand(regions, 2014, "de21")  # doctest: +SKIP
    >>> int(my_demand["DE01", "district heating"].sum())  # doctest: +SKIP
    18639262
    >>> int(my_demand["DE05", "all"].sum())  # doctest: +SKIP
    10069304

    """
    demand_series = {
        "electricity demand series": scenario_elec_demand(
            pd.DataFrame(),
            regions,
            year,
            name,
            weather_year=weather_year,
            version=opsd_version,
        )
    }
    if cfg.get("creator", "heat"):
        demand_series["heat demand series"] = scenario_heat_demand(
            regions, year, weather_year=weather_year
        ).reset_index(drop=True)
    return demand_series


def scenario_heat_demand(regions, year, weather_year=None):
    """

    Parameters
    ----------
    regions
    year
    weather_year

    Returns
    -------

    """
    return get_heat_profiles_deflex(
        regions, year, weather_year=weather_year
    ).sort_index(1)


def scenario_elec_demand(
    table, regions, year, name, version=None, weather_year=None
):
    """

    Parameters
    ----------
    table
    regions
    year
    name
    weather_year

    Returns
    -------

    """
    if weather_year is None:
        demand_year = year
    else:
        demand_year = weather_year

    df = demand_elec.get_entsoe_profile_by_region(
        regions, demand_year, name, annual_demand="bmwi", version=version
    )
    df = pd.concat([df], axis=1, keys=["all"]).swaplevel(0, 1, 1)
    df = df.reset_index(drop=True)
    if not calendar.isleap(year) and len(df) > 8760:
        df = df.iloc[:8760]
    return pd.concat([table, df], axis=1).sort_index(1)


if __name__ == "__main__":
    pass
