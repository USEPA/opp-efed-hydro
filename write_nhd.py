import numpy as np
import os


def create_dir(outfile):
    directory = os.path.dirname(outfile)
    if not os.path.exists(directory):
        os.makedirs(directory)


def navigator_file(nav_dir, region, paths, times, length, path_map, conversion):
    create_dir(nav_dir)
    outfile = os.path.join(nav_dir, f"nav_{region}.npz")
    np.savez_compressed(outfile, paths=paths, time=times, length=length, path_map=path_map,
                        alias_index=conversion)


def condensed_nhd(out_dir, run_id, region, reach_table, lake_table=None):
    create_dir(out_dir)
    for feature_type, table in (('reach', reach_table), ('waterbody', lake_table)):
        if table is not None:
            out_path = out_dir.format(run_id, region, feature_type)
            table.to_csv(out_path, index=None)
