class NavigatorBuilder(object):
    def __init__(self, nhd_table):
        """
        Initializes the creation of a Navigator object, which is used for rapid
        delineation of watersheds using NHD Plus catchments.
        :param nhd_table: Table of stream reach parameters from NHD Plus (df)
        """
        report("Unpacking NHD...", 2)
        nodes, times, dists, outlets, self.conversion = self.unpack_nhd(nhd_table)

        report("Tracing upstream...", 2)
        # paths, times = self.upstream_trace(nodes, outlets, times)
        # TODO - add clean capability to cumulatively trace any attribute (e.g time, distance)
        paths, times, dists = self.rapid_trace(nodes, outlets, times, dists, self.conversion)

        report("Mapping paths...", 2)
        self.path_map = self.map_paths(paths)

        report("Collapsing array...", 2)
        self.paths, self.times, self.length, self.start_cols = \
            self.collapse_array(paths, times, dists)

    @staticmethod
    def unpack_nhd(nhd_table):
        """
        Extract nodes, times, distances, and outlets from NHD table
        :param nhd_table: Table of NHD Plus parameters (df)
        :return: Modified NHD table with selected fields
        """
        # Extract nodes and travel times
        nodes = nhd_table[['tocomid', 'comid']]
        times = nhd_table['travel_time'].values
        dists = nhd_table['length'].values

        convert = pd.Series(np.arange(nhd_table.comid.size), index=nhd_table.comid.values)
        nodes = nodes.apply(lambda row: row.map(convert)).fillna(-1).astype(np.int32)

        # Extract outlets from aliased nodes
        outlets = nodes.comid[nhd_table.outlet == 1].values

        # Create a lookup key to convert aliases back to comids
        conversion_array = convert.sort_values().index.values

        # Return nodes, travel times, outlets, and conversion
        return nodes.values, times, dists, outlets, conversion_array

    @staticmethod
    def map_paths(paths):
        """
        Get the starting row and column for each path in the path array
        :param paths: Path array (np.array)
        :return:
        """

        column_numbers = np.tile(np.arange(paths.shape[1]) + 1, (paths.shape[0], 1)) * (paths > 0)
        path_begins = np.argmax(column_numbers > 0, axis=1)
        max_reach = np.max(paths)
        path_map = np.zeros((max_reach + 1, 3))
        n_paths = paths.shape[0]
        for i, path in enumerate(paths):
            for j, val in enumerate(path):
                if val:
                    if i == n_paths:
                        end_row = 0
                    else:
                        next_row = (path_begins[i + 1:] <= j)
                        if next_row.any():
                            end_row = np.argmax(next_row)
                        else:
                            end_row = n_paths - i - 1
                    values = np.array([i, i + end_row + 1, j])
                    path_map[val] = values

        return path_map

    @staticmethod
    def collapse_array(paths, times, lengths):
        """
        Reduce the size of input arrays by truncating at the path length
        :param paths: Array with node IDs (np.array)
        :param times: Array with reach travel times (np.array)
        :param lengths: Array with reach lengths (np.array)
        :return:
        """
        out_paths = []
        out_times = []
        out_lengths = []
        path_starts = []
        for i, row in enumerate(paths):
            active_path = (row > 0)
            path_starts.append(np.argmax(active_path))
            out_paths.append(row[active_path])
            out_times.append(times[i][active_path])
            out_lengths.append(lengths[i][active_path])
        return map(np.array, (out_paths, out_times, out_lengths, path_starts))

    @staticmethod
    def rapid_trace(nodes, outlets, times, dists, conversion, max_length=3000, max_paths=500000):
        """
        Trace upstream through the NHD Plus hydrography network and record paths,
        times, and lengths of traversals.
        :param nodes: Array of to-from node pairs (np.array)
        :param outlets: Array of outlet nodes (np.array)
        :param times: Array of travel times corresponding to nodes (np.array)
        :param dists: Array of flow lengths corresponding to nodes (np.array)
        :param conversion: Array to interpret node aliases (np.array)
        :param max_length: Maximum length of flow path (int)
        :param max_paths: Maximum number of flow paths (int)
        :return:
        """
        # Output arrays
        all_paths = np.zeros((max_paths, max_length), dtype=np.int32)
        all_times = np.zeros((max_paths, max_length), dtype=np.float32)
        all_dists = np.zeros((max_paths, max_length), dtype=np.float32)

        # Bounds
        path_cursor = 0
        longest_path = 0

        progress = 0  # Master counter, counts how many reaches have been processed
        already = set()  # This is diagnostic - the traversal shouldn't hit the same reach more than once

        # Iterate through each outlet
        for i in np.arange(outlets.size):
            start_node = outlets[i]

            # Reset everything except the master. Trace is done separately for each outlet
            queue = np.zeros((nodes.shape[0], 2), dtype=np.int32)
            active_reach = np.zeros(max_length, dtype=np.int32)
            active_times = np.zeros(max_length, dtype=np.float32)
            active_dists = np.zeros(max_length, dtype=np.float32)

            # Cursors
            start_cursor = 0
            queue_cursor = 0
            active_reach_cursor = 0
            active_node = start_node

            # Traverse upstream from the outlet.
            while True:
                # Report progress
                progress += 1
                if not progress % 10000:
                    report(progress, 3)
                upstream = nodes[nodes[:, 0] == active_node]

                # Check to make sure active node hasn't already been passed
                l1 = len(already)
                already.add(conversion[active_node])
                if len(already) == l1:
                    report("Loop at reach {}".format(conversion[active_node]))
                    exit()

                # Add the active node and time to the active path arrays
                active_reach[active_reach_cursor] = active_node
                active_times[active_reach_cursor] = times[active_node]
                active_dists[active_reach_cursor] = dists[active_node]

                # Advance the cursor and determine if a longest path has been set
                active_reach_cursor += 1
                if active_reach_cursor > longest_path:
                    longest_path = active_reach_cursor

                # If there is another reach upstream, continue to advance upstream
                if upstream.size:
                    active_node = upstream[0][1]
                    for j in range(1, upstream.shape[0]):
                        queue[queue_cursor] = upstream[j]
                        queue_cursor += 1

                # If not, write the active path arrays into the output matrices
                else:
                    all_paths[path_cursor, start_cursor:] = active_reach[start_cursor:]
                    all_times[path_cursor] = np.cumsum(active_times) * (all_paths[path_cursor] > 0)
                    all_dists[path_cursor] = np.cumsum(active_dists) * (all_paths[path_cursor] > 0)
                    queue_cursor -= 1
                    path_cursor += 1
                    last_node, active_node = queue[queue_cursor]
                    if last_node == 0 and active_node == 0:
                        break
                    for j in range(active_reach.size):
                        if active_reach[j] == last_node:
                            active_reach_cursor = j + 1
                            break
                    start_cursor = active_reach_cursor
                    active_reach[active_reach_cursor:] = 0.
                    active_times[active_reach_cursor:] = 0.
                    active_dists[active_reach_cursor:] = 0.

        return all_paths[:path_cursor, :longest_path], \
               all_times[:path_cursor, :longest_path], \
               all_dists[:path_cursor, :longest_path]


class Navigator(object):
    def __init__(self, region_id, upstream_path):
        self.file = upstream_path.format(region_id, 'nav', 'npz')
        self.paths, self.times, self.map, self.alias_to_reach, self.reach_to_alias = self.load()
        self.reach_ids = set(self.reach_to_alias.keys())

    def load(self):
        assert os.path.isfile(self.file), "Upstream file {} not found".format(self.file)
        data = np.load(self.file, mmap_mode='r', allow_pickle=True)
        conversion_array = data['alias_index']
        reverse_conversion = dict(zip(conversion_array, np.arange(conversion_array.size)))
        return data['paths'], data['time'], data['path_map'], conversion_array, reverse_conversion

    def upstream_watershed(self, reach_id, mode='reach', return_times=False, return_warning=False, verbose=False):

        def unpack(array):
            first_row = [array[start_row][start_col:]]
            remaining_rows = list(array[start_row + 1:end_row])
            return np.concatenate(first_row + remaining_rows)

        # Look up reach ID and fetch address from pstream object
        reach = reach_id if mode == 'alias' else self.reach_to_alias.get(reach_id)
        reaches, adjusted_times, warning = np.array([]), np.array([]), None
        try:
            start_row, end_row, col = map(int, self.map[reach])
            start_col = list(self.paths[start_row]).index(reach)
        except TypeError:
            warning = "Reach {} not found in region".format(reach)
        except ValueError:
            warning = "{} not in upstream lookup".format(reach)
        else:
            # Fetch upstream reaches and times
            aliases = unpack(self.paths)
            reaches = aliases if mode == 'alias' else np.int32(self.alias_to_reach[aliases])

        # Determine which output to deliver
        output = [reaches]
        if return_times:
            times = unpack(self.times)
            adjusted_times = np.int32(times - self.times[start_row][start_col])
            output.append(adjusted_times)
        if return_warning:
            output.append(warning)
        if verbose and warning is not None:
            report(warning, warn=1)
        return output[0] if len(output) == 1 else output


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
    volume_table = read.lake_volumes()

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


def nhd(region):
    """
    Loads data from the NHD Plus dataset and combines into a single table.
    :param region: NHD Hydroregion (str)
    :return:
    """

    fields.refresh()
    condensed_file = condensed_nhd_path.format(region)
    if not os.path.exists(condensed_file):
        condense_nhd(region, condensed_file)
    return pd.read_csv(condensed_file)

def nhd(nhd_table):
    """
    Modify data imported from the NHD Plus dataset. These modifications are chiefly
    to facilitate watershed delination methods in generate_hydro_files.py.
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
