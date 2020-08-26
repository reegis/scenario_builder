from disaggregator import data, spatial
from reegis import geometries as geo, config as cfg
import pandas as pd
import os

def get_household_heatload_by_NUTS3_scenario(
    m_type,  weight_by_income=True
):

    """
    Parameters
    ----------
    region_pick : list
        Selected regions in NUTS-3 format
    m_type: int
        1 = Status Quo, 2 = Conventional modernisation, 3 = Future modernisation
    weight_by_income : bool
        Choose whether heat demand shall be weighted by household income

    Returns: pd.DataFrame
        Dataframe containing yearly household load for selection
    -------
    """
    # Abweichungen in den Jahresmengen bei bottom-up
    qdem_temp= spatial.disagg_households_heatload_DB_scenario(
        m_type, weight_by_income=weight_by_income
    )

    qdem = qdem_temp.sum(axis=1)

    return qdem


def get_CTS_heatload_scenario(region_pick, efficiency_gain=0.5):
    """
    Parameters
    ----------
    region_pick : list
        Selected regions in NUTS-3 format
    efficiency_gain: float
        Reduction factor for heatload due to increased CTS building efficiency
        (0.99 equals 99% reduction, 0% equals no reduction)

    Returns: pd.DataFrame
        Dataframe containing yearly heat CTS heat consumption by NUTS-3 region
    -------
    """

    # Define year of interest
    data.cfg["base_year"] = 2015
    # Get gas consumption of defined year and divide by gas-share in end energy use for heating
    heatload_hh = data.gas_consumption_HH().sum() / 0.47
    # Multiply with CTS heatload share, Assumption: Share is constant because heatload mainly depends on wheather
    heatload_CTS_2015 = 0.37 * heatload_hh  # Verhältnis aus dem Jahr 2017
    # Assumption: Heatload is reduced equally for all regions
    heatload_CTS = heatload_CTS_2015 * (1-efficiency_gain)
    # Calculate CTS gas consumption by economic branch and NUTS3-region
    gc_CTS = spatial.disagg_CTS_industry(
        sector="CTS", source="gas", use_nuts3code=True
    )
    # Sum up the gas consumption per NUTS3-region
    sum_gas_CTS = gc_CTS.sum().sum()
    # Calculate scaling factor
    inc_fac = heatload_CTS / sum_gas_CTS
    # Calculate CTS heatload: Assumption: Heatload correlates strongly with gas consumption
    gc_CTS_new = gc_CTS.multiply(inc_fac)
    # Select heatload of NUTS3-regions of interest
    gc_CTS_combined = gc_CTS_new.sum()
    df = gc_CTS_combined[region_pick]

    return df


def get_industry_heating_hotwater_scenario(region_pick, efficiency_gain=0.5):
    """
    Parameters
    ----------
    region_pick : list
        Selected regions in NUTS-3 format
    efficiency_gain: float
        Reduction factor for heatload due to increased CTS building efficiency
        (0.99 equals 99% reduction, 0% equals no reduction)

    Returns: pd.DataFrame
        Dataframe containing yearly industry heat consumption by NUTS-3 region
    -------
    """

    # Define year of interest
    data.cfg["base_year"] = 2015
    # Get gas consumption of defined year and divide by gas-share in end energy use for heating
    heatload_hh = data.gas_consumption_HH().sum() / 0.47
    # Multiply with industries heatload share, Assumption: Share is constant because heatload mainly depends on wheather
    heatload_industry_2015 = 0.089 * heatload_hh  # Verhältnis aus dem Jahr 2017
    heatload_industry = heatload_industry_2015 * (1-efficiency_gain)
    # Calculate industry gas consumption by economic branch and NUTS3-region
    gc_industry = spatial.disagg_CTS_industry(
        sector="industry", source="gas", use_nuts3code=True
    )
    # Sum up the gas consumption per NUTS3-region
    sum_gas_industry = gc_industry.sum().sum()
    # Calculate scaling factor
    inc_fac = heatload_industry / sum_gas_industry
    # Calculate indsutries heatload: Assumption: Heatload correlates strongly with gas consumption
    gc_industry_new = gc_industry.multiply(inc_fac)
    gc_industry_combined = gc_industry_new.sum()
    # Select heatload of NUTS3-regions of interest
    df = gc_industry_combined[region_pick]

    return df


def get_industry_CTS_process_heat_scenario(region_pick, efficiency_gain=0.2):
    """
    Parameters
    ----------
    region_pick : list
        Selected regions in NUTS-3 format
    efficiency_gain: float
        Reduction factor for heatload due to increased CTS building efficiency
        (0.99 equals 99% reduction, 0% equals no reduction)

    Returns: pd.DataFrame
        Dataframe containing yearly industry heat consumption by NUTS-3 region
    -------
    """

    # Select year
    data.cfg["base_year"] = 2015
    # Get industrial gas consumption by NUTS3
    gc_industry = spatial.disagg_CTS_industry(
        sector="industry", source="gas", use_nuts3code=True
    )
    sum_gas_industry = gc_industry.sum().sum()
    # Calculate factor of process heat consumption to gas consumption.
    # Assumption: Process heat demand correlates with gas demand
    process_heat_2015 = (515 + 42) * 1e6
    process_heat = process_heat_2015 * (1-efficiency_gain)
    inc_fac = process_heat / sum_gas_industry
    # Calculate process heat with factor
    ph_industry = gc_industry.multiply(inc_fac)
    ph_industry_combined = ph_industry.sum()
    # Select process heat consumptions for NUTS3-Regions of interest
    df = ph_industry_combined[region_pick]

    return df


def get_combined_heatload_for_region_scenario(name, region_pick=None, m_type=2 , eff_gain_CTS=0,
                                              eff_gain_ph=0, eff_gain_ihw=0):
    """
    Parameters
    ----------
    year : int
        Year of interest, so far only 2015 and 2016 are valid inputs
    name: string
        Name of scenario
    region_pick : list
        Selected regions in NUTS-3 format, if None function will return demand for all regions

    Returns: pd.DataFrame
        Dataframe containing aggregated yearly low temperature heat demand (households, CTS, industry) as well
        as high temperature heat demand (ProcessHeat) for selection
    -------
    """
    if region_pick is None:
        nuts3_index = data.database_shapes().index  # Select all NUTS3 Regions

    fn_pattern = "heat_consumption_by_nuts3_{name}.csv".format(name=name)
    fn = os.path.join(cfg.get("paths", "disaggregator"), fn_pattern)

    if not os.path.isfile(fn):
        tmp0 = get_household_heatload_by_NUTS3_scenario(
            m_type, weight_by_income=True
        )  # Nur bis 2016
        tmp1 = get_CTS_heatload_scenario(nuts3_index, eff_gain_CTS)  # 2015 - 2035 (projection)
        tmp2 = get_industry_heating_hotwater_scenario(nuts3_index, eff_gain_ihw)
        tmp3 = get_industry_CTS_process_heat_scenario(nuts3_index, eff_gain_ph)

        df_heating = pd.concat([tmp0, tmp1, tmp2, tmp3], axis=1)
        df_heating.columns = ["Households", "CTS", "Industry", "ProcessHeat"]
        df_heating.to_csv(fn)

    else:
        df_heating = pd.read_csv(fn)
        df_heating.set_index("nuts3", drop=True, inplace=True)

    return df_heating


test = get_combined_heatload_for_region_scenario('test123', region_pick=None, m_type=2 , eff_gain_CTS=0,
                                              eff_gain_ph=0, eff_gain_ihw=0)
