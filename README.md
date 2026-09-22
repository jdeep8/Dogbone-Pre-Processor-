# Dogbone Tensile Specimen Pre-Processor & Mesher for Abaqus

An automated Python pre-processing pipeline for **Abaqus/CAE**. This script converts raw 3D solid tensile specimen CAD models into partitioned, cleaned 2D midsurface shell models with structured quad meshing and virtual extensometer node sets in a single execution.
<img width="1389" height="765" alt="grafik" src="https://github.com/user-attachments/assets/42e9fb01-5876-4c53-8105-4fd720c6d6e9" />

---

## Dimension Reference Guide

Before running the script, measure your specimen CAD model according to the schematic below and write them down somewhere to input it later in the script.

<img width="1198" height="600" alt="grafik" src="https://github.com/user-attachments/assets/11db58d1-de31-4494-97bc-edd24c4a0609" />


### Drawing Parameter Mapping

| GUI Input Field | Drawing Label | Parameter Name | Description |
| :--- | :---: | :--- | :--- |
| **Gauge Length L0 [mm]** | `a` | `L0` | Extensometer gauge length. Used for inner cell partitions and creating single-node tracking sets (`Set-Ext-1`, `Set-Ext-2`). |
| **Parallel Length Lc [mm]** | `b` | `Lc` | Total parallel section length. Used for outer gauge cell partitions and local seed edge selection. Must be greater than L0. |
| **Parallel Section Width [mm]** | `c` | `Width` | Width of the gauge section. Used as search bounding-box limit. |
| **End Section / Grip Height [mm]** | `d` | `h_grip` | Height of the outer grip heads / ears for datum partitioning. |
| **Bottom Grip Cut [mm]** | — | `Y_cut_bot` | Distance from lower bounding-box boundary to trim off excess mounting section via Boolean cut. |
| **Top Grip Cut [mm]** | — | `Y_cut_top` | Distance from upper bounding-box boundary to trim off excess mounting section via Boolean cut. |
| **Global Mesh Size [mm]** | — | `e_global` | Global seed size applied across the entire specimen body. |
| **Parallel Mesh Size [mm]** | — | `e_local` | Refined local seed size applied exclusively to the parallel gauge edges. |
| **Geometry & Search Tolerance [mm]** | — | `Tol` | Spatial tolerance for geometric search filters and node detection algorithms. |

---

## Key Features

* **Single-Dialog Automation**: Input geometric dimensions and meshing preferences in one unified setup dialog.
* **Datum & Cell Partitioning**: Automatically creates XZ datum planes to partition the parallel region (`Lc`), inner gauge region (`L0`), and grip sections (`h_grip`).
* **Automated Boolean Cuts**: Trims upper and lower grip geometries dynamically based on custom offset cuts.
* **3D Solid to 2D Midsurface Conversion**: Extracts front-facing faces and offsets them by half-thickness to generate 2D shell planar representations.
* **Structured Quad Meshing**: Enforces `STRUCTURED` quad mesh controls across shell regions, falling back to `FREE` quad where complex transitions dictate.
* **Local Edge Refinement**: Automatically groups parallel gauge faces and seeds boundaries with a refined element size.
* **Virtual Extensometer Node Sets**: Identifies and tags center nodes at `Y = Y_center ± (L0 / 2)` to form `Set-Ext-1` and `Set-Ext-2` for automated strain extraction during post-processing.

---

## Workflow Sequence

When executed, `run_complete_specimen_pipeline()` performs the following 10 steps sequentially:

1. **Origin CSYS Alignment**: Creates a Cartesian reference CSYS (`Ref_Origin_Corner`) at the lower corner of the specimen bounding box.
2. **Gauge & Parallel Partitioning**: Slices the part horizontally at `Y_center ± (Lc / 2)` and `Y_center ± (L0 / 2)`.
3. **Grip Region Partitioning**: Slices the top and bottom grip ears at `Y_max - h_grip` and `Y_min + h_grip`.
4. **Grip Trimming (Boolean Cut)**: Creates extrusion cutters to remove unneeded clamping material based on top and bottom grip cut values.
5. **2D Shell Extraction**: Extracts front faces and applies `OffsetFaces` by half-thickness to generate the midsurface geometry.
6. **Mesh Control Assignment**: Applies `QUAD` element shape and `STRUCTURED` meshing algorithm to all midsurface faces.
7. **Global Seeding**: Applies uniform global seeds across all edges.
8. **Parallel Region Identification**: Detects edges within the parallel zone (`Lc × Width`) and applies local mesh seeding (`e_local`).
9. **Mesh Generation & Extensometer Tagging**: Builds the quad element mesh and locates the two closest surface nodes at the gauge bounds (`L0`) to construct `Set-Ext-1` and `Set-Ext-2`.
10. **Assembly Update**: Re-creates dependent assembly instances and updates viewport displays automatically.

---

## How to Run in Abaqus/CAE

### Option 1: Via Abaqus GUI (Recommended)
1. Open your Abaqus/CAE database (`.cae`) containing the imported 3D specimen part under `Model-1`.
2. From the top menu bar, select **File -> Run Script...**
3. Browse and select `abaqus_specimen_pipeline.py`.
4. Fill in the parameters in the dialog box and click **OK**.

### Option 2: Via Abaqus Command Line / Kernel
Run the script directly inside the Abaqus CLI Command Line Interface at the bottom of the CAE window:

```python
execfile('abaqus_specimen_pipeline.py')
