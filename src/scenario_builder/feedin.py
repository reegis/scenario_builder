"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

from reegis import coastdat


def scenario_feedin(regions, year, name, weather_year=None):
    """

    Parameters
    ----------
    regions
    year
    name
    weather_year

    Returns
    -------

    Examples
    --------
    >>> regions=geometries.deflex_regions(rmap="de21")  # doctest: +SKIP
    >>> f=scenario_feedin(regions, 2014, "de21")  # doctest: +SKIP
    >>> f["DE01"].sum()  # doctest: +SKIP
    geothermal    4380.000000
    hydro         1346.632529
    solar          913.652083
    wind          2159.475906
    dtype: float64
    >>> f["DE16"].sum()  # doctest: +SKIP
    geothermal    4380.000000
    hydro         1346.632529
    solar          903.527200
    wind          1753.673492
    dtype: float64
    """
    wy = weather_year
    try:
        feedin = coastdat.scenario_feedin(year, name, weather_year=wy)
    except FileNotFoundError:
        coastdat.get_feedin_per_region(year, regions, name, weather_year=wy)
        feedin = coastdat.scenario_feedin(year, name, weather_year=wy)
    return feedin
