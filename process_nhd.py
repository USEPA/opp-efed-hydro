import numpy as np
from nhd import vpus_nhd
from utilities_hydro import fields_hydro as fields


def process_nhd(nhd_table):
    """
    Modify data imported from the NHD Plus dataset. These modifications are chiefly
    to facilitate watershed delineation methods in generate_hydro_files.py.
    Remove rows in the condensed NHD table which signify a connection between a reach and a divergence.
    Retains only a single record for a given comid with the downstream divergence info for main divergence.
    :param nhd_table: Hydrographic data from NHD Plus (df)
    :return: Modified hydrographic data (df)
    """
    # Add the divergence and streamcalc of downstream reaches to each row
    downstream = nhd_table[['comid', 'divergence', 'streamcalc', 'fcode']]
    downstream.columns = ['tocomid'] + [f + "_ds" for f in downstream.columns.values[1:]]
    downstream = nhd_table[['comid', 'tocomid']].drop_duplicates().merge(
        downstream.drop_duplicates(), how='left', on='tocomid')

    # Where there is a divergence, select downstream reach with the highest streamcalc or lowest divergence
    downstream = downstream.sort_values('streamcalc_ds', ascending=False).sort_values('divergence_ds')
    downstream = downstream[~downstream.duplicated('comid')]

    nhd_table = nhd_table.merge(downstream, on=['comid', 'tocomid'], how='inner')

    # Calculate travel time, channel surface area, identify coastal reaches and
    # reaches draining outside a region as outlets and sever downstream connection
    # for outlet reaches

    nhd_table['tocomid'] = nhd_table.tocomid.fillna(-1)

    # Convert units
    nhd_table['length'] = nhd_table.pop('lengthkm') * 1000.  # km -> m
    for month in list(map(lambda x: str(x).zfill(2), range(1, 13))) + ['ma']:
        nhd_table["q_{}".format(month)] *= 2446.58  # cfs -> cmd
        nhd_table["v_{}".format(month)] *= 26334.7  # f/s -> md

    # Calculate travel time
    nhd_table["travel_time"] = nhd_table.length / nhd_table.v_ma

    # Calculate surface area
    stream_channel_a = 4.28
    stream_channel_b = 0.55
    cross_section = nhd_table.q_ma / nhd_table.v_ma
    nhd_table['surface_area'] = stream_channel_a * np.power(cross_section, stream_channel_b)

    # Indicate whether reaches are coastal
    nhd_table['coastal'] = np.int16(nhd_table.pop('fcode') == 56600)

    # Identify basin outlets
    nhd_table['outlet'] = 0

    # Identify all reaches that are a 'terminal path'. HydroSeq is used for Terminal Path ID in the NHD
    nhd_table.loc[nhd_table.hydroseq.isin(nhd_table.terminal_path), 'outlet'] = 1

    # Identify all reaches that empty into a reach outside the region
    nhd_table.loc[~nhd_table.tocomid.isin(nhd_table.comid) & (nhd_table.streamcalc > 0), 'outlet'] = 1

    # Designate coastal reaches as outlets. These don't need to be accumulated
    nhd_table.loc[nhd_table.coastal == 1, 'outlet'] = 1

    # Sever connection between outlet and downstream reaches
    nhd_table.loc[nhd_table.outlet == 1, 'tocomid'] = 0

    return nhd_table


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
            for month in list(range(1, 13)) + ['MA']:
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
