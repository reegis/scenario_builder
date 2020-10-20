"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import os
from types import SimpleNamespace

import pandas as pd
from reegis.tools import download_file

from scenario_builder import config as cfg

TRANSLATION_FUEL = {
    "Abfall": "waste",
    "Kernenergie": "nuclear",
    "Braunkohle": "lignite",
    "Steinkohle": "hard coal",
    "Erdgas": "natural gas",
    "GuD": "natural gas",
    "Gasturbine": "natural gas",
    "Öl": "oil",
    "Sonstige": "other",
    "Emissionszertifikatspreis": "co2_price",
}


def get_ewi_data():
    """

    Returns
    -------
    namedtuple

    Examples
    --------
    >>> my_ewi_data = get_ewi_data()
    >>> round(my_ewi_data.fuel_costs.loc["hard coal", "value"], 2)
    11.28

    """
    # Download file
    url = (
        "https://www.ewi.uni-koeln.de/cms/wp-content/uploads/2019/12"
        "/EWI_Merit_Order_Tool_2019_1_4.xlsm"
    )
    fn = os.path.join(cfg.get("paths", "general"), "ewi.xlsm")
    download_file(fn, url)

    # Create named tuple with all sub tables
    ewi_tables = {
        "fuel_costs": {"skiprows": 7, "usecols": "C:F", "nrows": 7},
        "transport_costs": {"skiprows": 21, "usecols": "C:F", "nrows": 7},
        "variable_costs": {"skiprows": 31, "usecols": "C:F", "nrows": 8},
        "downtime_factor": {
            "skiprows": 31,
            "usecols": "H:K",
            "nrows": 8,
            "scale": 0.01,
        },
        "emission": {"skiprows": 31, "usecols": "M:P", "nrows": 7},
        "co2_price": {"skiprows": 17, "usecols": "C:F", "nrows": 1},
    }
    ewi_data = {}
    cols = ["fuel", "value", "unit", "source"]
    xls = pd.ExcelFile(fn)
    for table in ewi_tables.keys():
        tmp = xls.parse("Start", header=[0], **ewi_tables[table]).replace(
            TRANSLATION_FUEL
        )
        tmp.drop_duplicates(tmp.columns[0], keep="first", inplace=True)
        tmp.columns = cols
        ewi_data[table] = tmp.set_index("fuel")
        if "scale" in ewi_tables[table]:
            ewi_data[table]["value"] *= ewi_tables[table]["scale"]

    return SimpleNamespace(**ewi_data)
