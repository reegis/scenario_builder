"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import pandas as pd
from reegis import storages


PARAMETER_RENAME = {
    "energy": "energy content",
    "energy_inflow": "energy inflow",
    "pump": "charge capacity",
    "turbine": "discharge capacity",
    "pump_eff": "charge efficiency",
    "turbine_eff": "discharge efficiency",
}


def scenario_storages(regions, year, name):
    """
    Fetch storage, pump and turbine capacity and their efficiency of
    hydroelectric storages for each deflex region.

    Parameters
    ----------
    regions
    year
    name

    Returns
    -------

    Examples
    --------
    >>> from reegis import geometries
    >>> fs=geometries.get_federal_states_polygon()
    >>> deflex_storages=scenario_storages(fs, 2012, "de17")
    >>> list(deflex_storages.index.get_level_values(0))
    ['BW', 'BY', 'HE', 'NI', 'NW', 'SH', 'SN', 'ST', 'TH']
    >>> int(deflex_storages.loc[("TH", "phes"), "turbine"])
    1522
    >>> int(deflex_storages.loc[("TH", "phes"), "energy"])
    12115
    """
    stor = storages.pumped_hydroelectric_storage_by_region(regions, year, name)
    stor = pd.concat([stor], keys=["phes"]).swaplevel(0, 1)
    stor["loss rate"] = 0
    return stor.rename(columns=PARAMETER_RENAME)
