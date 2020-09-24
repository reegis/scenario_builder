import pandas as pd
from reegis import geometries as geo_reegis
from deflex import geometries as geo_deflex
from reegis import land_availability_glaes, demand_disaggregator
from disaggregator import data

def get_cost_emission_scenario_data(path_to_data):

    commodity_sources = dict.fromkeys({'StatusQuo', 'NEP2030', 'AllElectric', 'SynFuel'})

    for n in commodity_sources.keys():
        cost_data = pd.read_excel(path_to_data, n)
        cost_data.set_index('Unnamed: 0', drop=True, inplace=True)
        cost_data.drop(['emission_cost', 'total_cost'], inplace=True)
        commodity_sources[n] = cost_data

    return commodity_sources


def return_normalized_domestic_profiles(regions, df):

    test = df.groupby(level=[0,2], axis=1).sum()
    profile_domestic = pd.DataFrame(index=test.index, columns=regions.index[0:18] )

    for reg in regions.index[0:18]:
        profile_domestic[reg] = test[reg]["domestic"] + test[reg]["retail"]

    profile_domestic = profile_domestic.div(profile_domestic.sum())

    return profile_domestic


def return_normalized_industrial_profiles(regions, df):

    test = df.groupby(level=[0, 2], axis=1).sum()
    profile_domestic = pd.DataFrame(index=test.index, columns=regions.index[0:18])

    for reg in regions.index[0:18]:
        profile_domestic[reg] = test[reg]["industrial"]

    profile_industrial = profile_domestic.div(profile_domestic.sum())

    return profile_industrial


def transform_NEP_capacities_to_de21(path_to_NEP_capacities):
    de21 = geo_deflex.deflex_regions(rmap='de21')
    fed_states = geo_reegis.get_federal_states_polygon()
    nuts3_index = data.database_shapes().index

    # Load NEP capacities
    NEP2030_capacity = pd.read_excel(path_to_NEP_capacities)
    NEP2030_capacity.set_index('fedstate', drop=True, inplace=True)
    NEP2030_capacity = NEP2030_capacity.multiply(1e3)

    #Fetch GLAES RES capacities and compare to NEP data
    glaes_capacity = land_availability_glaes.aggregate_capacity_by_region(fed_states)
    compare_RES = pd.concat([glaes_capacity, NEP2030_capacity['onshore'], NEP2030_capacity['offshore'],
                      NEP2030_capacity['solar pv']], axis=1)

    compare_RES.drop(['N0', 'N1', 'O0', 'P0'], axis=0, inplace=True)

    scaling_wind = compare_RES['onshore'] / compare_RES['P_wind']
    scaling_pv = compare_RES['solar pv'] / compare_RES['P_pv']

    mapped_nuts = demand_disaggregator.get_nutslist_for_regions(fed_states)
    res_capacity_nuts3 = land_availability_glaes.get_pv_wind_capacity_potential_by_nuts3()

    # Zuordnung der installierten Leistungen zu den jeweiligen Landkreisen
    P_NEP_nuts3 = pd.DataFrame(index=nuts3_index, columns=['onshore', 'pv'])

    for zone in compare_RES.index:
        region_pick = mapped_nuts.loc[zone]
        for nuts3 in region_pick.iloc[0]:
            P_NEP_nuts3.loc[nuts3]['onshore'] = res_capacity_nuts3['P_wind'][nuts3] * scaling_wind[zone]
            P_NEP_nuts3.loc[nuts3]['pv'] = res_capacity_nuts3['P_pv'][nuts3] * scaling_pv[zone]

    NEP_capacity_de21 = pd.DataFrame(
        index=de21.index, columns=["P_wind", "P_pv"]
    )
    nuts3_list_de21 = demand_disaggregator.get_nutslist_for_regions(de21)

    for zone in de21.index:
        idx = nuts3_list_de21.loc[zone]["nuts"]
        NEP_capacity_de21.loc[zone]["P_wind"] = P_NEP_nuts3["onshore"][idx].sum()
        NEP_capacity_de21.loc[zone]["P_pv"] = P_NEP_nuts3["pv"][idx].sum()

    return NEP_capacity_de21


def load_NEP_pp_capacities(path_to_NEP_capacities):
    NEP2030_capacity = pd.read_excel(path_to_NEP_capacities)
    NEP2030_capacity.set_index('fedstate', drop=True, inplace=True)
    NEP2030_capacity = NEP2030_capacity.multiply(1e3)

    # Select pp capacities
    pp_capacities = pd.concat([NEP2030_capacity['lignite'], NEP2030_capacity['hard coal'], NEP2030_capacity['oil'],
                             NEP2030_capacity['natural gas'], NEP2030_capacity['biomass'],
                             NEP2030_capacity['other']], axis=1)

    return pp_capacities


def aggregate_by_region(regions, data):
    out_df = pd.Series(index=regions.index)
    nuts3_list = demand_disaggregator.get_nutslist_for_regions(regions)

    for zone in regions.index:
        idx = nuts3_list.loc[zone]["nuts"]
        out_df.loc[zone] = data[idx].sum()

    return out_df

