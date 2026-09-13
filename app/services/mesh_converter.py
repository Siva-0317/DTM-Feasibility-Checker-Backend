import logging
import os
import numpy as np
import trimesh
from typing import Dict, Any, Tuple

from OCC.Core.TopoDS import TopoDS_Shape, topods
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCC.Core.TopLoc import TopLoc_Location

from app.services.cad_parser import load_step_file, compute_bounding_box

logger = logging.getLogger(__name__)

def tessellate_shape(shape: TopoDS_Shape, linear_deflection: float = 0.5, angular_deflection: float = 0.5) -> Dict[str, Any]:
    try:
        mesh_alg = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
        mesh_alg.Perform()
    except Exception as e:
        logger.warning(f"BRepMesh_IncrementalMesh failed: {e}")
    
    vertices = []
    faces = []
    
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    vertex_offset = 0
    
    while exp.More():
        face = topods.Face(exp.Current())
        
        location = TopLoc_Location()
        poly = None
        try:
            poly = BRep_Tool.Triangulation(face, location)
        except TypeError:
            res = BRep_Tool.Triangulation(face)
            if isinstance(res, tuple):
                poly, location = res
            else:
                poly = res
                location = face.Location()
                
        if poly is not None and poly:
            nb_nodes = poly.NbNodes()
            nb_triangles = poly.NbTriangles()
            
            transf = location.Transformation()
            
            for i in range(1, nb_nodes + 1):
                pnt = poly.Node(i)
                pnt.Transform(transf)
                vertices.append([pnt.X(), pnt.Y(), pnt.Z()])
                
            reverse = (face.Orientation() == TopAbs_REVERSED)
            
            for i in range(1, nb_triangles + 1):
                t = poly.Triangle(i)
                idx1, idx2, idx3 = t.Get()
                
                v1 = idx1 - 1 + vertex_offset
                v2 = idx2 - 1 + vertex_offset
                v3 = idx3 - 1 + vertex_offset
                
                if reverse:
                    faces.append([v1, v3, v2])
                else:
                    faces.append([v1, v2, v3])
                    
            vertex_offset += nb_nodes
            
        exp.Next()
        
    return {
        "vertices": vertices,
        "faces": faces,
        "face_count": len(faces)
    }

def shape_to_trimesh(shape: TopoDS_Shape) -> trimesh.Trimesh:
    data = tessellate_shape(shape)
    
    if not data["vertices"] or not data["faces"]:
        raise ValueError("Shape contains no tessellable faces or tessellation failed.")
        
    mesh = trimesh.Trimesh(
        vertices=np.array(data["vertices"]),
        faces=np.array(data["faces"])
    )
    mesh.process()
    return mesh

def export_to_glb(shape: TopoDS_Shape, output_path: str) -> str:
    try:
        mesh = shape_to_trimesh(shape)
        mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=[200, 200, 210, 255])
        
        mesh.export(output_path, file_type='glb')
        return output_path
    except Exception as e:
        logger.error(f"Failed to export GLB to {output_path}: {e}")
        raise RuntimeError(f"Export failed: {e}")

def convert_step_to_glb(step_path: str, job_id: str, output_dir: str) -> str:
    try:
        shape = load_step_file(step_path)
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{job_id}.glb")
        return export_to_glb(shape, out_path)
    except Exception as e:
        logger.error(f"Error converting step {step_path} to glb: {e}")
        raise

def get_model_center(shape: TopoDS_Shape) -> Tuple[float, float, float]:
    try:
        bbox = compute_bounding_box(shape)
        cx = (bbox.get("xmin", 0) + bbox.get("xmax", 0)) / 2.0
        cy = (bbox.get("ymin", 0) + bbox.get("ymax", 0)) / 2.0
        cz = (bbox.get("zmin", 0) + bbox.get("zmax", 0)) / 2.0
        return (cx, cy, cz)
    except Exception as e:
        logger.warning(f"Failed to compute model center: {e}")
        return (0.0, 0.0, 0.0)
