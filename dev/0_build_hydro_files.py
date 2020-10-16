"""
generate_hydro_files.py

Generate Navigator files, flow files, and lake files, which are used as inputs for the SAM model. These files
are created from the National Hydrography Dataset Plus (NHD Plus).
"""

# Import local modules and functions
from tools_hydro.tools import report
from utilities_hydro import fields_hydro as fields
import read_hydro
from nhd_tools.params_nhd import NavigatorBuilder

# TODO - use DivFrac to route percentages rather than just burning divergences

def extract_lakes(nhd_table):
    """
    Create a separate table of static waterbodies from master NHD table
    :param nhd_table: Input NHD table (df)
    :return: Table of parameters indexed to waterbodies (df)
    """
    fields.refresh()
    fields.expand('monthly')

    # Get a table of all lentic reaches, with the COMID of the reach and waterbody
    lentic_table = nhd_table[fields.fetch('lentic')].rename(columns={'q_ma': 'flow'})

    """ Identify the outlet reach corresponding to each reservoir """
    # Filter the reach table down to only outlet reaches by getting the minimum hydroseq for each wb_comid
    lentic_table = lentic_table.sort_values("hydroseq").groupby("wb_comid", as_index=False).first()
    del lentic_table['hydroseq']

    # Add mean annual flows
    flows = nhd_table[fields.fetch("monthly")].rename(columns={'q_ma': 'flow'})[['comid', 'flow']].drop_duplicates()
    lentic_table = lentic_table.merge(flows, on='comid', how='left')
    lentic_table = lentic_table.rename(columns={'comid': 'outlet_comid'})

    # Add reservoir volumes and calculate residnce time
    lentic_table['residence_time'] = lentic_table['volume'] / lentic_table.flow

    return lentic_table


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
    from nhd_tools.params_nhd import nhd_regions
    regions = nhd_regions
    regions = ['07']
    for region in regions:
        report(f"Generating hydro files for Region {region}", 1)
        report("Reading NHD...", 2)

        # Read and modify NHD Plus tabular data
        nhd_reach_table, nhd_lake_table = \
            read_hydro.condensed_nhd(region, overwrite=True)

        nhd_table = modify.nhd(nhd_table)

        report("Building navigator...", 2)
        # Build Navigator object and write to file
        nav = NavigatorBuilder(nhd_table)
        write.navigator(region, nav)

        report("Building flow file...", 2)
        # Extract flow data from NHD and write to file
        flows = extract_flows(nhd_table)
        write.flow_file(flows, region)

        report("Building lake file...", 2)
        # Extract lake data from NHD and write to file
        lakes = extract_lakes(nhd_table)
        write.lake_file(lakes, region)


main()
