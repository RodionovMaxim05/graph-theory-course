# Graph Theory Course Benchmark Repository

This repository contains the infrastructure for a comparative study of graph algorithms in the [LAGraph](https://github.com/GraphBLAS/LAGraph) and [SPLA](https://github.com/SparseLinearAlgebra/spla) libraries.
It is based on a [`fork of spla-bench`](https://github.com/RodionovMaxim05/spla-bench) and adds custom research features for a performance comparison.

## Project scope

- Base benchmark infrastructure: [`spla-bench fork`](https://github.com/RodionovMaxim05/spla-bench)
- Updated dependency versions: `LAGraph`, `SPLA`, and `SuiteSparse/GraphBLAS`
- Added support for PageRank benchmarking
- Added best-source selection for path-finding algorithms
- Unified algorithm execution parameters across benchmarks

## Repository layout

- `spla-bench/` — forked benchmark suite with submodules and benchmark scripts
- `plot.py` — plot generator for benchmark CSV results
- `profile_utils/parse_spla_profile.py` — parser for SPLA profiling output
- `requirements.txt` — Python requirements for plotting and benchmarking tools

## How to build

```bash
git submodule update --init --recursive
```

### Build benchmark dependencies

The benchmark suite automatically builds the required dependencies the first time you run the benchmarks. However, if you encounter any issues, please refer to the [README](./spla-bench/README.md).

### Apply LAGraph patches

Before benchmarking, apply the research-specific patches to LAGraph:

```bash
(cd spla-bench/ && python3 patchs/patch_lagraph_bfs.py && python3 patchs/patch_lagraph_tc.py)
```

More information about the patches themselves can be found in the corresponding [README](./spla-bench/patchs/README.md).

Rebuild the patched LAGraph executables:

```bash
cmake --build spla-bench/deps/lagraph/build --target bfs_demo tc_demo -j$(nproc)
```

## How to run benchmarks

The benchmark wrapper is available in `spla-bench/scripts/benchmark.py`.
It supports `--algo` values: `bfs`, `sssp`, `tc`, `pr`.
It supports `--tool` values: `spla`, `lagraph`.

Basic examples:

```bash
cd spla-bench

# BFS
./scripts/benchmark.py --algo bfs --tool lagraph --output ../benchmarks/bfs_lagraph.csv --format OutputFormat.csv --printer all

./scripts/benchmark.py --algo bfs --tool spla --output ../benchmarks/bfs_spla.csv --format OutputFormat.csv --printer all

# SSSP
./scripts/benchmark.py --algo sssp --tool lagraph --output ../benchmarks/sssp_lagraph.csv --format OutputFormat.csv --printer all

# PageRank
./scripts/benchmark.py --algo tc --tool lagraph --output ../benchmarks/tc_lagraph_nosort.csv --format OutputFormat.csv --printer all

# Triangle Counting
./scripts/benchmark.py --algo pr --tool spla --output ../benchmarks/pr_spla.csv --format OutputFormat.csv --printer all
```

### Notes on benchmark configuration

- The bench wrapper uses `spla-bench/scripts/config.py` for dataset selection and tool paths.

## Plotting results

After the benchmark runs complete, use `plot.py` to generate comparison charts.

Example:

```bash
# Standard comparison (BFS, SSSP, PR)
python3 plot.py benchmarks/lagraph.csv benchmarks/spla.csv --algo bfs --output plots/

# Triangle Counting with optional AutoSort baseline
python3 plot.py benchmarks/tc_lagraph_nosort.csv benchmarks/tc_spla.csv \
    --algo tc \
    --lagraph-sort benchmarks/tc_lagraph_autosort.csv \
    --output plots/
```

## Profiling commands

### LAGraph (CPU)

#### Call-graph profiling

```bash
perf record -g --call-graph=dwarf -F 999 ./spla-bench/deps/lagraph/build/src/benchmark/bfs_demo ./spla-bench/dataset/belgium_osm.mtx ./spla-bench/sources.mtx
perf report --stdio --no-children > perf_report_bfs_belgium.txt
```

#### Hardware counters

```bash
perf stat -e cycles,instructions,cache-references,cache-misses,LLC-loads,LLC-load-misses,branch-misses,branch-instructions -r 5 ./spla-bench/deps/lagraph/build/src/benchmark/bfs_demo ./spla-bench/dataset/belgium_osm.mtx ./spla-bench/sources.mtx
```

### SPLA (GPU)

#### Build with profiling support

```bash
cmake -S ./spla-bench/deps/spla -B ./spla-bench/deps/spla/build_profile -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_FLAGS="-fno-omit-frame-pointer"
cmake --build ./spla-bench/deps/spla/build_profile -j$(nproc)
```

#### Run and parse

```bash
./spla-bench/deps/spla/build_profile/bfs --mtxpath=./spla-bench/dataset/rgg_n_2_22_s0.mtx --niters=1 --source=1 | tee spla_profile_bfs_rgg.txt

# For BFS and SSSP only
python3 ./profile_utils/parse_spla_profile.py spla_profile_bfs_rgg.txt | tee spla_profile_bfs_rgg_summary.txt
```

## License

Distributed under the [MIT License](https://choosealicense.com/licenses/mit/). See [`LICENSE`](LICENSE) for more information.
