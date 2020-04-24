import os

root_dir = r"J:\NationalData"
weather_dir = r"J:\opp-efed-data\hydro\weather"
local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))

# Inputs
ncep_path = os.path.join(root_dir, "MetData", "{}.gauss.{}.nc")  # var, year
precip_path = os.path.join(root_dir, "MetData", "precip.V1.0.{}.nc")  # year
met_grid_path = os.path.join(weather_dir, "grid", "met_stations.csv")
crosswalk_path = os.path.join(local_dir, "Tables", "station_xwalk.csv")

# Intermediate
scratch_path = os.path.join(weather_dir, "temp")
ncep_table_path = os.path.join(scratch_path, "ncep_{}.csv")  # year

# Outputs
weather_array_path = os.path.join(weather_dir, "weather_array.dat")
weather_key_path = os.path.join(weather_dir, "weather_key.npz")
