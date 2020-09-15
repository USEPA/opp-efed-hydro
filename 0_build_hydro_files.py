"""
generate_hydro_files.py

Generate Navigator files, flow files, and lake files, which are used as inputs for the SAM model. These files
are created from the National Hydrography Dataset Plus (NHD Plus).
"""
# Import builtin and standard libraries
import os
import numpy as np
import pandas as pd

# Import local modules and functions
import read_hydro
import write_hydro
import modify
from utilities_hydro import report, fields
from hydro.nhd import NavigatorBuilder


def extract_lakes(nhd_table):
    """
    Create a separate table of static waterbodies from master NHD table
    :param nhd_table: Input NHD table (df)
    :return: Table of parameters indexed to waterbodies (df)
    """
    # Get a table of all lentic reaches, with the COMID of the reach and waterbody
    nhd_table = nhd_table[["comid", "wb_comid", "hydroseq", "q_ma"]].rename(columns={'q_ma': 'flow'})

    """ Identify the outlet reach corresponding to each reservoir """
    # Filter the reach table down to only outlet reaches by getting the minimum hydroseq for each wb_comid
    nhd_table = nhd_table.sort_values("hydroseq").groupby("wb_comid", as_index=False).first()
    nhd_table = nhd_table.rename(columns={'comid': 'outlet_comid'})
    del nhd_table['hydroseq']

    # Read and reformat volume table
    volume_table = read_hydro.lake_volumes()

    # Join reservoir table with volumes
    nhd_table = nhd_table.merge(volume_table, on="wb_comid")
    nhd_table['residence_time'] = nhd_table['volume'] / nhd_table.flow

    return nhd_table


def extract_flows(nhd_table):
    """
    Extract modeled flows from master NHD table
    :param nhd_table: Input NHD data table (df)
    :return: Table of modeled flows from NHD (df)
    """
    fields.refresh()
    fields.expand('monthly')
    return nhd_table[fields.fetch('flow_file')]


def main():
    from parameters import nhd_regions

    for region in nhd_regions:
        report(f"Generating hydro files for Region {region}", 1)
        report("Reading NHD...", 2)

        # Read and modify NHD Plus tabular data
        nhd_table = read_hydro.nhd(region)
        nhd_table = modify.nhd(nhd_table)

        report("Building navigator...", 2)
        # Build Navigator object and write to file
        nav = NavigatorBuilder(nhd_table)
        write_hydro.navigator(region, nav)

        report("Building flow file...", 2)
        # Extract flow data from NHD and write to file
        flows = extract_flows(nhd_table)
        write_hydro.flow_file(flows, region)

        report("Building lake file...", 2)
        # Extract lake data from NHD and write to file
        lakes = extract_lakes(nhd_table)
        write_hydro.lake_file(lakes, region)


main()
