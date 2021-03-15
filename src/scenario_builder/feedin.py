"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

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
    >>> from reegis import geometries  # doctest: +SKIP
    >>> fs=geometries.get_federal_states_polygon()  # doctest: +SKIP
    >>> f = scenario_feedin(regions, 2014, "fs")  # doctest: +SKIP
    >>> f["NI"].sum()  # doctest: +SKIP
    geothermal    4380.000000
    hydro         2242.134748
    solar          831.424963
    wind          2602.090478
    dtype: float64
    >>> f["BY"].sum()  # doctest: +SKIP
    geothermal    4380.000000
    hydro         2242.134748
    solar          849.019372
    wind          1279.604124
    dtype: float64
    """
    wy = weather_year
    try:
        feedin = coastdat.scenario_feedin(year, name, weather_year=wy)
    except FileNotFoundError:
        coastdat.get_feedin_per_region(year, regions, name, weather_year=wy)
        feedin = coastdat.scenario_feedin(year, name, weather_year=wy)
    return feedin
