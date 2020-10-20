"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import pandas as pd
from reegis import storages


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
    ['DE01', 'DE03', 'DE05', 'DE06', 'DE08', 'DE09', 'DE14', 'DE15', 'DE16']
    >>> int(deflex_storages.loc[("DE03", "phes"), "turbine"])
    220
    >>> int(deflex_storages.loc[("DE16", "phes"), "energy"])
    12115
    """
    stor = storages.pumped_hydroelectric_storage_by_region(regions, year, name)
    return pd.concat([stor], keys=["phes"]).swaplevel(0, 1)
