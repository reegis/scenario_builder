import os
import oemof.thermal.compression_heatpumps_and_chillers as cmpr_hp_chiller
import pandas as pd
import numpy as np
from disaggregator import data
from reegis import coastdat, demand_disaggregator
from reegis import config as cfg


def flow_temperature_dependent_on_ambient(t_max, t_min, t_amb):
    """
    Parameters
    ----------
    t_max : int
        Maximum flow temperature of heating system
    t_min : int
        Minimum flow temperature of heating system
    t_amb : pd.Series
        Ambient temperature

    Returns: list
        List containing flow temperature depending on heatload/ambient temperature
    -------
    """

    delta_t_flow = t_max - t_min
    delta_t_amb = 30
    T_flow = [t_max - (delta_t_flow/delta_t_amb) * i for i in range(31)]
    T_round = np.round(t_amb)

    t_ind = np.zeros(shape=(len(t_amb)))
    tvl = np.zeros(shape=(len(t_amb)))  # Vorlauftemperatur
    for i in range(len(t_amb)):
        if T_round[i] < -14:
            t_ind[i] = 1
        elif T_round[i] >= -14 and T_round[i] < 0:
            t_ind[i] = abs(15 + T_round[i])  # nimm erste 15 Stellen bei -10 bis 0°C
        elif T_round[i] >= 0:
            t_ind[i] = min(31, 16 + T_round[i])
        tvl[i] = int(max(t_min, T_flow[int(t_ind[i] - 1)]))

    tvl = list(tvl)

    return tvl


def calculate_COP(t_flow, t_low, quality_grade):
    """
    Parameters
    ----------
    t_flow : int
        Maximum flow temperature of heating system
    t_low : Series
        Minimum flow temperature of heating system
    quality_grade : float
        Ambient temperature

    Returns: list
        List containing flow temperature depending on heatload/ambient temperature
    -------
    """

    cops = cmpr_hp_chiller.calc_cops(
        temp_high=list([t_flow]),
        temp_low=t_low,
        quality_grade=quality_grade,
        mode='heat_pump',
        temp_threshold_icing=2,
        factor_icing=0.8)

    return cops


def calculate_dynamic_COP(t_flow, t_low, quality_grade):
    r"""
    This function calculates COPs of a heatpump. Both, the flow temperature and the heat source must be given
    as a timeseries and can very for each timestep.

    Parameters
    ----------
    t_flow : Series
        Flow temperature series
    t_low : Series
        Heat source of heatpump
    quality_grade : float
        Carnot efficiency factor of heat pump

    Returns: Series
        Series containing COPs
    -------
    """
    cops = []
    for i in range(0, len(t_flow)):
        tmp_high = list([t_flow[i]])
        tmp_low = list([t_low[i]])

        cop = cmpr_hp_chiller.calc_cops(
            temp_high=tmp_high,
            temp_low=tmp_low,
            quality_grade=quality_grade,
            mode='heat_pump',
            temp_threshold_icing=2,
            factor_icing=0.8)

        cops.append(cop[0])

    cops = pd.Series(cops)

    return cops


def calculate_mixed_COPS_per_region(t_amb, t_ground, quality_grade, share_ashp=0.7, share_gshp=0.3):
    """
    Parameters
    ----------
    t_amb : Series
        Ambient temperature
    t_ground : Series
        Ground temperature for GSHP
    quality_grade : float
        Ambient temperature
    share_ashp: Float
        Share of air sourced heat pumps
    share_gshp: Float
        Share of ground sourced heat pumps

    Returns: DataFrame
        DataFrame containing some COP series
    -------
    """

    t_flow = dict(high = 75, medium=55, low = 40)

    # Calculate flow temperature for different temperature levels
    tvl75 = flow_temperature_dependent_on_ambient(t_flow['high'], 50, t_amb)
    tvl50 = flow_temperature_dependent_on_ambient(t_flow['medium'], 30 , t_amb)
    tvl35 = flow_temperature_dependent_on_ambient(t_flow['low'], 30 , t_amb)

    # Calculate COPs for air sourced heat pump
    cop75_ASHP = calculate_dynamic_COP(tvl75, t_amb, quality_grade)
    cop50_ASHP = calculate_dynamic_COP(tvl50, t_amb, quality_grade)
    cop35_ASHP = calculate_dynamic_COP(tvl35, t_amb, quality_grade)
    copwater_ASHP = calculate_dynamic_COP(np.ones(shape=8760)*50, t_amb, quality_grade)

    # Calculate COPs for ground sourced heat pump
    cop75_GSHP = calculate_dynamic_COP(tvl75, t_ground, quality_grade)
    cop50_GSHP = calculate_dynamic_COP(tvl50, t_ground, quality_grade)
    cop35_GSHP = calculate_dynamic_COP(tvl35, t_ground, quality_grade)
    copwater_GSHP = calculate_dynamic_COP(np.ones(shape=8760)*50, t_ground, quality_grade)

    cops_aggregated = pd.DataFrame(columns=['COP35_air', 'COP50_air', 'COP75_air', 'COP35_ground', 'COP50_ground',
                                            'COP75_ground', 'COPwater_air', 'COPwater_ground','COP_mean' ])

    # Write COP-Series to DataFrame
    cops_aggregated['COP35_air'] = cop35_ASHP
    cops_aggregated['COP50_air'] = cop50_ASHP
    cops_aggregated['COP75_air'] = cop75_ASHP
    cops_aggregated['COP35_ground'] = cop35_GSHP
    cops_aggregated['COP50_ground'] = cop50_GSHP
    cops_aggregated['COP75_ground'] = cop75_GSHP
    cops_aggregated['COPwater_air'] = copwater_ASHP
    cops_aggregated['COPwater_ground'] = copwater_GSHP

    # Calculate mean COP and add it to DataFrame
    cop_air_mean = (cop35_ASHP + cop50_ASHP + cop75_ASHP) / 3
    cop_ground_mean = (cop35_GSHP + cop50_GSHP + cop75_GSHP) / 3
    cop_mean = share_ashp * cop_air_mean + share_gshp * cop_ground_mean
    cops_aggregated['COP_mean'] = cop_mean

    # Limit COP to 7
    limit = cops_aggregated >= 7
    artifact = cops_aggregated < 0
    cops_aggregated[limit] = 7
    cops_aggregated[artifact] = 7

    return cops_aggregated


def calculate_mixed_cops_by_nuts3(year, name, share_ashp=0.7, share_gshp=0.3, quality_grade=0.4):
    """
    Parameters
    ----------
    year: int
        Year of interest
    name: string
        Name of the analysed set
    share_ashp: Float
        Share of air sourced heat pumps
    share_gshp: Float
        Share of ground sourced heat pumps
    quality_grade : float
        Ambient temperature

    Returns: 2 DataFrames
        DataFrames containing mean COP series for each German NUTS3 region
    -------
    """

    fn_pattern = "mixed_cops_by_nuts3_{name}_{year}.csv".format(name=name, year=year)
    fn_pattern_water = "cops_by_nuts3_{name}_{year}_water.csv".format(name=name, year=year)
    fn = os.path.join(cfg.get("paths", "cop_precalc"), fn_pattern)
    fn_water = os.path.join(cfg.get("paths", "cop_precalc"), fn_pattern_water)

    if not os.path.isfile(fn):
        share_ashp = share_ashp
        share_gshp = share_gshp
        quality_grade = quality_grade
        t_ground = pd.Series(np.ones(8760)*10)

        outfile = os.path.join(cfg.get("paths", "cop_precalc"), "average_temp_by_nuts3_{year}.csv".format(year=year))

        if not os.path.isfile(outfile):

            # Load NUTS3-geometries
            nuts3 = data.database_shapes()
            nuts3 = nuts3.to_crs(crs=4326)

            # Get average temperature per NUTS3, coastdat only available until 2014
            coastdat.spatial_average_weather(year, nuts3, 'temp_air', 'deTemp', outfile=outfile)
            NUTS3_temp = pd.read_csv(outfile)
            NUTS3_temp.drop('Unnamed: 0', axis='columns', inplace=True)

        else:
            NUTS3_temp = pd.read_csv(outfile)
            NUTS3_temp.drop('Unnamed: 0', axis='columns', inplace=True)

        # Create empty DataFrames
        COP_NUTS3 = pd.DataFrame(index=pd.date_range('1/1/'+str(year), periods=8760, freq='H'),
                                 columns=NUTS3_temp.columns)
        COP_NUTS3_water = pd.DataFrame(index=pd.date_range('1/1/'+str(year), periods=8760, freq='H'),
                                       columns=NUTS3_temp.columns)

        # Loop through NUTS3-regions and calculate mixed COP for each region
        for r in COP_NUTS3.columns:
            tmp_cop = calculate_mixed_COPS_per_region(NUTS3_temp[r]-273.15, t_ground, quality_grade=quality_grade,
                                                      share_ashp=share_ashp, share_gshp=share_gshp)
            tmp_cop.set_index(COP_NUTS3.index, inplace=True)
            COP_NUTS3[r] = tmp_cop['COP_mean']
            COP_NUTS3_water[r] = tmp_cop['COPwater_air']* share_ashp + tmp_cop['COPwater_ground'] * share_gshp

        COP_NUTS3.to_csv(fn)
        COP_NUTS3_water.to_csv(fn_water)

    else:
        COP_NUTS3 = pd.read_csv(fn)
        COP_NUTS3_water = pd.read_csv(fn_water)

    return COP_NUTS3, COP_NUTS3_water


def aggregate_COP_by_region(regions, COP):
    mean_COP = pd.DataFrame(columns=regions.index)
    #mean_COP_water = pd.DataFrame(columns=regions.index)

    nuts3_list = demand_disaggregator.get_nutslist_for_regions(regions)

    for zone in regions.index:
        idx = nuts3_list.loc[zone]["nuts"]
        mean_COP[zone] = COP[idx].mean(axis=1)
        #mean_COP_water[zone] = COP_water[idx].mean(axis=1)

    return mean_COP


def get_hp_timeseries(heat_profile, cop, E_el):
    cop.index = heat_profile.index

    for Q_rated in range(0,10000000,1000):
        heat_hp = Q_rated * cop * heat_profile
        elc_hp = heat_hp / cop

        if elc_hp.sum() > E_el:
            break

    return elc_hp, heat_hp
