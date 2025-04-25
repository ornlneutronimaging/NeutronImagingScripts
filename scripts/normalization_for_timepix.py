import argparse
import logging
import os
import numpy as np

from neutronimaging.normalization_for_tof import normalization_with_list_of_runs
from neutronimaging.util import retrieve_root_nexus_full_path


LOG_PATH = "/SNS/VENUS/shared/log/"
LOAD_DTYPE = np.uint16

PROTON_CHARGE_TOLERANCE = 0.1

file_name, ext = os.path.splitext(os.path.basename(__file__))
log_file_name = os.path.join(LOG_PATH, f"{file_name}.log")
logging.basicConfig(filename=log_file_name,
                    filemode='w',
                    format='[%(levelname)s] - %(asctime)s - %(message)s',
                    level=logging.INFO)
logging.info(f"*** Starting a new script {file_name} ***")


class DataType:
    sample = "sample"
    ob = "ob"
    unknown = "unknown"


class MasterDictKeys:
    frame_number = "frame_number"
    proton_charge = "proton_charge"
    matching_ob = "matching_ob"
    list_tif = "list_tif"
    data = "data"
    nexus_path = "nexus_path"
    data_path = "data_path"
    shutter_counts = "shutter_counts"
    list_spectra = "list_spectra"
    

class StatusMetadata:
    all_shutter_counts_found = True
    all_spectra_found = True
    all_proton_charge_found = True


if __name__ == '__main__':

    # sample_master_dict = {'run_number': {'nexus_path': 'path', 'frame_number': 'value', 'proton_charge': 'value', 'matching_ob': []}}

    parser = argparse.ArgumentParser(description="Normalized Timepix data with shutter counts and proton charge",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("--sample", type=str, nargs=1, help="Full path to sample run number")
    parser.add_argument("--ob", type=str, nargs=1, help="Full path to the ob run number")
    parser.add_argument("--output", type=str, nargs=1, help="Path to the output folder", default="./")
    
    args = parser.parse_args()
    logging.info(f"{args = }")

    try:
        sample_run_number = args.sample[0]
        if not os.path.exists(sample_run_number):
            logging.info(f"sample run number {sample_run_number} does not exist!")
            raise FileNotFoundError(f"Folder {sample_run_number} does not exist!")
        else:
            logging.info(f"sample run number {sample_run_number} located!")

    except (TypeError, FileNotFoundError):
        print("\n *** INPUT ERROR of sample run number! ***\n")
        print(parser.print_help())
        exit()
    
    try:
        ob_run_number = args.ob[0]
        if not os.path.exists(ob_run_number):
            logging.info(f"open beam run number {ob_run_number} does not exist!")
            raise FileNotFoundError(f"Folder {ob_run_number} does not exist!")
        else:
            logging.info(f"open beam run number {ob_run_number} located!")

    except (TypeError, FileNotFoundError):
        print("\n *** INPUT ERROR of ob folder! ***\n")
        print(parser.print_help())
        exit()

    try:
        output_folder = args.output[0]
    
    except TypeError:
        print("\n *** INPUT ERROR of output folder! ***\n")
        print(parser.print_help())
        exit()

    normalization_with_list_of_runs(sample_run_numbers=[sample_run_number],
                                    ob_run_numbers=[ob_run_number], 
                                    output_folder=output_folder, 
                                    nexus_path=retrieve_root_nexus_full_path(sample_run_number),
                                    verbose=False)

    # normalization(sample_folder=sample_folder, ob_folder=ob_folder, output_folder=output_folder)

    print(f"Normalization is done! Check the log file {log_file_name} for more details!")
    print(f"Exported data to {output_folder}")

    # sample = /SNS/VENUS/IPTS-34808/shared/autoreduce/mcp/November17_Sample6_UA_H_Batteries_1_5_Angs_min_30Hz_5C
    # ob = /SNS/VENUS/IPTS-34808/shared/autoreduce/mcp/November17_OB_for_UA_H_Batteries_1_5_Angs_min_30Hz_5C

    # full command to use to test code
    
    # source /opt/anaconda/etc/profile.d/conda.sh
    # conda activate ImagingReduction
    # > python normalization_for_timepix.py --sample /SNS/VENUS/IPTS-34808/shared/autoreduce/mcp/November17_Sample6_UA_H_Batteries_1_5_Angs_min_30Hz_5C --ob /SNS/VENUS/IPTS-34808/shared/autoreduce/mcp/November17_OB_for_UA_H_Batteries_1_5_Angs_min_30Hz_5C --output /SNS/VENUS/IPTS-34808/shared/processed_data/jean_test