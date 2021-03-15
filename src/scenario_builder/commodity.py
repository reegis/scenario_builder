"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import logging
from warnings import warn

import pandas as pd
from reegis import commodity_sources
from reegis import config as cfg

from scenario_builder import data


def scenario_commodity_sources(year):
    """

    Parameters
    ----------
    year

    Returns
    -------

    Examples
    --------
    >>> from reegis import geometries
    >>> from scenario_builder import powerplants
    >>> fs=geometries.get_federal_states_polygon()  # doctest: +SKIP
    >>> pp=powerplants.scenario_powerplants(dict(), fs, 2014, "federal_states"
    ...     )  # doctest: +SKIP
    >>> src=scenario_commodity_sources(pp)  # doctest: +SKIP
    >>> round(src.loc[("DE", "hard coal"), "costs"], 2)  # doctest: +SKIP
    12.53
    >>> round(src.loc[("DE", "natural gas"), "emission"], 2)  # doctest: +SKIP
    201.0
    """
    if cfg.get("creator", "costs_source") == "reegis":
        commodity_src = create_commodity_sources_reegis(year)
    elif cfg.get("creator", "costs_source") == "ewi":
        commodity_src = create_commodity_sources_ewi()
    else:
        commodity_src = None

    # Add region level to be consistent to other tables
    commodity_src.index = pd.MultiIndex.from_product(
        [["DE"], commodity_src.index]
    )

    if cfg.get("creator", "use_CO2_costs") is False:
        commodity_src["co2_price"] = 0

    commodity_src["annual limit"] = "inf"
    return commodity_src


def create_commodity_sources_ewi():
    """

    Returns
    -------

    """
    ewi = data.get_ewi_data()
    df = pd.DataFrame()
    df["costs"] = ewi.fuel_costs["value"] + ewi.transport_costs["value"]
    df["emission"] = ewi.emission["value"].multiply(1000)
    df["co2_price"] = float(ewi.co2_price["value"])
    missing = "bioenergy"
    msg = (
        "Costs/Emission for {0} in ewi is missing.\n"
        "Values for {0} are hard coded! Use with care."
    )
    warn(msg.format(missing), UserWarning)
    df.loc[missing, "emission"] = 7.2
    df.loc[missing, "costs"] = 20
    df.loc[missing, "co2_price"] = df.loc["natural gas", "co2_price"]
    return df


def create_commodity_sources_reegis(year, use_znes_2014=True):
    """

    Parameters
    ----------
    year
    use_znes_2014

    Returns
    -------

    """
    msg = (
        "The unit for {0} of the source is '{1}'. "
        "Will multiply it with {2} to get '{3}'."
    )

    converter = {
        "costs": ["costs", "EUR/J", 1e9 * 3.6, "EUR/MWh"],
        "emission": ["emission", "g/J", 1e6 * 3.6, "kg/MWh"],
    }

    cs = commodity_sources.get_commodity_sources()
    rename_cols = {
        key.lower(): value
        for key, value in cfg.get_dict("source_names").items()
    }
    cs = cs.rename(columns=rename_cols)
    cs_year = cs.loc[year]
    if use_znes_2014:
        before = len(cs_year[cs_year.isnull()])
        cs_year = cs_year.fillna(cs.loc[2014])
        after = len(cs_year[cs_year.isnull()])
        if before - after > 0:
            logging.warning("Values were replaced with znes2014 data.")
    cs_year = cs_year.sort_index().unstack()

    # convert units
    for key in converter.keys():
        cs_year[key] = cs_year[key].multiply(converter[key][2])
        logging.warning(msg.format(*converter[key]))

    return cs_year
