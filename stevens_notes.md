# Documentation
1. [openst](https://rajewsky-lab.github.io/openst/latest/)
1. [spacemake](https://spacemake.readthedocs.io/en/latest/)
1. [Flow cell layout and tile naming (page 73-74)](https://support.illumina.com/content/dam/illumina-support/documents/documentation/system_documentation/novaseq/1000000019358_16-novaseq-6000-system-guide.pdf#page=85)
1. [FastQ file format](https://help.basespace.illumina.com/files-used-by-basespace/fastq-files#format)

# Steps
1. install openst
    1. clone local fork (https://github.com/saluic/openst) - contains alot of fixes for the barcode preprocessing code
    1. create conda environment from `<openst_repo>/environment.yaml`
    1. install in editable mode
        ```
        pip install -e <openst_repo>
        ```
1. generate barcode coordinate files for each tile (tile = puck).
    ```
    openst barcode_preprocessing \
    --in-fastq fc/barcode_registration_R1.fastq.gz \
    --out-path fc/raw_tiles \
    --out-prefix "L3_tile_" \
    --out-suffix ".txt.gz" \
    --crop-seq 5:30 \
    --rev-comp
    ```
    1. **NB** make sure `--out-suffix` is `.txt` or `.txt.gz` (because of [this line](https://github.com/rajewsky-lab/spacemake/blob/50291f2bfba2df93b5a9c4fd397b6782c2a88e98/spacemake/snakemake/scripts/n_intersect_sequences.py#L213) - only hinted at in the openst docs)
1. post process the barcode files for a given sample
    1. a convenient way to do this is to make a folder of symlinks to the specific tiles for a sample
        ```
        mkdir adult_mouse_hippocampus/data/raw_tiles
        for F in {tile1,tile2,[...],tileN}; \
        do ln -s fc/raw_tiles/$F adult_mouse_hippocampus/data/raw_tiles/$F; \
        done
        ```
    1. run deduplication/filtering
        ```
        openst filter_sample_barcodes \
        --sample-barcode-files adult_mouse_hippocampus/data/raw_tiles/* \
        --out-path adult_mouse_hippocampus/data/tiles
        ```
1. install, initialize, and configure spacemake. spacemake processes fastqs into the expression matrix.
    1. spacemake >= `v0.7.4` ships with openst configurations ([PR #83](https://github.com/rajewsky-lab/spacemake/pull/83)), but this version is not on pypi yet. need to install from source, clone repo: https://github.com/rajewsky-lab/spacemake
    1. _**update**_ openst environment with `<spacemake_repo>/environment.yaml`
        ```
        conda env update --name openst --file environment.yaml
        ```
    1. install pulp == `v2.7.0` ([issue with snakemake dependency](https://github.com/snakemake/snakemake/issues/2607))
        ```
        pip install pulp==2.7.0
        ```
    1. [download Dropseq-tools version 2.5.1](https://github.com/broadinstitute/Drop-seq/releases/download/v2.5.1/Drop-seq_tools-2.5.1.zip). unzip somewhere
    1. [download genome & annotation files](https://www.gencodegenes.org)
    1. install in editable mode
        ```
        pip install -e <spacemake_repo>
        ```
    1. make a directory for spacemake runs. run all subsequent steps from within this directory.
    1. initialize spacemake 
        ```
        spacemake init \
        --dropseq_tools <unzipped_dropseq_tools>
        ```
        1. copies `config.yaml` and `puck_data` into the current directory. `puck_data/openst_coordinate_system.csv` has the coordinate offset for each tile relative to the flowcell, so tile coordinates can be translated to flowcell coordinates. replace `openst_coordinate_system.csv` as necessary. also disable hexagonal meshing...
    1. configure spacemake with the `species`. I used `GRCm39.genoma.fa` and `gencode.vM34.annotation.gtf` from gencode M34.
        ```
        spacemake config add_species \
        --name mouse \
        --sequence <genome.fa> \
        --annotation <annotation.gtf>
        ```
1. add samples to project and run spacemake. i.e. generate expression matrix.
    1. add samples to project
        ```
        spacemake projects add_sample \
        --project_id adult_mouse_hippocampus \
        --sample_id sample1 \
        --R1 adult_mouse_hippocampus/data/adult_mouse_hippocampus_R1_001.fastq.gz \
        --R2 adult_mouse_hippocampus/data/adult_mouse_hippocampus_R2_001.fastq.gz \
        --species mouse \
        --puck openst \
        --run_mode openst \
        --barcode_flavor openst \
        --puck_barcode_file adult_mouse_hippocampus/data/tiles/* \
        --map_strategy "STAR:genome:final"
        ```
    1. run spacemake
        ```
        spacemake run \
        --cores <n_cores>
        ```
1. stitch pucks together (`openst spatial_stitch`) to generate one expression matrix
    1. use anndata.obsm["spatial"] for capture-area coordinates (vs anndata.obs["x/y_pos"])