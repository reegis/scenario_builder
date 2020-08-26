from emobpy import DataBase
import pandas as pd
import os
import numpy as np
from reegis import config as cfg
from matplotlib import pyplot as plt

def get_charging_profiles_from_database(path):
    """
    This function can be used to process results obtained with the library emobpy by DIW Berlin.
    It takes a path to data as input and returns the summed charging power.

    Parameters
    ----------
    path: String
        Path to a folder with stored driving, availability and charging profiles

    Returns: DataFrame
        Summed charging power for 4 different charging strategies
    -------
    """

    # Load profiles from Files
    manager = DataBase(path)
    manager.update()

    # Liste mit Availability Profilen
    keys_driving = [k for k, v in manager.db.items() if v['kind'] == 'driving']
    keys_availability = [k for k, v in manager.db.items() if v['kind'] == 'availability']
    keys_charging = [k for k, v in manager.db.items() if v['kind'] == 'charging']
    keys_immediate = [k for k, v in manager.db.items() if v['kind'] == 'charging' and v['option'] == 'immediate' ]
    keys_balanced = [k for k, v in manager.db.items() if v['kind'] == 'charging' and v['option'] == 'balanced' ]
    keys_23to8 = [k for k, v in manager.db.items() if v['kind'] == 'charging' and v['option'] == 'from_23_to_8_at_home']
    keys_0to24 = [k for k, v in manager.db.items() if v['kind'] == 'charging' and v['option'] == 'from_0_to_24_at_home']

    # Summenprofil für Fahrleistung in kmd
    driving_profiles = pd.DataFrame()
    for k in keys_driving:
        test = manager.db[k]["timeseries"]["consumption"]
        driving_profiles = pd.concat([driving_profiles, test], axis=1)

    #cum_profile = driving_profiles.sum(axis=1)


    # Summenprofil für Ladeleistung (immediate)
    ch_profiles_immediate = pd.DataFrame()
    for k in keys_immediate:
        tmp = manager.db[k]["timeseries"]["charge_grid"]
        ch_profiles_immediate = pd.concat([ch_profiles_immediate, tmp], axis=1)

    P_immediate = ch_profiles_immediate.sum(axis=1)


    # Summenprofil für Ladeleistung (balanced)
    ch_profiles_balanced = pd.DataFrame()
    for k in keys_balanced:
        tmp = manager.db[k]["timeseries"]["charge_grid"]
        ch_profiles_balanced = pd.concat([ch_profiles_balanced, tmp], axis=1)

    P_balanced = ch_profiles_balanced.sum(axis=1)


    # Summenprofil für Ladeleistung (23 to 8)
    ch_profiles_23to8 = pd.DataFrame()
    for k in keys_23to8:
        tmp = manager.db[k]["timeseries"]["charge_grid"]
        ch_profiles_23to8 = pd.concat([ch_profiles_23to8, tmp], axis=1)

    P_23to8 = ch_profiles_23to8.sum(axis=1)


    # Summenprofil für Ladeleistung (0 to 24)
    ch_profiles_0to24 = pd.DataFrame()
    for k in keys_0to24:
        tmp = manager.db[k]["timeseries"]["charge_grid"]
        ch_profiles_0to24 = pd.concat([ch_profiles_0to24, tmp], axis=1)

    P_0to24 = ch_profiles_0to24.sum(axis=1)

    P_sum = pd.concat([P_immediate, P_balanced, P_23to8, P_0to24], axis=1)
    P_sum.columns = ['immediate', 'balanced', '23to8', '0to24']

    return P_sum


def return_normalized_charging_series(df):
    """
    This function normalizes profiles so that the sum of the timeseries is 1. The profiles can then be scaled to
    a user defined energy consumption of BEV charging.

    Parameters
    ----------
    df: DataFrame
        Dataframe with 4 charging timereries

    Returns: DataFrame
        Normalized charging series
    -------
    """

    # Cut off initial charging
    df.iloc[0:48] = df.iloc[48:96].values
    # Cut off end charging to intial SoC
    df.iloc[len(df)-48:len(df)] = df.iloc[len(df)-96:len(df)-48].values
    idx = pd.DatetimeIndex(df.index, freq='30min')
    df.set_index(idx, inplace=True)
    p_immediate = df['immediate']
    p_balanced = df['balanced']
    p_23to8 = df['23to8']
    p_0to24 = df['0to24']

    # Resample to hourly values
    immediate_hourly = p_immediate.resample('H').sum()
    balanced_hourly = p_balanced.resample('H').sum()
    hourly_23to8 = p_23to8.resample('H').sum()
    hourly_0to24 = p_0to24.resample('H').sum()

    # Normalize Yearly energy use to 1
    immediate_norm = immediate_hourly * (1 / immediate_hourly.sum())
    balanced_norm = balanced_hourly * (1 / balanced_hourly.sum())
    norm_23to8 =  hourly_23to8  * (1 / hourly_23to8 .sum())
    norm_0to24 = hourly_0to24 * (1 / hourly_0to24.sum())

    P_sum_norm = pd.concat([immediate_norm, balanced_norm, norm_23to8, norm_0to24], axis=1)
    smaller_zero = P_sum_norm < 0
    P_sum_norm[smaller_zero] = 0

    for n in ['immediate', 'balanced', '23to8', '0to24']:
        inc_fac = 1 / P_sum_norm[n].sum()
        P_sum_norm[n] = P_sum_norm[n].multiply(inc_fac)

    return P_sum_norm


def return_sum_charging_power(path=None):
    """
    This function returns a DataFrame with summed charging power series. Prerequisite is the calculation of profiles
    with the library emobpy by DIW Berlin. If the function is run for the first time a path to data must be provided.

    Parameters
    ----------
    path: String
        Path to a directory containing at least one folder with charging power series files.

    Returns: DataFrame
        Summed charging profiles
    -------
    """
    fn = os.path.join(cfg.get("paths", "scenario_data"), 'sum_charging_power.csv')

    if not os.path.isfile(fn):
        os.chdir(path)
        dirs = os.listdir(os.getcwd())
        result_dict = dict.fromkeys(dirs)

        for dir in result_dict.keys():
            path = os.path.join(os.getcwd(), dir)
            result_dict[dir] = get_charging_profiles_from_database(path)

        charging_types = result_dict[dir].columns
        idx = result_dict[dir].index
        P_sum = pd.DataFrame(index=idx, columns=charging_types)
        len_series = len(result_dict[list(result_dict.keys())[0]]['immediate'])

        for ch_type in charging_types:
            sum_temp = pd.Series(np.zeros(shape=len_series), index=idx)

            for key in result_dict.keys():
                P_tmp = result_dict[key][ch_type]
                sum_temp = sum_temp.add(P_tmp, fill_value=0)

            P_sum[ch_type] = sum_temp

        P_sum.to_csv(fn)

    else:
        P_sum = pd.read_csv(fn)
        P_sum.set_index('Unnamed: 0', drop=True, inplace=True)

    return P_sum


def return_averaged_charging_series(weight_im=0.4, weight_bal=0.4, weight_night=0.2):
    cs = return_sum_charging_power()
    cs_norm = return_normalized_charging_series(cs)

    im = cs_norm["immediate"]
    bal = cs_norm["balanced"]
    night = cs_norm["23to8"]

    P_charge = weight_im * im + weight_bal * bal + weight_night * night

    return P_charge


def plot_charging_series_comparison(df, df_mean):
    fig, axs = plt.subplots(5)
    fig.suptitle('Charging strategy comparison')
    axs[0].plot(df["immediate"]), axs[0].set_title('Immediate')
    axs[1].plot(df["balanced"]), axs[1].set_title('balanced')
    axs[2].plot(df["0to24"]), axs[2].set_title('0to24')
    axs[3].plot(df["23to8"]), axs[3].set_title('23to8')
    axs[4].plot(df_mean), axs[4].set_title('Averaged series')
