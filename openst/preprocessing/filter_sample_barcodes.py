import argparse
import gzip
import os
import time
from collections.abc import Callable

import pandas as pd
from tqdm import tqdm


def get_filter_sample_barcodes_parser():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        add_help=False,
        description="filter the barcodes for the tiles which make up a capture area (a sample) e.g. deduplicate barcodes across the sample",
    )
    parser.add_argument(
        "--sample-barcode-files",
        type=str,
        nargs="+",
        required=True,
        help="path to the tile barcode files, from barcode_preprocessing",
    )
    parser.add_argument(
        "--out-path",
        type=str,
        required=True,
        help="folder where the output files will be generated, e.g. /path/to/this/sample/tiles",
    )

    return parser


def setup_filter_sample_barcodes_parser(parent_parser):
    """setup_filter_sample_barcodes_parser"""
    parser = parent_parser.add_parser(
        "filter_sample_barcodes",
        help="filter the barcodes for the tiles which make up a capture area (a sample) e.g. deduplicate barcodes across the sample",
        parents=[get_filter_sample_barcodes_parser()],
    )
    parser.set_defaults(func=_run_filter_sample_barcodes)

    return parser


def _run_filter_sample_barcodes(args):
    start_time = time.time()

    tiles = []
    for fpath in tqdm(args.sample_barcode_files, desc="Loading raw tiles"):
        tile = pd.read_csv(fpath, sep="\t")
        tile["fname"] = os.path.basename(fpath)
        tiles.append(tile)

    # remove duplicates barcodes
    all_tiles = pd.concat(tiles)
    all_tiles = all_tiles.drop_duplicates("cell_bc", keep=False) # do not keep any instances with duplicates

    os.makedirs(args.out_path, exist_ok=True)
    if len(os.listdir(args.out_path)) != 0:
        raise ValueError("Out path is not empty, please clean up or specify different out path")

    for fname, tile in tqdm(all_tiles.groupby("fname"), desc="Writing filtered tiles"):
        tile = tile.drop(columns="fname")
        tile.to_csv(os.path.join(args.out_path, fname), index=False, sep="\t")

    print(f"Finished in {round(time.time()-start_time, 2)} sec")


if __name__ == "__main__":
    args = get_filter_sample_barcodes_parser().parse_args()
    _run_filter_sample_barcodes(args)
