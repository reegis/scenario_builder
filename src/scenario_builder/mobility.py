"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
import calendar
import configparser

import pandas as pd
from reegis import config as cfg
from reegis import mobility


def scenario_mobility(year, table):
    """

    Parameters
    ----------
    year
    table

    Returns
    -------

    Examples
    --------
    >>> my_table = scenario_mobility(2015, {})
    >>> my_table["mobility_mileage"]["DE"].sum()
    diesel    3.769021e+11
    petrol    3.272263e+11
    other     1.334462e+10
    dtype: float64
    >>> my_table["mobility_spec_demand"]["DE"].loc["passenger car"]
    diesel    0.067
    petrol    0.079
    other     0.000
    Name: passenger car, dtype: float64
    >>> my_table["mobility_energy_content"]["DE"]["diesel"]
    energy_per_liter [MJ/l]    34.7
    Name: diesel, dtype: float64
    """
    if calendar.isleap(year):
        hours_of_the_year = 8784
    else:
        hours_of_the_year = 8760

    try:
        other = cfg.get("creator", "mobility_other")
    except configparser.NoSectionError:
        other = cfg.get("general", "mobility_other")

    mobility_mileage = mobility.get_mileage_by_type_and_fuel(year)

    # fetch table of specific demand by fuel and vehicle type (from 2011)
    mobility_spec_demand = (
        pd.DataFrame(
            cfg.get_dict_list("fuel consumption"),
            index=["diesel", "petrol", "other"],
        )
        .astype(float)
        .transpose()
    )

    mobility_spec_demand["other"] = mobility_spec_demand[other]
    fuel_usage = mobility_spec_demand.mul(mobility_mileage).sum()

    # fetch the energy content of the different fuel types
    mobility_energy_content = pd.DataFrame(
        cfg.get_dict("energy_per_liter"), index=["energy_per_liter [MJ/l]"]
    )[["diesel", "petrol", "other"]]

    mobility_energy_content["other"] = mobility_energy_content[other]

    # Convert to MW????? BITTE GENAU!!!
    energy_usage = fuel_usage.mul(mobility_energy_content).div(3600)

    s = energy_usage.div(hours_of_the_year).transpose()[
        "energy_per_liter [MJ/l]"
    ]
    table["mobility demand series"] = pd.DataFrame(
        index=range(hours_of_the_year), columns=energy_usage.columns
    ).fillna(1)

    table["mobility demand series"] = table["mobility demand series"].mul(
        s, axis=1
    )

    table["mobility demand series"][other] += table["mobility demand series"][
        "other"
    ]
    table["mobility demand series"].drop("other", axis=1, inplace=True)

    table["mobility demand series"] = (
        table["mobility demand series"].astype(float).round().astype(int)
    )

    table["mobility"] = pd.DataFrame(
        index=["diesel", "petrol", "electricity"],
        columns=["efficiency", "source", "source region"],
    )

    for col in table["mobility"].columns:
        for idx in table["mobility"].index:
            section = "mobility: " + idx
            table["mobility"].loc[idx, col] = cfg.get(section, col)

    # Add "DE" as region level to be consistent to other tables
    table["mobility"].index = pd.MultiIndex.from_product(
        [["DE"], table["mobility"].index]
    )
    table["mobility demand series"].columns = pd.MultiIndex.from_product(
        [["DE"], table["mobility demand series"].columns]
    )
    return table
