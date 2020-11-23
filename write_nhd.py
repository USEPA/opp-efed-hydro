from hydro.paths_nhd import navigator_path
import numpy as np
import os


def create_dir(outfile):
    directory = os.path.dirname(outfile)
    if not os.path.exists(directory):
        os.makedirs(directory)


def navigator_file(region, paths, times, length, path_map, conversion):
    create_dir(navigator_path)
    outfile = navigator_path.format(region)
    np.savez_compressed(outfile, paths=paths, time=times, length=length, path_map=path_map,
                        alias_index=conversion)
