import argparse
import gzip
import os
import time
from collections.abc import Callable

import pandas as pd
from tqdm import tqdm


def get_barcode_preprocessing_parser():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        add_help=False,
        description="convert fastq files into spatial barcode files (sequence and coordinates)",
    )
    parser.add_argument("--in-fastq", type=str, required=True, help="path to the fastq file")
    parser.add_argument(
        "--out-path",
        type=str,
        required=True,
        help="folder where the output files will be generated",
    )
    parser.add_argument(
        "--out-suffix",
        type=str,
        required=True,
        help="where to write the output file. it works as the suffix when multiple tiles are generated",
    )
    parser.add_argument(
        "--out-prefix",
        type=str,
        default="",
        help="where to write the output file. it works as the prefix when multiple tiles are generated",
    )
    parser.add_argument(
        "--crop-seq",
        type=str,
        default=":",
        help="crop the input sequence, should be a valid python slice",
    )
    parser.add_argument(
        "--rev-comp",
        action="store_true",
        help="applies reverse complementary after sequence cropping",
    )

    return parser


def setup_barcode_preprocessing_parser(parent_parser):
    """setup_barcode_preprocessing_parser"""
    parser = parent_parser.add_parser(
        "barcode_preprocessing",
        help="convert fastq files into spatial barcode files (sequence and coordinates)",
        parents=[get_barcode_preprocessing_parser()],
    )
    parser.set_defaults(func=_run_barcode_preprocessing)

    return parser


tab = str.maketrans("ACTG", "TGAC")


def reverse_complement_table(seq):
    return seq.translate(tab)[::-1]


def get_tile_info(seq_id: str) -> tuple[int, int, int, int]:
    """
    Extracts lane, tile, x-coord, and y-coord from sequence ID line.
    See: https://help.basespace.illumina.com/files-used-by-basespace/fastq-files
    """
    info = seq_id.split(" ")[0].split(":")[-4:]
    return tuple(int(x) for x in info)


written_files = set()


def append_barcodes_to_disk(
    *,  # enforce kwargs
    lane: int,
    tile: int,
    barcodes: list[str],
    xs: list[int],
    ys: list[int],
    out_path: str,
    out_prefix: str,
    out_suffix: str,
) -> None:
    # fname = f"{lane}_{tile}"
    fname = f"{tile}"
    fpath = os.path.join(out_path, f"{out_prefix}{fname}{out_suffix}")
    df = pd.DataFrame({"cell_bc": barcodes, "xcoord": xs, "ycoord": ys})

    exists = os.path.exists(fpath)
    if exists and fpath not in written_files:
        raise FileExistsError(f"{fpath} already exists prior to this run")
    written_files.add(fpath)

    df.to_csv(
        fpath,
        index=False,
        header=not exists,
        sep="\t",
        mode="a",
    )


def process_multiple_unsorted_tiles(
    *,  # enforce kwargs
    in_fastq: str,
    out_path: str,
    out_prefix: str,
    out_suffix: str,
    sequence_preprocessor: Callable[[str], str] | None = None,
):
    if sequence_preprocessor is None:
        sequence_preprocessor = lambda x: x
    curr_tile = None
    barcodes, xs, ys = [[], [], []]
    fastq_size = os.stat(in_fastq).st_size  # in compressed bytes
    last_byte = 0
    with gzip.open(in_fastq, "rt") as f, tqdm(total=fastq_size, unit="B") as pbar:
        for i, seq_id in enumerate(f):
            seq = f.readline()
            _ = f.readline()
            _ = f.readline()
            lane, tile, x, y = get_tile_info(seq_id)
            next_tile = (lane, tile)
            barcode = sequence_preprocessor(seq)
            if next_tile != curr_tile and curr_tile is not None:
                append_barcodes_to_disk(
                    lane=curr_tile[0],
                    tile=curr_tile[1],
                    barcodes=barcodes,
                    xs=xs,
                    ys=ys,
                    out_path=out_path,
                    out_prefix=out_prefix,
                    out_suffix=out_suffix,
                )
                barcodes, xs, ys = [[], [], []]
            curr_tile = next_tile
            barcodes.append(barcode)
            xs.append(x)
            ys.append(y)
            if i % 10_000:
                curr_byte = f.buffer.fileobj.tell()
                pbar.update(curr_byte - last_byte)
                last_byte = curr_byte
    append_barcodes_to_disk(
        lane=curr_tile[0],
        tile=curr_tile[1],
        barcodes=barcodes,
        xs=xs,
        ys=ys,
        out_path=out_path,
        out_prefix=out_prefix,
        out_suffix=out_suffix,
    )


def _run_barcode_preprocessing(args):
    crop_seq_slice = slice(
        *[{True: lambda n: None, False: int}[x == ""](x) for x in (args.crop_seq.split(":") + ["", "", ""])[:3]]
    )

    def sequence_preprocessor(sequence: str) -> str:
        # slice --> translate --> reverse
        sequence = sequence.strip()
        sequence = sequence[crop_seq_slice].strip()
        if args.rev_comp:
            sequence = reverse_complement_table(sequence)
        return sequence

    start_time = time.time()

    process_multiple_unsorted_tiles(
        in_fastq=args.in_fastq,
        out_path=args.out_path,
        out_prefix=args.out_prefix,
        out_suffix=args.out_suffix,
        sequence_preprocessor=sequence_preprocessor,
    )

    print(f"Finished in {round(time.time()-start_time, 2)} sec")


if __name__ == "__main__":
    args = get_barcode_preprocessing_parser().parse_args()
    _run_barcode_preprocessing(args)
