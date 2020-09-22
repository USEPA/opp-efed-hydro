import urllib
from nhd_tools.params_nhd import nhd_regions, vpus_nhd
import os
import re
from paths_nhd import zipped_dir

# TODO - capitalization (Hydrodem vs HydroDem), inconsistent paths
def pull_file(region, table, letteral, overwrite=False):
    def grab(url, local):
        try:
            urllib.request.urlretrieve(url, local)
            return True
        except urllib.error.HTTPError:
            False
    vpu = vpus_nhd[region]
    if letteral:
        super_region = re.match("(\d{2})", region).group(1)
        filename = f"NHDPlusV21_{vpu}_{region}_{super_region}{{}}_{table}"  # letter, trailing number
    else:
        filename = f"NHDPlusV21_{vpu}_{region}_{table}"
    local_path = os.path.join(zipped_dir, filename + ".7z")
    for letter in 'abcdefghijkl':
        l = local_path.format(letter) if letteral else local_path
        print(f"Searching for {l}...")
        for n in range(1, 20):
            if overwrite or not os.path.exists(l):
                root_a = f"https://s3.amazonaws.com/edap-nhdplus/NHDPlusV21/Data/NHDPlus{vpu}"
                root_b = f"https://s3.amazonaws.com/edap-nhdplus/NHDPlusV21/Data/NHDPlus{vpu}/NHDPlus{region}"
                for root in root_a, root_b:
                    trailing_num = str(n).zfill(2)
                    basename = filename.format(letter) if letteral else filename
                    file_url = f"{root}/{basename}_{trailing_num}.7z"
                    found = grab(file_url, l)
                    if found:
                        print(f"Acquired {l}")
                        return
            else:
                print(f"{l} already exists")
                return
    print(f"Unable to find {filename}")


files = \
    [["CatSeed", True],
     ["FdrFac", True],
     ["FdrNull", True],
     ["FilledAreas", True],
     ["HydroDem", True],
     ["NEDSnapshot", True],
     ["EROMExtension", False],
     ["NHDPlusAttributes", False],
     ["NHDPlusBurnComponents", False],
     ["NHDPlusCatchment", False],
     ["NHDSnapshotFGDB", False],
     ["NHDSnapshot", False],
     ["VPUAttributeExtension", False],
     ["VogelExtension", False],
     ["WBDSnapshot", False]]

for region in nhd_regions:
    for table, letteral in files:
        pull_file(region, table, letteral)
