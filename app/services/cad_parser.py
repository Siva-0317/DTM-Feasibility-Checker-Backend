import logging
from typing import Optional, List, Tuple, Dict, Any

from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Face, TopoDS_Edge, topods
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_WIRE
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRep import BRep_Tool
from OCC.Core.GCPnts import GCPnts_AbscissaPoint
from OCC.Core.GeomAdaptor import GeomAdaptor_Curve
from OCC.Core.gp import gp_Pnt, gp_Vec
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.GeomAbs import GeomAbs_Cylinder
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.Geom import Geom_CylindricalSurface

logger = logging.getLogger(__name__)

def load_step_file(file_path: str) -> TopoDS_Shape:
    try:
        reader = STEPControl_Reader()
        status = reader.ReadFile(file_path)
        if status != IFSelect_RetDone:
            raise ValueError(f"Error reading STEP file: {file_path}")
        
        reader.TransferRoots()
        shape = reader.OneShape()
        return shape
    except Exception as e:
        logger.error(f"Failed to load STEP file {file_path}: {e}")
        raise ValueError(f"Failed to load STEP file: {e}")

def get_all_faces(shape: TopoDS_Shape) -> List[TopoDS_Face]:
    faces = []
    try:
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            faces.append(topods.Face(explorer.Current()))
            explorer.Next()
    except Exception as e:
        logger.warning(f"Error getting faces: {e}")
    return faces

def get_all_edges(shape: TopoDS_Shape) -> List[TopoDS_Edge]:
    edges = []
    try:
        explorer = TopExp_Explorer(shape, TopAbs_EDGE)
        while explorer.More():
            edges.append(topods.Edge(explorer.Current()))
            explorer.Next()
    except Exception as e:
        logger.warning(f"Error getting edges: {e}")
    return edges

def measure_face_to_face_distance(face1: TopoDS_Face, face2: TopoDS_Face) -> float:
    try:
        dist_calc = BRepExtrema_DistShapeShape(face1, face2)
        dist_calc.Perform()
        if dist_calc.IsDone() and dist_calc.NbSolution() > 0:
            return float(dist_calc.Value())
        return -1.0
    except Exception as e:
        logger.warning(f"Error computing face distance: {e}")
        return -1.0

def get_face_normal_at_center(face: TopoDS_Face) -> Tuple[float, float, float]:
    try:
        adaptor = BRepAdaptor_Surface(face)
        u_min = adaptor.FirstUParameter()
        u_max = adaptor.LastUParameter()
        v_min = adaptor.FirstVParameter()
        v_max = adaptor.LastVParameter()
        
        u_center = (u_min + u_max) / 2.0
        v_center = (v_min + v_max) / 2.0
        
        p = gp_Pnt()
        du = gp_Vec()
        dv = gp_Vec()
        adaptor.D1(u_center, v_center, p, du, dv)
        
        normal = du.Crossed(dv)
        if normal.Magnitude() > 1e-10:
            normal.Normalize()
            return (float(normal.X()), float(normal.Y()), float(normal.Z()))
        return (0.0, 0.0, 0.0)
    except Exception as e:
        logger.warning(f"Error computing face normal: {e}")
        return (0.0, 0.0, 0.0)

def get_edge_length(edge: TopoDS_Edge) -> float:
    try:
        res = BRep_Tool.Curve(edge)
        if not res or res[0] is None:
            return 0.0
        curve_handle, u1, u2 = res
        
        gac = GeomAdaptor_Curve(curve_handle, u1, u2)
        return float(GCPnts_AbscissaPoint.Length(gac))
    except Exception as e:
        logger.warning(f"Error computing edge length: {e}")
        return 0.0

def measure_fillet_radius(edge: TopoDS_Edge, shape: Optional[TopoDS_Shape] = None) -> Optional[float]:
    if shape is None:
        return None
    try:
        for face in get_all_faces(shape):
            edges_in_face = get_all_edges(face)
            if any(e.IsSame(edge) for e in edges_in_face):
                adaptor = BRepAdaptor_Surface(face)
                if adaptor.GetType() == GeomAbs_Cylinder:
                    return float(adaptor.Cylinder().Radius())
        return None
    except Exception as e:
        logger.warning(f"Error measuring fillet radius: {e}")
        return None

def get_edge_midpoint(edge: TopoDS_Edge) -> Tuple[float, float, float]:
    try:
        res = BRep_Tool.Curve(edge)
        if not res or res[0] is None:
            return (0.0, 0.0, 0.0)
        curve_handle, u1, u2 = res
        
        u_mid = (u1 + u2) / 2.0
        pnt = curve_handle.Value(u_mid)
        return (float(pnt.X()), float(pnt.Y()), float(pnt.Z()))
    except Exception as e:
        logger.warning(f"Error getting edge midpoint: {e}")
        return (0.0, 0.0, 0.0)

def count_holes_by_topology(shape: TopoDS_Shape) -> int:
    hole_count = 0
    try:
        exp_face = TopExp_Explorer(shape, TopAbs_FACE)
        while exp_face.More():
            face = topods.Face(exp_face.Current())
            
            wire_count = 0
            exp_wire = TopExp_Explorer(face, TopAbs_WIRE)
            while exp_wire.More():
                wire_count += 1
                exp_wire.Next()
                
            if wire_count > 1:
                hole_count += (wire_count - 1)
                
            exp_face.Next()
    except Exception as e:
        logger.warning(f"Error counting holes: {e}")
    return hole_count

def get_bottom_edges(shape: TopoDS_Shape, z_threshold_percentile: float = 0.15) -> List[TopoDS_Edge]:
    bottom_edges = []
    try:
        bbox = compute_bounding_box(shape)
        zmin = bbox["zmin"]
        zmax = bbox["zmax"]
        threshold_z = zmin + (zmax - zmin) * z_threshold_percentile
        
        all_edges = get_all_edges(shape)
        for edge in all_edges:
            edge_bbox = Bnd_Box()
            brepbndlib.Add(edge, edge_bbox)
            
            eminX, eminY, eminZ, emaxX, emaxY, emaxZ = edge_bbox.Get()
            edge_z_center = (eminZ + emaxZ) / 2.0
            
            if edge_z_center <= threshold_z:
                bottom_edges.append(edge)
    except Exception as e:
        logger.warning(f"Error finding bottom edges: {e}")
    return bottom_edges

def compute_bounding_box(shape: TopoDS_Shape) -> Dict[str, float]:
    try:
        bbox = Bnd_Box()
        brepbndlib.Add(shape, bbox)
        
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        
        return {
            "xmin": float(xmin),
            "xmax": float(xmax),
            "ymin": float(ymin),
            "ymax": float(ymax),
            "zmin": float(zmin),
            "zmax": float(zmax),
            "dx": float(xmax - xmin),
            "dy": float(ymax - ymin),
            "dz": float(zmax - zmin)
        }
    except Exception as e:
        logger.warning(f"Error computing bounding box: {e}")
        return {
            "xmin": 0.0, "xmax": 0.0, "ymin": 0.0, "ymax": 0.0,
            "zmin": 0.0, "zmax": 0.0, "dx": 0.0, "dy": 0.0, "dz": 0.0
        }

def classify_faces_by_normal(faces: List[TopoDS_Face]) -> Dict[str, List[TopoDS_Face]]:
    groups = {
        "horizontal": [],
        "vertical_x": [],
        "vertical_y": [],
        "angled": []
    }
    
    try:
        for face in faces:
            nx, ny, nz = get_face_normal_at_center(face)
            
            if abs(nz) > 0.8:
                groups["horizontal"].append(face)
            elif abs(nx) > 0.8:
                groups["vertical_x"].append(face)
            elif abs(ny) > 0.8:
                groups["vertical_y"].append(face)
            else:
                groups["angled"].append(face)
    except Exception as e:
        logger.warning(f"Error classifying faces: {e}")
        
    return groups

def extract_geometry_report(shape: TopoDS_Shape) -> Dict[str, Any]:
    try:
        faces = get_all_faces(shape)
        edges = get_all_edges(shape)
        hole_count = count_holes_by_topology(shape)
        bbox = compute_bounding_box(shape)
        
        bottom_edges_objs = get_bottom_edges(shape)
        bottom_edges_list = []
        for e in bottom_edges_objs:
            bottom_edges_list.append({
                "length": get_edge_length(e),
                "midpoint": list(get_edge_midpoint(e))
            })
            
        fillet_radii = []
        for e in edges:
            rad = measure_fillet_radius(e, shape)
            if rad is not None:
                fillet_radii.append({
                    "radius": rad,
                    "location": list(get_edge_midpoint(e))
                })
                
        face_groups = classify_faces_by_normal(faces)
        face_groups_count = {k: len(v) for k, v in face_groups.items()}
        
        return {
            "face_count": len(faces),
            "edge_count": len(edges),
            "hole_count": hole_count,
            "bounding_box": bbox,
            "bottom_edges": bottom_edges_list,
            "fillet_radii": fillet_radii,
            "face_groups": face_groups_count
        }
    except Exception as e:
        logger.error(f"Error generating geometry report: {e}")
        return {
            "face_count": 0,
            "edge_count": 0,
            "hole_count": 0,
            "bounding_box": {},
            "bottom_edges": [],
            "fillet_radii": [],
            "face_groups": {}
        }
