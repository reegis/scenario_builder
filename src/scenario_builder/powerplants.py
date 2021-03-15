"""Create a basic scenario from the internal data structure.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

import logging
import os
from warnings import warn

import pandas as pd
from reegis import bmwi
from reegis import config as cfg
from reegis import energy_balance
from reegis import geometries as reegis_geometries
from reegis import powerplants

from scenario_builder import data
from scenario_builder import demand

# Todo: Revise and test.


def pp_reegis2deflex(regions, name, filename_in=None, filename_out=None):
    """
    Add federal states and deflex regions to powerplant table from reegis. As
    the process takes a while the result is stored for further usage.

    Returns
    -------
    str : The full path where the result file is stored.

    """
    if filename_out is None:
        filename_out = os.path.join(
            cfg.get("paths", "powerplants"),
            cfg.get("powerplants", "deflex_pp"),
        ).format(map=name)

    # Add deflex regions to powerplants
    pp = powerplants.add_regions_to_powerplants(
        regions, name, dump=False, filename=filename_in
    )

    # Add federal states to powerplants
    federal_states = reegis_geometries.get_federal_states_polygon()
    pp = powerplants.add_regions_to_powerplants(
        federal_states, "federal_states", pp=pp, dump=False
    )

    # store the results for further usage of deflex
    pp.to_hdf(filename_out, "pp")
    return filename_out


# def remove_onshore_technology_from_offshore_regions(df):
#     """ This filter should be improved. It is slow and has to be adapted
#     manually. Anyhow it seems to work this way."""
#
#     logging.info("Removing onshore technology from offshore regions.")
#     logging.info("The code is not efficient. So it may take a while.")
#
#     offshore_regions=(
#         cfg.get_dict_list('offshore_regions_set')[cfg.get('init', 'map')])
#
#     coast_regions={'de02': {'MV': 'DE01',
#                               'SH': 'DE01',
#                               'NI': 'DE01 '},
#                      'de17': {'MV': 'DE13',
#                               'SH': 'DE01',
#                               'NI': 'DE03'},
#                      'de21': {'MV': 'DE01',
#                               'SH': 'DE13',
#                               'NI': 'DE14'},
#                      'de22': {'MV': 'DE01',
#                               'SH': 'DE13',
#                               'NI': 'DE14'}}
#     try:
#         dc=coast_regions[cfg.get('init', 'map')]
#     except KeyError:
#         raise ValueError('Coast regions not defined for {0} model.'.format(
#             cfg.get('init', 'map')))
#
#     region_column='{0}_region'.format(cfg.get('init', 'map'))
#
#     for ttype in ['Solar', 'Bioenergy', 'Wind']:
#         for region in offshore_regions:
#             logging.debug("Clean {1} from {0}.".format(region, ttype))
#
#             c1=df['energy_source_level_2'] == ttype
#             c2=df[region_column] == region
#
#             condition=c1 & c2
#
#             if ttype == 'Wind':
#                 condition=c1 & c2 & (df['technology'] == 'Onshore')
#
#             for i, v in df.loc[condition].iterrows():
#                 df.loc[i, region_column]=(
#                     dc[df.loc[i, 'federal_states']])
#     return df


def process_pp_table(pp):
    # # Remove powerplants outside Germany
    # for state in cfg.get_list('powerplants', 'remove_states'):
    #     pp=pp.loc[pp.state != state]
    #
    # if clean_offshore:
    #     pp=remove_onshore_technology_from_offshore_regions(pp)
    # Remove PHES (storages)
    if cfg.get("powerplants", "remove_phes"):
        pp = pp.loc[pp.technology != "Pumped storage"]
    return pp


def get_deflex_pp_by_year(
    regions, year, name, overwrite_capacity=False, filename=None
):
    """

    Parameters
    ----------
    regions : GeoDataFrame
    year : int
    name : str
    filename : str
    overwrite_capacity : bool
        By default (False) a new column "capacity_<year>" is created. If set to
        True the old capacity column will be overwritten.

    Returns
    -------

    """
    if filename is None:
        filename = os.path.join(
            cfg.get("paths", "powerplants"),
            cfg.get("powerplants", "deflex_pp"),
        ).format(map=name)
    logging.info("Get deflex power plants for {0}.".format(year))
    if not os.path.isfile(filename):
        msg = "File '{0}' does not exist. Will create it from reegis file."
        logging.debug(msg.format(filename))
        filename = pp_reegis2deflex(regions, name, filename_out=filename)
    pp = pd.DataFrame(pd.read_hdf(filename, "pp"))

    # Remove unwanted data sets
    pp = process_pp_table(pp)

    filter_columns = ["capacity_{0}", "capacity_in_{0}"]

    # Get all powerplants for the given year.
    # If com_month exist the power plants will be considered month-wise.
    # Otherwise the commission/decommission within the given year is not
    # considered.

    for fcol in filter_columns:
        filter_column = fcol.format(year)
        orig_column = fcol[:-4]
        c1 = (pp["com_year"] < year) & (pp["decom_year"] > year)
        pp.loc[c1, filter_column] = pp.loc[c1, orig_column]

        c2 = pp["com_year"] == year
        pp.loc[c2, filter_column] = (
            pp.loc[c2, orig_column] * (12 - pp.loc[c2, "com_month"]) / 12
        )
        c3 = pp["decom_year"] == year
        pp.loc[c3, filter_column] = (
            pp.loc[c3, orig_column] * pp.loc[c3, "com_month"] / 12
        )

        if overwrite_capacity:
            pp[orig_column] = 0
            pp[orig_column] = pp[filter_column]
            del pp[filter_column]

    return pp


def scenario_powerplants(table_collection, regions, year, name):
    """Get power plants for the scenario year

    Examples
    --------
    >>> from reegis import geometries
    >>> fs=geometries.get_federal_states_polygon()
    >>> my_pp=scenario_powerplants(
    ...     dict(), fs, 2014, "federal_states")  # doctest: +SKIP
    >>> my_pp["volatile plants"].loc[("DE03", "wind"), "capacity"
    ...     ] # doctest: +SKIP
    3052.8
    >>> my_pp["power plants"].loc[("DE03", "lignite"), "capacity"
    ...     ] # doctest: +SKIP
    1135.6
    """
    pp = get_deflex_pp_by_year(regions, year, name, overwrite_capacity=True)
    tables = create_powerplants(pp, table_collection, year, name)
    tables["power plants"]["source region"] = "DE"
    return tables


def create_powerplants(
    pp, table_collection, year, region_column="deflex_region"
):
    """This function works for all power plant tables with an equivalent
    structure e.g. power plants by state or other regions."""
    logging.info("Adding power plants to your scenario.")

    replace_names = cfg.get_dict("source_names")

    # TODO Waste is not "other"
    replace_names.update(cfg.get_dict("source_groups"))
    pp["count"] = 1
    pp["energy_source_level_2"].replace(replace_names, inplace=True)

    pp["model_classes"] = pp["energy_source_level_2"].replace(
        cfg.get_dict("model_classes")
    )

    power_plants = {
        "volatile plants": pp.groupby(
            ["model_classes", region_column, "energy_source_level_2"]
        )
        .sum()[["capacity", "count"]]
        .loc["volatile plants"]
    }

    if cfg.get("creator", "group_transformer"):
        power_plants["power plants"] = (
            pp.groupby(
                ["model_classes", region_column, "energy_source_level_2"]
            )
            .sum()[["capacity", "capacity_in", "count"]]
            .loc["power plants"]
        )
        power_plants["power plants"]["fuel"] = power_plants[
            "power plants"
        ].index.get_level_values(1)
    else:
        pp["efficiency"] = pp["efficiency"].round(2)
        power_plants["power plants"] = (
            pp.groupby(
                [
                    "model_classes",
                    region_column,
                    "energy_source_level_2",
                    "efficiency",
                ]
            )
            .sum()[["capacity", "capacity_in", "count"]]
            .loc["power plants"]
        )
        power_plants["power plants"]["fuel"] = power_plants[
            "power plants"
        ].index.get_level_values(1)
        power_plants["power plants"].index = [
            power_plants["power plants"].index.get_level_values(0),
            power_plants["power plants"].index.map("{0[1]} - {0[2]}".format),
        ]

    for class_name, pp_class in power_plants.items():
        if "capacity_in" in pp_class:
            pp_class["efficiency"] = (
                pp_class["capacity"] / pp_class["capacity_in"] * 100
            )
            del pp_class["capacity_in"]
        if cfg.get("creator", "round") is not None:
            pp_class = pp_class.round(cfg.get("creator", "round"))
        if "efficiency" in pp_class:
            pp_class["efficiency"] = pp_class["efficiency"].div(100)
        pp_class = pp_class.transpose()
        pp_class.index.name = "parameter"
        table_collection[class_name] = pp_class.transpose()

    table_collection = add_pp_limit(table_collection, year)
    table_collection = add_additional_values(table_collection)
    return table_collection


def add_additional_values(table_collection):
    """

    Parameters
    ----------
    table_collection

    Returns
    -------

    """
    transf = table_collection["power plants"]
    for values in ["variable_costs", "downtime_factor"]:
        if cfg.get("creator", "use_{0}".format(values)) is True:
            add_values = getattr(data.get_ewi_data(), values)
            if cfg.has_option("creator", "downtime_bioenergy"):
                add_values.loc["bioenergy", "value"] = cfg.get(
                    "creator", "downtime_bioenergy"
                )
            transf = transf.merge(
                add_values,
                right_index=True,
                how="left",
                left_on="fuel",
            )
            transf.drop(["unit", "source"], axis=1, inplace=True)
            transf.rename({"value": values}, axis=1, inplace=True)
        else:
            transf[values] = 0
    table_collection["power plants"] = transf
    return table_collection


def add_pp_limit(table_collection, year):
    """

    Parameters
    ----------
    table_collection
    year

    Returns
    -------

    """
    if len(cfg.get_list("creator", "limited_transformer")) > 0:
        # Multiply with 1000 to get MWh (bmwi: GWh)
        repp = bmwi.bmwi_re_energy_capacity() * 1000
        trsf = table_collection["power plants"]
        for limit_trsf in cfg.get_list("creator", "limited_transformer"):
            trsf = table_collection["power plants"]
            try:
                limit = repp.loc[year, (limit_trsf, "energy")]
            except KeyError:
                msg = "Cannot calculate limit for {0} in {1}."
                raise ValueError(msg.format(limit_trsf, year))
            cond = trsf["fuel"] == limit_trsf
            cap_sum = trsf.loc[pd.Series(cond)[cond].index, "capacity"].sum()
            trsf.loc[pd.Series(cond)[cond].index, "limit_elec_pp"] = (
                trsf.loc[pd.Series(cond)[cond].index, "capacity"]
                .div(cap_sum)
                .multiply(limit)
                + 0.5
            )
        trsf["limit_elec_pp"] = trsf["limit_elec_pp"].fillna(float("inf"))

        table_collection["power plants"] = trsf
    return table_collection


def scenario_chp(table_collection, regions, year, name, weather_year=None):
    """

    Parameters
    ----------
    table_collection
    regions
    year
    name
    weather_year

    Returns
    -------

    Examples
    --------
    >>> from reegis import geometries
    >>> fs=geometries.get_federal_states_polygon()
    >>> pp=scenario_powerplants(dict(), fs, 2014, "federal_states"
    ...     )  # doctest: +SKIP
    >>> int(pp["power plants"].loc[("NW", "hard coal"), "capacity"]
    ...     )  # doctest: +SKIP
    1291
    >>> table=scenario_chp(pp, fs, 2014, "federal_states")  # doctest: +SKIP
    >>> transf=table["power plants"]  # doctest: +SKIP
    >>> chp_hp=table["heat-chp plants"]  # doctest: +SKIP
    >>> int(transf.loc[("MV", "hard coal"), "capacity"])  # doctest: +SKIP
    623
    >>> int(chp_hp.loc[("HH", "hard coal"), "capacity_elec_chp"]
    ...     )  # doctest: +SKIP
    667
    """
    # values from heat balance

    cb = energy_balance.get_transformation_balance_by_region(
        regions, year, name
    )
    cb.rename(columns={"re": "bioenergy"}, inplace=True)
    heat_b = powerplants.calculate_chp_share_and_efficiency(cb)

    heat_demand = demand.get_heat_profiles_deflex(
        regions, year, weather_year=weather_year
    )
    tables = chp_table(heat_b, heat_demand, table_collection)
    tables["heat-chp plants"]["source region"] = "DE"
    return tables


def chp_table(heat_b, heat_demand, table_collection, regions=None):
    """

    Parameters
    ----------
    heat_b
    heat_demand
    table_collection
    regions

    Returns
    -------

    """

    chp_hp = pd.DataFrame(
        columns=pd.MultiIndex(levels=[[], []], codes=[[], []])
    )

    rows = ["Heizkraftwerke der allgemeinen Versorgung (nur KWK)", "Heizwerke"]
    if regions is None:
        regions = sorted(heat_b.keys())

    eta_heat_chp = None
    eta_elec_chp = None

    for region in regions:
        eta_hp = round(heat_b[region]["sys_heat"] * heat_b[region]["hp"], 2)
        eta_heat_chp = round(
            heat_b[region]["sys_heat"] * heat_b[region]["heat_chp"], 2
        )
        eta_elec_chp = round(heat_b[region]["elec_chp"], 2)

        # Due to the different efficiency between heat from chp-plants and
        # heat from heat-plants the share of the output is different to the
        # share of the input. As heat-plants will produce more heat per fuel
        # factor will be greater than 1 and for chp-plants smaller than 1.
        out_share_factor_chp = heat_b[region]["out_share_factor_chp"]
        out_share_factor_hp = heat_b[region]["out_share_factor_hp"]

        # Remove "district heating" and "electricity" and spread the share
        # to the remaining columns.
        share = pd.DataFrame(columns=heat_b[region]["fuel_share"].columns)
        for row in rows:
            tmp = heat_b[region]["fuel_share"].loc[region, :, row]
            tot = float(tmp["total"])

            d = float(tmp["district heating"] + tmp["electricity"])
            tmp = tmp + tmp / (tot - d) * d
            tmp = tmp.reset_index(drop=True)
            share.loc[row] = tmp.loc[0]
        del share["district heating"]
        del share["electricity"]

        # Remove the total share
        del share["total"]

        max_val = float(heat_demand[region]["district heating"].max())
        sum_val = float(heat_demand[region]["district heating"].sum())

        share = share.rename({"gas": "natural gas"}, axis=1)

        for fuel in share.columns:
            # CHP
            chp_hp.loc["limit_heat_chp", (region, fuel)] = round(
                sum_val * share.loc[rows[0], fuel] * out_share_factor_chp + 0.5
            )
            cap_heat_chp = round(
                max_val * share.loc[rows[0], fuel] * out_share_factor_chp
                + 0.005,
                2,
            )
            chp_hp.loc["capacity_heat_chp", (region, fuel)] = cap_heat_chp
            cap_elec = cap_heat_chp / eta_heat_chp * eta_elec_chp
            chp_hp.loc["capacity_elec_chp", (region, fuel)] = round(
                cap_elec, 2
            )
            chp_hp[region] = chp_hp[region].fillna(0)

            # HP
            chp_hp.loc["limit_hp", (region, fuel)] = round(
                sum_val * share.loc[rows[1], fuel] * out_share_factor_hp + 0.5
            )
            chp_hp.loc["capacity_hp", (region, fuel)] = round(
                max_val * share.loc[rows[1], fuel] * out_share_factor_hp
                + 0.005,
                2,
            )
            if chp_hp.loc["capacity_hp", (region, fuel)] > 0:
                chp_hp.loc["efficiency_hp", (region, fuel)] = eta_hp
            if cap_heat_chp * cap_elec > 0:
                chp_hp.loc[
                    "efficiency_heat_chp", (region, fuel)
                ] = eta_heat_chp
                chp_hp.loc[
                    "efficiency_elec_chp", (region, fuel)
                ] = eta_elec_chp
            chp_hp.loc["fuel", (region, fuel)] = fuel

    logging.info("Done")

    chp_hp.sort_index(axis=1, inplace=True)

    # for col in trsf.sum().loc[trsf.sum() == 0].index:
    #     del trsf[col]
    # trsf[trsf < 0] = 0

    table_collection["heat-chp plants"] = chp_hp.transpose()

    table_collection = substract_chp_capacity_and_limit_from_pp(
        table_collection, eta_heat_chp, eta_elec_chp
    )

    return {
        "heat-chp plants": table_collection["heat-chp plants"],
        "power plants": table_collection["power plants"],
    }


def substract_chp_capacity_and_limit_from_pp(tc, eta_heat_chp, eta_elec_chp):
    """

    Parameters
    ----------
    tc
    eta_heat_chp
    eta_elec_chp

    Returns
    -------

    """
    chp_hp = tc["heat-chp plants"]
    pp = tc["power plants"]
    diff = 0
    for region in chp_hp.index.get_level_values(0).unique():
        for fuel in chp_hp.loc[region].index:
            # If the power plant limit is not "inf" the limited electricity
            # output of the chp plant has to be subtracted from the power plant
            # limit because this is related to the overall electricity output.
            limit_elec_pp = pp.loc[
                (pp.index.get_level_values(0) == region) & (pp.fuel == fuel),
                "limit_elec_pp",
            ].sum()
            if not limit_elec_pp == float("inf"):
                limit_elec_chp = (
                    chp_hp.loc[(region, fuel), "limit_heat_chp"]
                    / eta_heat_chp
                    * eta_elec_chp
                )
                factor = 1 - limit_elec_chp / limit_elec_pp
                pp.loc[
                    (pp.index.get_level_values(0) == region)
                    & (pp.fuel == fuel),
                    "limit_elec_pp",
                ] *= factor

            # Substract the electric capacity of the chp from the capacity
            # of the power plant.
            capacity_elec_pp = pp.loc[
                (pp.index.get_level_values(0) == region) & (pp.fuel == fuel),
                "capacity",
            ].sum()
            capacity_elec_chp = chp_hp.loc[(region, fuel), "capacity_elec_chp"]
            if capacity_elec_chp < capacity_elec_pp:
                factor = 1 - capacity_elec_chp / capacity_elec_pp
            elif capacity_elec_chp == capacity_elec_pp:
                factor = 0
            else:
                factor = 0
                diff += capacity_elec_chp - capacity_elec_pp
                msg = (
                    "Electricity capacity of chp plant it greater than "
                    "existing electricity capacity in one region.\n"
                    "Region: {0}, capacity_elec: {1}, capacity_elec_chp: "
                    "{2}, fuel: {3}"
                )
                warn(
                    msg.format(
                        region, capacity_elec_pp, capacity_elec_chp, fuel
                    ),
                    UserWarning,
                )
            pp.loc[
                (pp.index.get_level_values(0) == region) & (pp.fuel == fuel),
                "capacity",
            ] *= factor
    if diff > 0:
        msg = (
            "Electricity capacity of some chp plants it greater than "
            "existing electricity capacity.\n"
            "Overall difference: {0}"
        )
        warn(msg.format(diff), UserWarning)
    return tc


if __name__ == "__main__":
    pass
