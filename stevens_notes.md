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
1. generate barcode coordinate files for each tile (tile = puck)
    ```
    openst barcode_preprocessing \
    --in-fastq data/adult_mouse_hippocampus/adult_mouse_hippocampus_R1_001.fastq.gz \
    --out-path tile-barcode-coords/adult_mouse_hippocampus \
    --out-prefix "" \
    --out-suffix ".txt" \
    --crop-seq 2:27
    ```
    1. **NB** make sure `--out-suffix` is `.txt` (because of [this line](https://github.com/rajewsky-lab/spacemake/blob/50291f2bfba2df93b5a9c4fd397b6782c2a88e98/spacemake/snakemake/scripts/n_intersect_sequences.py#L213) - only hinted at in the openst docs)
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
    1. install in editable mode
        ```
        pip install -e <spacemake_repo>
        ```
    1. make a directory for spacemake runs. run all subsequent steps from within this directory.
    1. initialize spacemake and download genome & annotation files
        ```
        spacemake init \
        --dropseq_tools <unzipped_dropseq_tools> \
        --download_species
        ```
        1. copies `config.yaml` and `puck_data` into the current directory. `puck_data/openst_coordinate_system.csv` has the coordinate offset for each tile so tile coordinates can be translated as flowcell coordinates. (on the [data download page](https://rajewsky-lab.github.io/openst/latest/examples/datasets/#barcode-spatial-coordinates-and-coordinate-systems), a little unclear how `fc_1` and `fc_2` coordinate files differ)
        1. downloads `.fa` and `.gtf` files for `human` and `mouse`
    1. **this step is not necessary if using the downloaded human or mouse genomes from the last step**. if you move the genome files, can just update their paths in `config.yaml`. otherwise configure spacemake with the `species`. all other configuration _should_ be the shipped with `v0.7.4` (specifically, `barcode_flavor`, `puck`, and `run_mode` should already be configured in `config.yaml`).
        ```
        spacemake config add_species \
        --name mouse \
        --sequence <genome.fa> \
        --annotation <annotation.gtf>
        ```
    1. **NB** the provided run mode configuration overlays a hexagonal mesh over the coordinate grid. spots are aggregated into these hexagonal patches instead
1. add samples to project and run spacemake. i.e. generate expression matrix.
    1. need to tiles into separate fastqs???
    1. add samples to project
        ```
        spacemake projects add_sample \
        --project_id adult_mouse_hippocampus \
        --sample_id 1_1101 \
        --R1 data/adult_mouse_hippocampus/1_1101_R1.fastq.gz \
        --R2 data/adult_mouse_hippocampus/1_1101_R2.fastq.gz \
        --species mouse \
        --puck openst \
        --run_mode openst \
        --barcode_flavor openst \
        --puck_barcode_file tile-barcode-coords/adult_mouse_hippocampus/1_1101.txt
        ```
    1. run spacemake
        ```
        spacemake run \
        --cores <n_cores> \
        --keep-going
        ```
1. stitch pucks together (`openst spatial_stitch`) to generate one expression matrix