"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import pandas as pd
from reegis import mobility
from scenario_builder import config as cfg


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
    >>> table = scenario_mobility(2015, {})
    >>> table["mobility_mileage"]["DE"].sum()
    diesel    3.769021e+11
    petrol    3.272263e+11
    other     1.334462e+10
    dtype: float64
    >>> table["mobility_spec_demand"]["DE"].loc["passenger car"]
    diesel    0.067
    petrol    0.079
    other     0.000
    Name: passenger car, dtype: float64
    >>> table["mobility_energy_content"]["DE"]["diesel"]
    energy_per_liter [MJ/l]    34.7
    Name: diesel, dtype: float64
    """

    table["mobility_mileage"] = mobility.get_mileage_by_type_and_fuel(year)

    # fetch table of specific demand by fuel and vehicle type (from 2011)
    table["mobility_spec_demand"] = (
        pd.DataFrame(
            cfg.get_dict_list("fuel consumption"),
            index=["diesel", "petrol", "other"],
        )
        .astype(float)
        .transpose()
    )

    # fetch the energy content of the different fuel types
    table["mobility_energy_content"] = pd.DataFrame(
        cfg.get_dict("energy_per_liter"), index=["energy_per_liter [MJ/l]"]
    )[["diesel", "petrol", "other"]]

    for key in [
        "mobility_mileage",
        "mobility_spec_demand",
        "mobility_energy_content",
    ]:
        # Add "DE" as region level to be consistent to other tables
        table[key].columns = pd.MultiIndex.from_product(
            [["DE"], table[key].columns]
        )
    return table
