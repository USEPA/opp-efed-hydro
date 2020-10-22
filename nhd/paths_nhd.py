import os

local_run = True

if local_run:
    global_dir = r"E:\opp-efed-data\global"
    local_dir = r"A:\opp-efed\hydro"
else:
    global_dir = "/src/app-data/sampreprocessed"
    local_dir = os.path.realpath(__file__)

# Tables
table_dir = os.path.join(local_dir, "Tables")
fields_and_qc_path = os.path.join(table_dir, "fields_and_qc.csv")
nhd_map_path = os.path.join(table_dir, "nhd_map.csv")

# HydroFiles
navigator_map_path = os.path.join(table_dir, "nhd_map_nav.csv")
navigator_path = os.path.join(global_dir, "NavigatorFiles", "nav{}.npz")  # region

# Path containing NHD Plus dataset
nhd_dir = os.path.join(global_dir, "NHDPlusV21")
nhd_region_dir = os.path.join(nhd_dir, "NHDPlus{}", "NHDPlus{}")  # vpu, region
catchment_path = os.path.join(nhd_region_dir, "NHDPlusCatchment", "Catchment.shp")