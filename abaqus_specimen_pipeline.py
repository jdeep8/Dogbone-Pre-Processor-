from abaqus import *
from abaqusConstants import *
import part


def run_complete_specimen_pipeline():

    # =========================================================
    # 1. DYNAMIC MODEL & PART INITIALIZATION
    # =========================================================

    model_name = 'Model-1'
    if model_name not in mdb.models:
        print("ERROR: Model '{}' not found.".format(model_name))
        return

    model = mdb.models[model_name]

    if len(model.parts) == 0:
        print("ERROR: No parts found in Model-1.")
        return

    part_name = list(model.parts.keys())[0]

    print("\n==============================================")
    print(" AUTOMATED 2D SPECIMEN GENERATOR PIPELINE")
    print("==============================================")
    print("Target CAD Part: {}".format(part_name))


    # =========================================================
    # 2. UNIFIED USER INPUT DIALOG
    # =========================================================

    fields = (
        ('Gauge Length L0 [mm]:', '10.0'),
        ('Parallel Length Lc [mm]:', '15.0'),
        ('Parallel Section Width [mm]:', '10.0'),
        ('End Section / Grip Height [mm]:', '21.77'),
        ('Bottom Grip Cut [mm]:', '15.5'),
        ('Top Grip Cut [mm]:', '15.5'),
        ('Global Mesh Size [mm]:', '2.0'),
        ('Parallel Mesh Size [mm]:', '0.5'),
        ('Geometry & Search Tolerance [mm]:', '0.20'),
    )

    user_input = getInputs(
        fields=fields,
        label='Specimen Geometry, Meshing & Extensometer Setup',
        dialogTitle='Master Specimen Generator Setup'
    )

    if not user_input:
        print("Operation cancelled by user.")
        return

    try:
        l_gauge          = float(user_input[0])
        l_parallel       = float(user_input[1])
        parallel_width   = float(user_input[2])
        h_grip           = float(user_input[3])
        bottom_grip      = float(user_input[4])
        top_grip         = float(user_input[5])
        global_mesh_size = float(user_input[6])
        local_mesh_size  = float(user_input[7])
        tol              = float(user_input[8])
    except Exception:
        print("ERROR: Invalid numerical input provided.")
        return

    # Validation Checks
    if l_parallel <= l_gauge:
        print("ERROR: Parallel length Lc ({:.2f} mm) must be greater than Gauge length L0 ({:.2f} mm).".format(l_parallel, l_gauge))
        return

    if (global_mesh_size <= 0.0 or parallel_width <= 0.0 or 
        local_mesh_size <= 0.0 or tol <= 0.0 or h_grip <= 0.0):
        print("ERROR: Dimensions and mesh parameters must be positive non-zero numbers.")
        return


    # =========================================================
    # STEP 1: SET CORNER REFERENCE CSYS
    # =========================================================

    p = model.parts[part_name]

    x_coords = [v.pointOn[0][0] for v in p.vertices]
    y_coords = [v.pointOn[0][1] for v in p.vertices]
    z_coords = [v.pointOn[0][2] for v in p.vertices]

    xmin, xmax = min(x_coords), max(x_coords)
    ymin, ymax = min(y_coords), max(y_coords)
    zmin, zmax = min(z_coords), max(z_coords)

    corner_origin = (xmin, ymin, zmin)

    p.DatumCsysByThreePoints(
        name='Ref_Origin_Corner',
        coordSysType=CARTESIAN,
        origin=corner_origin,
        point1=(xmax, ymin, zmin),
        point2=(xmin, ymax, zmin)
    )

    print("[1/10] CSYS 'Ref_Origin_Corner' created at ({:.3f}, {:.3f}, {:.3f})".format(xmin, ymin, zmin))


    # =========================================================
    # STEP 2: PARTITION GAUGE & PARALLEL SECTIONS
    # =========================================================

    bbox = p.vertices.getBoundingBox()
    y_center = (bbox['low'][1] + bbox['high'][1]) / 2.0

    half_gauge = l_gauge / 2.0
    half_parallel = l_parallel / 2.0

    y_top_parallel = y_center + half_parallel
    y_bot_parallel = y_center - half_parallel
    y_top_gauge    = y_center + half_gauge
    y_bot_gauge    = y_center - half_gauge

    # Outer parallel bounds
    dp_top_par = p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=y_top_parallel)
    p.PartitionCellByDatumPlane(datumPlane=p.datums[dp_top_par.id], cells=p.cells)

    dp_bot_par = p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=y_bot_parallel)
    p.PartitionCellByDatumPlane(datumPlane=p.datums[dp_bot_par.id], cells=p.cells)

    # Inner gauge bounds
    dp_top_g = p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=y_top_gauge)
    p.PartitionCellByDatumPlane(datumPlane=p.datums[dp_top_g.id], cells=p.cells)

    dp_bot_g = p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=y_bot_gauge)
    p.PartitionCellByDatumPlane(datumPlane=p.datums[dp_bot_g.id], cells=p.cells)

    print("[2/10] Gauge (L0={:.2f} mm) and Parallel (Lc={:.2f} mm) partitions created.".format(l_gauge, l_parallel))


    # =========================================================
    # STEP 3: PARTITION OUTER EARS
    # =========================================================

    bbox = p.vertices.getBoundingBox()
    ymin_curr, ymax_curr = bbox['low'][1], bbox['high'][1]

    y_top_part = ymax_curr - h_grip
    y_bot_part = ymin_curr + h_grip

    dp_top = p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=y_top_part)
    p.PartitionCellByDatumPlane(datumPlane=p.datums[dp_top.id], cells=p.cells)

    dp_bot = p.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE, offset=y_bot_part)
    p.PartitionCellByDatumPlane(datumPlane=p.datums[dp_bot.id], cells=p.cells)

    print("[3/10] Outer ears partitions created at Y = {:.3f} mm and Y = {:.3f} mm.".format(y_top_part, y_bot_part))


    # =========================================================
    # STEP 4: CUT GRIPPING SECTIONS (BOOLEAN CUT)
    # =========================================================

    bbox = p.vertices.getBoundingBox()
    xmin, ymin, zmin = bbox['low'][0], bbox['low'][1], bbox['low'][2]
    xmax, ymax, zmax = bbox['high'][0], bbox['high'][1], bbox['high'][2]

    y_bottom_cut = ymin + bottom_grip
    y_top_cut    = ymax - top_grip

    if y_bottom_cut >= y_top_cut:
        print("ERROR: Grip cut locations overlap.")
        return

    margin = 10.0
    box_xmin, box_xmax = xmin - margin, xmax + margin
    box_ymin, box_ymax = ymin - margin, ymax + margin
    box_depth = (zmax - zmin) + 2.0 * margin

    # Top Cutter
    sketch_top = model.ConstrainedSketch(name='TopCutterSketch', sheetSize=200.0)
    sketch_top.rectangle(point1=(box_xmin, y_top_cut), point2=(box_xmax, box_ymax))
    top_cutter = model.Part(name='TopCutter', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    top_cutter.BaseSolidExtrude(sketch=sketch_top, depth=box_depth)
    del model.sketches['TopCutterSketch']

    # Bottom Cutter
    sketch_bottom = model.ConstrainedSketch(name='BottomCutterSketch', sheetSize=200.0)
    sketch_bottom.rectangle(point1=(box_xmin, box_ymin), point2=(box_xmax, y_bottom_cut))
    bottom_cutter = model.Part(name='BottomCutter', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    bottom_cutter.BaseSolidExtrude(sketch=sketch_bottom, depth=box_depth)
    del model.sketches['BottomCutterSketch']

    # Assembly Boolean Cut
    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)

    original_instance = a.Instance(name='OriginalInstance', part=p, dependent=ON)
    top_instance      = a.Instance(name='TopCutterInstance', part=top_cutter, dependent=ON)
    bottom_instance   = a.Instance(name='BottomCutterInstance', part=bottom_cutter, dependent=ON)

    a.translate(
        instanceList=('TopCutterInstance', 'BottomCutterInstance'),
        vector=(0.0, 0.0, zmin - margin)
    )

    a.InstanceFromBooleanCut(
        name='Temp_Cleaned',
        instanceToBeCut=original_instance,
        cuttingInstances=(top_instance, bottom_instance),
        originalInstances=SUPPRESS
    )

    # Clean temporary items
    del a.instances['TopCutterInstance']
    del a.instances['BottomCutterInstance']
    del a.instances['OriginalInstance']
    if 'Temp_Cleaned-1' in a.instances.keys():
        del a.instances['Temp_Cleaned-1']

    del model.parts['TopCutter']
    del model.parts['BottomCutter']

    # Re-key new part back to original CAD part name
    del model.parts[part_name]
    model.parts.changeKey(fromName='Temp_Cleaned', toName=part_name)
    p = model.parts[part_name]

    print("[4/10] Gripping sections cut successfully. Remaining height: {:.3f} mm".format(y_top_cut - y_bottom_cut))


    # =========================================================
    # STEP 5: CONVERT TO 2D MIDSURFACE SHELL
    # =========================================================

    try:
        p.AssignMidsurfaceRegion(cellList=p.cells)
    except Exception as e:
        print("Notice on AssignMidsurfaceRegion: {}".format(str(e)))

    bbox = p.vertices.getBoundingBox()
    zmin_shell = bbox['low'][2]
    zmax_shell = bbox['high'][2]

    thickness = zmax_shell - zmin_shell
    half_thickness = thickness / 2.0

    tol_z = 1e-3
    front_faces = p.faces.getByBoundingBox(zMin=zmax_shell - tol_z, zMax=zmax_shell + tol_z)

    if len(front_faces) == 0:
        print("ERROR: Could not identify front-facing faces at Z = {:.4f}".format(zmax_shell))
        return

    try:
        p.OffsetFaces(
            faceList=front_faces,
            distance=half_thickness,
            trimToReferenceRep=False
        )
    except Exception:
        try:
            p.OffsetFaces(
                faceList=front_faces,
                distance=-half_thickness,
                trimToReferenceRep=False
            )
        except Exception as e2:
            print("ERROR executing OffsetFaces: {}".format(str(e2)))
            return

    print("[5/10] 2D Midsurface shell generated (Offset: {:.3f} mm)".format(half_thickness))


    # =========================================================
    # STEP 6: ENFORCE STRUCTURED MESH CONTROLS
    # =========================================================

    bbox = p.vertices.getBoundingBox()
    zmin, zmax = bbox['low'][2], bbox['high'][2]
    z_mid = (zmin + zmax) / 2.0

    midsurface_faces = p.faces.getByBoundingBox(zMin=z_mid - 1e-2, zMax=z_mid + 1e-2)
    target_faces = midsurface_faces if len(midsurface_faces) > 0 else p.faces

    structured_count = 0
    fallback_count = 0

    for f in target_faces:
        face_region = p.faces[f.index:f.index+1]
        try:
            p.setMeshControls(
                regions=face_region, 
                technique=STRUCTURED, 
                elemShape=QUAD
            )
            structured_count += 1
        except Exception:
            try:
                p.setMeshControls(
                    regions=face_region, 
                    technique=FREE, 
                    elemShape=QUAD
                )
                fallback_count += 1
            except Exception as e:
                print("  Failed on face {}: {}".format(f.index, str(e)))

    print("[6/10] Mesh controls enforced: {} Structured / {} Free Quad face(s)".format(structured_count, fallback_count))


    # =========================================================
    # STEP 7: APPLY GLOBAL PART SEED
    # =========================================================

    try:
        p.seedPart(
            size=global_mesh_size,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )
        print("[7/10] Global part seed applied: {:.3f} mm".format(global_mesh_size))
    except Exception as e:
        print("ERROR during global seeding: {}".format(str(e)))
        return


    # =========================================================
    # STEP 8: DETECT PARALLEL FACES & APPLY LOCAL SEED
    # =========================================================

    xmin, ymin = bbox['low'][0], bbox['low'][1]
    xmax, ymax = bbox['high'][0], bbox['high'][1]

    x_center = (xmin + xmax) / 2.0
    y_center = (ymin + ymax) / 2.0

    x_left   = x_center - (parallel_width / 2.0)
    x_right  = x_center + (parallel_width / 2.0)
    y_bottom = y_center - (l_parallel / 2.0)
    y_top    = y_center + (l_parallel / 2.0)

    selected_faces = []
    for face in p.faces:
        pt = face.pointOn[0]
        fx, fy = pt[0], pt[1]

        if (x_left - tol <= fx <= x_right + tol) and (y_bottom - tol <= fy <= y_top + tol):
            selected_faces.append(face)

    if len(selected_faces) == 0:
        print("ERROR: No faces found inside parallel section bounds.")
        return

    selected_edge_indices = set()
    for face in selected_faces:
        for e_idx in face.getEdges():
            selected_edge_indices.add(e_idx)

    selected_edges = [p.edges[idx] for idx in sorted(selected_edge_indices)]

    face_array = part.FaceArray(tuple(selected_faces))
    edge_array = part.EdgeArray(tuple(selected_edges))

    face_set_name = 'PARALLEL_GAUGE_FACES'
    edge_set_name = 'PARALLEL_GAUGE_SEED_EDGES'

    if face_set_name in p.sets.keys():
        del p.sets[face_set_name]
    if edge_set_name in p.sets.keys():
        del p.sets[edge_set_name]

    p.Set(name=face_set_name, faces=face_array)
    p.Set(name=edge_set_name, edges=edge_array)

    try:
        target_edge_set = p.sets[edge_set_name]
        p.seedEdgeBySize(
            edges=target_edge_set.edges,
            size=local_mesh_size,
            deviationFactor=0.1,
            minSizeFactor=0.1,
            constraint=FINER
        )
        print("[8/10] Parallel section seeded locally with size: {:.3f} mm".format(local_mesh_size))
    except Exception as e:
        print("ERROR while applying local edge seed: {}".format(str(e)))
        return


    # =========================================================
    # STEP 9: GENERATE MESH & CREATE EXTENSOMETER NODE SETS
    # =========================================================

    try:
        p.generateMesh()
        print("[9/10] Mesh generated successfully! Total Nodes: {}".format(len(p.nodes)))
    except Exception as e:
        print("ERROR during mesh generation: {}".format(str(e)))
        return

    # Extensometer Node Sets (Uses L0 directly)
    node_bbox = p.nodes.getBoundingBox()
    n_zmin, n_zmax = node_bbox['low'][2], node_bbox['high'][2]

    ext_y_top = y_center + half_gauge
    ext_y_bot = y_center - half_gauge

    top_candidates = p.nodes.getByBoundingBox(
        xMin=x_left - tol, xMax=x_right + tol,
        yMin=ext_y_top - tol, yMax=ext_y_top + tol,
        zMin=n_zmin - 1.0, zMax=n_zmax + 1.0
    )

    bot_candidates = p.nodes.getByBoundingBox(
        xMin=x_left - tol, xMax=x_right + tol,
        yMin=ext_y_bot - tol, yMax=ext_y_bot + tol,
        zMin=n_zmin - 1.0, zMax=n_zmax + 1.0
    )

    def get_closest_center_node(node_candidates, target_x, target_y):
        best_node = None
        min_dist = float('inf')
        for node in node_candidates:
            nx, ny = node.coordinates[0], node.coordinates[1]
            dist = ((nx - target_x) ** 2 + (ny - target_y) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                best_node = node
        return best_node

    if len(top_candidates) > 0 and len(bot_candidates) > 0:
        top_center_node = get_closest_center_node(top_candidates, x_center, ext_y_top)
        bot_center_node = get_closest_center_node(bot_candidates, x_center, ext_y_bot)

        set_1_name = 'Set-Ext-1'
        set_2_name = 'Set-Ext-2'

        if set_1_name in p.sets.keys():
            del p.sets[set_1_name]
        if set_2_name in p.sets.keys():
            del p.sets[set_2_name]

        top_node_array = p.nodes.sequenceFromLabels((top_center_node.label,))
        bot_node_array = p.nodes.sequenceFromLabels((bot_center_node.label,))

        p.Set(name=set_1_name, nodes=top_node_array)
        p.Set(name=set_2_name, nodes=bot_node_array)

        print("  -> Extensometer Set-Ext-1 created at Node {} ({:.3f}, {:.3f})".format(
            top_center_node.label, top_center_node.coordinates[0], top_center_node.coordinates[1]))
        print("  -> Extensometer Set-Ext-2 created at Node {} ({:.3f}, {:.3f})".format(
            bot_center_node.label, bot_center_node.coordinates[0], bot_center_node.coordinates[1]))
    else:
        print("WARNING: Could not find candidate nodes for extensometer sets within tolerance.")


    # =========================================================
    # STEP 10: ASSEMBLY REFRESH & VIEWPORT DISPLAY
    # =========================================================

    instance_name = part_name + '-1'
    if instance_name in a.instances.keys():
        del a.instances[instance_name]

    a.Instance(name=instance_name, part=p, dependent=ON)
    a.regenerate()

    session.viewports['Viewport: 1'].setValues(displayedObject=a)

    print("\n==============================================")
    print(" PIPELINE COMPLETE | READY FOR ANALYSIS")
    print("==============================================\n")


# =============================================================
# RUN EXECUTION
# =============================================================

run_complete_specimen_pipeline()