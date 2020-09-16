import os
import numpy as np
import pandas as pd
import xarray as xr
<<<<<<< HEAD
from paths_hydro import precip_path, ncep_path, weather_key_path, met_grid_path, crosswalk_path, ncep_key_path
=======
from paths_hydro import precip_path, ncep_path, weather_key_path, met_grid_path, crosswalk_path, ncep_key_path, \
    condensed_nhd_path, nhd_map_path

from utilities_hydro import fields_hydro as fields
>>>>>>> 4657bb242ca4fe4849977f07c96ac9b57d3dfaa3


def cdf(path):
    a = xr.open_dataset(path)
    return a.to_dataframe()


def crosswalk():
    return pd.read_csv(crosswalk_path)


def precip(year, bounds=None):
    # Read file and adjust longitude
    precip_table = cdf(precip_path.format(year)).reset_index()
    precip_table['lon'] -= 360
    precip_table['precip'] /= 10.  # mm -> cm
    # Filter out points by geography and completeness
    precip_table = precip_table.groupby(['lat', 'lon']).filter(lambda x: x['precip'].sum() > 0)
    if bounds is not None:
        precip_table = \
            precip_table[(precip_table.lat >= bounds[0]) & (precip_table.lat <= bounds[1]) &
                         (precip_table.lon >= bounds[2]) & (precip_table.lon <= bounds[3])]

    return precip_table


def ncep(year, ncep_vars, bounds=(20, 60, -130, -60), path=None):
    y_min, y_max, x_min, x_max = bounds
    path = ncep_path if path is None else path

    # Read and merge all NCEP data tables for the year
    table_paths = [path.format(var, year) for var in ncep_vars]
    full_table = None
    for table_path in table_paths:
        table = cdf(table_path).reset_index()
        table['lon'] -= 360
        table = table[(table.lat >= y_min) & (table.lat <= y_max) & (table.lon >= x_min) & (table.lon <= x_max)]
        if full_table is None:
            full_table = table
        else:
            full_table = full_table.merge(table, on=['lat', 'lon', 'time'])
    return full_table


def keyfile(type='weather'):
    path = weather_key_path if type == 'weather' else ncep_key_path
    data = np.load(path)
    points, years, header = data['points'], data['years'], data['header']
    start_date = np.datetime64('{}-01-01'.format(years[0]))
    end_date = np.datetime64('{}-12-31'.format(years[-1]))
    return start_date, end_date, header, points


def met_grid():
    return pd.read_csv(met_grid_path).set_index('weather_grid')


def nhd_map():
    return pd.read_csv(nhd_map_path)


def condensed_nhd(region):
    """
    Loads data from the NHD Plus dataset and combines into a single table.
    :param region: NHD Hydroregion (str)
    :return:
    """

    condensed_file = condensed_nhd_path.format(region)
    if not os.path.exists(condensed_file):
        condense_nhd(region, condensed_file)
    return pd.read_csv(condensed_file)


def condense_nhd(region):
    """
    This function extracts data from the native dbf files that are packaged with NHD
    and writes the data to .csv files with a similar name for faster reading in future
    runs
    :param region: NHD Plus Hydroregion (str)
    """

    def append(master, new_table):
        return new_table if master is None else master.merge(new_table, on='comid', how='outer')

    fields.refresh()
    table_map = fields.table_map('NHD')
    master_table = None
    for table_name, new_fields, old_fields in table_map:
        if table_name == 'EROM':
            for month in erom_months:
                rename = dict(zip(old_fields, [f"{new}_{month}" for new in new_fields]))
                del rename['comid']
                table_path = nhd_paths[table_name].format(vpus_nhd[region], region, month)
                table = dbf(table_path)[old_fields]
                table = table.rename(columns=rename)
                table['table_name'] = table_name
                master_table = append(master_table, table)
        else:
            rename = dict(zip(old_fields, new_fields))
            table_path = nhd_paths[table_name].format(vpus_nhd[region], region)
            table = dbf(table_path)
            table = table[old_fields].rename(columns=rename)
            table['table_name'] = table_name
            if table_name == 'PlusFlow':
                table = table[table.comid > 0]
            master_table = append(master_table, table)
    write.condensed_nhd(region, master_table)
