from process_nhd import condense_nhd

field_map_path = r"A:\opp-efed\hydro\Tables\nhd_map_nav.csv"
reach_table, _ = condense_nhd('07', field_map_path)

reach_table.to_csv("r07_condensed_nav_reach.csv")