import os

global_dir = r"J:\opp-efed-data\global"
local_dir = r"J:\opp-efed-data\hydro"

# Weather
weather_dir = os.path.join(local_dir, "weather")
weather_grid_file = os.path.join(global_dir, "WeatherFiles", "weather_stations_highres_thiessens_US_alb",
                         "weather_stations_highres_thiessens_US_alb.shp")


# HydroFiles
hydrofile_dir = os.path.join(local_dir, "HydroFiles")
nav_path = os.path.join(hydrofile_dir, "region_{}_nav.npz")

# Path containing NHD Plus dataset
nhd_dir = os.path.join(global_dir, "NHDPlusV21")
catchment_path = os.path.join(nhd_dir, "NHDPlus{}", "NHDPlus{}", "NHDPlusCatchment", "Catchment.shp")

# Inputs
ncep_path = os.path.join(global_dir, "MetDataNew", "{}.gauss.{}.nc")  # var, year
precip_path = os.path.join(global_dir, "MetData", "precip.V1.0.{}.nc")  # year
met_grid_path = os.path.join(weather_dir, "grid", "met_stations.csv")
crosswalk_path = os.path.join(local_dir, "Tables", "station_xwalk.csv")

# Intermediate
scratch_path = os.path.join(weather_dir, "temp")
ncep_table_path = os.path.join(scratch_path, "ncep_{}.csv")  # year
condensed_nhd_path = os.path.join(local_dir, "CondensedNHD", 'nhd{}.csv')  # region

# Outputs
weather_array_path = os.path.join(weather_dir, "weather_array.dat")
ncep_array_path = os.path.join(weather_dir, "ncep_array.dat")
weather_key_path = os.path.join(weather_dir, "weather_key.npz")
ncep_key_path = os.path.join(weather_dir, "ncep_key.npz")
