# Standard Add-on Wrapper (Blender Add-on Template)
# To turn your standalone script into a shareable add-on file (.py), you must bundle your components alongside an initialization bl_info dictionary block. 
#Save this complete block as a single python file.

bl_info = {
    "name": "3D Print Prep",
    "description": "3D printing addon with cut and key making features. Required Scene Units > Unit System > Unit Scale: Metric/0.001",
    "author": "wicodepy",
    "version": (1, 0, 0),
    "blender": (5, 1, 2), # The minimum Blender version required
    "location": "View3D > Sidebar > Keymaker",
    "warning": "", # Use to display warning text in the Preferences menu
    "category": "Add-on", # Must be one of Blender's supported categories
}

import bpy
import bmesh
import mathutils

# May need to change to 3DPrintPrepSettings
class PrintPrepSettings(bpy.types.PropertyGroup):
    #Unified container class for all custom tool properties.
    
    # CUTMAKER SETTINGS

    cutm_cut_height: bpy.props.FloatProperty(
        name="Global Cut Height",
        description="Global Z value to cut the object along",
        default=0.0,
        unit='LENGTH'
    )

    # KEYMAKER SETTINGS

    keym_cut_height: bpy.props.FloatProperty(
        name="Global Cut Height",
        description="Global Z value to cut the object along",
        default=0.0,
        unit='LENGTH'
    )
    
    size_percentage: bpy.props.FloatProperty(
        name="Key Size (%)",
        description="Key(cube) size as a percentage of the smaller cross-section width (X or Y). Ensures that key does not poke out",
        default=25.0,
        min=5.0,
        max=95.0,
        subtype='PERCENTAGE'
    )
    
    clearance: bpy.props.FloatProperty(
        name="Clearance",
        description="Total clearance for hole. Default is 0.2 mm, which adds 0.1 mm to each side",
        default=0.2,
        min=0.0, # consider removing for user freedom
        step=1.0,
        unit='LENGTH'
    )

class CUTMAKER_PT_Panel(bpy.types.Panel):
    bl_label = "Cutmaker"   # The display name that appears in the panel header.
    bl_idname = "CUTMAKER_PT_Panel" # The unique identifier for the panel. By convention, it consists of an uppercase category abbreviation and the panel name (e.g., VIEW3D_PT_my_panel)
    bl_space_type = 'VIEW_3D'   # The Blender workspace area the panel belongs to (e.g., VIEW_3D for the 3D Viewport or PROPERTIES for the Properties Editor sidebar).
    bl_region_type = 'UI'   # The specific UI region within the space (e.g., WINDOW for main areas, UI for the Sidebar/N-panel, or HEADER).
    bl_category = '3D Print Prep' # The name of the tab in the UI region (e.g., your add-on's name).

    def draw(self, context):
        layout = self.layout
        props = context.scene.PrintPrep3D  # Pull values from our custom container class

        layout.prop(props, "cutm_cut_height")
        
        layout.operator("mesh.make_cuts", text="Make cuts")

class KEYMAKER_PT_Panel(bpy.types.Panel):
    bl_label = "Keymaker"   # The display name that appears in the panel header.
    bl_idname = "KEYMAKER_PT_Panel" # The unique identifier for the panel. By convention, it consists of an uppercase category abbreviation and the panel name (e.g., VIEW3D_PT_my_panel)
    bl_space_type = 'VIEW_3D'   # The Blender workspace area the panel belongs to (e.g., VIEW_3D for the 3D Viewport or PROPERTIES for the Properties Editor sidebar).
    bl_region_type = 'UI'   # The specific UI region within the space (e.g., WINDOW for main areas, UI for the Sidebar/N-panel, or HEADER).
    bl_category = '3D Print Prep' # The name of the tab in the UI region (e.g., your add-on's name).

    def draw(self, context):
        layout = self.layout
        props = context.scene.PrintPrep3D  # Pull values from our custom container class. Access properties via PropertyGroup reference


        layout.prop(props, "keym_cut_height")    # 1st parameter is data container, 2nd parameter is accesses
        layout.prop(props, "size_percentage")
        layout.prop(props, "clearance")
        
        layout.operator("mesh.make_keys", text="Make keys")

class CUTMAKER_OT_MakeCuts(bpy.types.Operator):
    bl_idname = "mesh.make_cuts"    # This is a mandatory string variable used to uniquely identify and register custom tools, menus, panels, and operators
    bl_label = "Cut Keys"  # This is a string that determines the visible name of the operator as it appears to the user in menus, buttons, and the Undo/Redo history panel
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        orig_obj = context.active_object
        props = context.scene.PrintPrep3D  # Pull values from our custom container class. Access properties via PropertyGroup reference

        # Object selection and type check
        if not orig_obj or orig_obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a target mesh object.")
            return {'CANCELLED'}

        # Ensure all transformations are applied for correct spatial calculations
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Declare variable names for settings from panel

        # Cutmaker settings
        cut_z = props.cutm_cut_height
        original_name = orig_obj.name
        
        # --- CALCULATE TRUE CROSS SECTION AT CUT HEIGHT ---
        bm = bmesh.new()    # Generate new empty BMesh
        bm.from_mesh(orig_obj.data) # Copies all the vertices, edges, and faces from your selected object into this temporary virtual sandbox for Blender's advanced mesh editing.
        
        # Bisect along Z axis
        bisect_res = bmesh.ops.bisect_plane(
            bm,
            geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
            plane_co=(0, 0, cut_z),
            plane_no=(0, 0, 1.0),
            clear_inner=False,
            clear_outer=False
        )
        
        # Identifying the vertices along the cut line
        cut_verts = [v for v in bisect_res['geom_cut'] if isinstance(v, bmesh.types.BMVert)]
            #bisect_res['geom_cut']: The slice operator returns a dictionary of newly created edges, faces, and vertices right on the cut line.
            # Use list comprehension to create a list of only the vertices

        
        # Check that a cut was made and verts were stored, otherwise cancel
        if not cut_verts:
            self.report({'ERROR'}, f"No geometry found intersecting Global Cut Height ({cut_z}).")
            bm.free()       # Free memory used for virtual sandbox
            return {'CANCELLED'}

        # Collect x and y values  
        cut_x_coords = [v.co.x for v in cut_verts]
        cut_y_coords = [v.co.y for v in cut_verts]
        # Find the min and max
        cut_min_x, cut_max_x = min(cut_x_coords), max(cut_x_coords)
        cut_min_y, cut_max_y = min(cut_y_coords), max(cut_y_coords)
        # Determine X and Y width, determine which is smaller value
        cross_width_x = cut_max_x - cut_min_x
        cross_width_y = cut_max_y - cut_min_y
        smallest_cross_width = min(cross_width_x, cross_width_y)
        # Use midpoint of X and Y to find center of cross section
        center_x = (cut_min_x + cut_max_x) / 2.0
        center_y = (cut_min_y + cut_max_y) / 2.0
        
        bm.free()   # Free memory used for virtual sandbox
        
        # Create duplicate for top split
        bpy.ops.object.select_all(action='DESELECT')    # clear all selections
        orig_obj.select_set(True)                       #select target mesh
        context.view_layer.objects.active = orig_obj    #Designates your model as the Active Object (highlighted in bright yellow). Blender's duplication commands require an active object reference to execute properly
        
        bpy.ops.object.duplicate()              #Executes Blender's native duplication operator (the equivalent of hitting Shift + D in the viewport). This instantly duplicates the active mesh along with all of its modifiers and structural data.
        top_obj = context.active_object
        top_obj.name = f"{original_name}_top"   #Rename object with top
        
        # Create duplicate for bottom split
        bpy.ops.object.select_all(action='DESELECT')
        orig_obj.select_set(True)
        context.view_layer.objects.active = orig_obj
        
        bpy.ops.object.duplicate()              #Executes Blender's native duplication operator (the equivalent of hitting Shift + D in the viewport). This instantly duplicates the active mesh along with all of its modifiers and structural data.
        bottom_obj = context.active_object
        bottom_obj.name = f"{original_name}_bottom" #Rename object with bottom

        # Read overall bounds boundaries for the split operation
        bbox_corners = [orig_obj.matrix_world @ mathutils.Vector(v) for v in orig_obj.bound_box]    
            #Every object in Blender has an optimized native list containing 8 coordinates. These coordinates form an imaginary box that tightly wraps around the mesh's furthest outer points. By default, these coordinates are stored in Local Space (relative only to the object's origin point).
            #This is a matrix multiplication operation. It transforms each local bounding box corner into Absolute World Space (relative to the global 0,0,0 center point of the viewport grid).
        cross_width_z = max([v.z for v in bbox_corners]) - min([v.z for v in bbox_corners])   # Find the height of the bounding box based on the difference

        # Large cutter configuration sizing bounds
        cutter_size = max(cross_width_x, cross_width_y, cross_width_z) * 4.0
        
        # --- Create Top Object Slicing ---
        bpy.ops.mesh.primitive_cube_add(size=cutter_size, location=(center_x, center_y, cut_z - (cutter_size / 2.0)))   # Spawns a large cube at the cross section and moves it down.
        cutter_bottom = context.active_object
        
        context.view_layer.objects.active = top_obj
        mod_top_cut = top_obj.modifiers.new(name="CutTop", type='BOOLEAN')
        mod_top_cut.operation = 'DIFFERENCE'
        mod_top_cut.solver = 'EXACT'
        mod_top_cut.object = cutter_bottom
        
        try:
            bpy.ops.object.modifier_apply(modifier=mod_top_cut.name)    # Apply boolean modifier
        except Exception:
            mod_top_cut.solver = 'FAST'                                 # Change solver to Fast
            bpy.ops.object.modifier_apply(modifier=mod_top_cut.name)    # Apply boolean moifier
            
        bpy.data.objects.remove(cutter_bottom, do_unlink=True)          # Delete the cutter cuber

        # --- Create Bottom Object Slicing ---
        bpy.ops.mesh.primitive_cube_add(size=cutter_size, location=(center_x, center_y, cut_z + (cutter_size / 2.0)))
        cutter_top = context.active_object
        
        context.view_layer.objects.active = bottom_obj
        mod_bottom_cut = bottom_obj.modifiers.new(name="CutBottom", type='BOOLEAN')
        mod_bottom_cut.operation = 'DIFFERENCE'
        mod_bottom_cut.solver = 'EXACT'
        mod_bottom_cut.object = cutter_top
        
        try:
            bpy.ops.object.modifier_apply(modifier=mod_bottom_cut.name)
        except Exception:
            mod_bottom_cut.solver = 'FAST'
            bpy.ops.object.modifier_apply(modifier=mod_bottom_cut.name)
            
        bpy.data.objects.remove(cutter_top, do_unlink=True)


        # Leave original selection active and unchanged
        bpy.ops.object.select_all(action='DESELECT')
        orig_obj.select_set(True)
        context.view_layer.objects.active = orig_obj

        self.report({'INFO'}, "Successfully cut mesh!")
        return {'FINISHED'}

class KEYMAKER_OT_MakeKeys(bpy.types.Operator):
    bl_idname = "mesh.make_keys"    # This is a mandatory string variable used to uniquely identify and register custom tools, menus, panels, and operators
    bl_label = "Make Keys"  # This is a string that determines the visible name of the operator as it appears to the user in menus, buttons, and the Undo/Redo history panel
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        orig_obj = context.active_object
        props = context.scene.PrintPrep3D  # Pull values from our custom container class. Access properties via PropertyGroup reference

        # Object selection and type check
        if not orig_obj or orig_obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a target mesh object.")
            return {'CANCELLED'}

        # Ensure all transformations are applied for correct spatial calculations
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Declare variable names for settings from panel
        
        # Keymaker settings
        cut_z = props.keym_cut_height
        clearance_val = props.clearance
        size_pct = props.size_percentage
        original_name = orig_obj.name
        
        # --- CALCULATE TRUE CROSS SECTION AT CUT HEIGHT ---
        bm = bmesh.new()    # Generate new empty BMesh
        bm.from_mesh(orig_obj.data) # Copies all the vertices, edges, and faces from your selected object into this temporary virtual sandbox for Blender's advanced mesh editing.
        
        # Bisect along Z axis
        bisect_res = bmesh.ops.bisect_plane(
            bm,
            geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
            plane_co=(0, 0, cut_z),
            plane_no=(0, 0, 1.0),
            clear_inner=False,
            clear_outer=False
        )
        
        # Identifying the vertices along the cut line
        cut_verts = [v for v in bisect_res['geom_cut'] if isinstance(v, bmesh.types.BMVert)]
            #bisect_res['geom_cut']: The slice operator returns a dictionary of newly created edges, faces, and vertices right on the cut line.
            # Use list comprehension to create a list of only the vertices

        
        # Check that a cut was made and verts were stored, otherwise cancel
        if not cut_verts:
            self.report({'ERROR'}, f"No geometry found intersecting Global Cut Height ({cut_z}).")
            bm.free()       # Free memory used for virtual sandbox
            return {'CANCELLED'}

        # Collect x and y values  
        cut_x_coords = [v.co.x for v in cut_verts]
        cut_y_coords = [v.co.y for v in cut_verts]
        # Find the min and max
        cut_min_x, cut_max_x = min(cut_x_coords), max(cut_x_coords)
        cut_min_y, cut_max_y = min(cut_y_coords), max(cut_y_coords)
        # Determine X and Y width, determine which is smaller value
        cross_width_x = cut_max_x - cut_min_x
        cross_width_y = cut_max_y - cut_min_y
        smallest_cross_width = min(cross_width_x, cross_width_y)
        # Use midpoint of X and Y to find center of cross section
        center_x = (cut_min_x + cut_max_x) / 2.0
        center_y = (cut_min_y + cut_max_y) / 2.0
        
        bm.free()   # Free memory used for virtual sandbox

        # Calculate key width for X and Y as a percentage of smallest cross section width
        key_width_xy = smallest_cross_width * (size_pct / 100.0)
        
        # Key height Z matches key width
        key_height_z = key_width_xy
        
        # Create duplicate for top split
        bpy.ops.object.select_all(action='DESELECT')    # clear all selections
        orig_obj.select_set(True)                       #select target mesh
        context.view_layer.objects.active = orig_obj    #Designates your model as the Active Object (highlighted in bright yellow). Blender's duplication commands require an active object reference to execute properly
        
        bpy.ops.object.duplicate()              #Executes Blender's native duplication operator (the equivalent of hitting Shift + D in the viewport). This instantly duplicates the active mesh along with all of its modifiers and structural data.
        top_obj = context.active_object
        top_obj.name = f"{original_name}_top"   #Rename object with top
        
        # Create duplicate for bottom split
        bpy.ops.object.select_all(action='DESELECT')
        orig_obj.select_set(True)
        context.view_layer.objects.active = orig_obj
        
        bpy.ops.object.duplicate()              #Executes Blender's native duplication operator (the equivalent of hitting Shift + D in the viewport). This instantly duplicates the active mesh along with all of its modifiers and structural data.
        bottom_obj = context.active_object
        bottom_obj.name = f"{original_name}_bottom" #Rename object with bottom

        # Read overall bounds boundaries for the split operation
        bbox_corners = [orig_obj.matrix_world @ mathutils.Vector(v) for v in orig_obj.bound_box]    
            #Every object in Blender has an optimized native list containing 8 coordinates. These coordinates form an imaginary box that tightly wraps around the mesh's furthest outer points. By default, these coordinates are stored in Local Space (relative only to the object's origin point).
            #This is a matrix multiplication operation. It transforms each local bounding box corner into Absolute World Space (relative to the global 0,0,0 center point of the viewport grid).
        cross_width_z = max([v.z for v in bbox_corners]) - min([v.z for v in bbox_corners])   # Find the height of the bounding box based on the difference

        # Large cutter configuration sizing bounds
        cutter_size = max(cross_width_x, cross_width_y, cross_width_z) * 4.0
        
        # --- Create Top Object Slicing ---
        bpy.ops.mesh.primitive_cube_add(size=cutter_size, location=(center_x, center_y, cut_z - (cutter_size / 2.0)))   # Spawns a large cube at the cross section and moves it down.
        cutter_bottom = context.active_object
        
        context.view_layer.objects.active = top_obj
        mod_top_cut = top_obj.modifiers.new(name="CutTop", type='BOOLEAN')
        mod_top_cut.operation = 'DIFFERENCE'
        mod_top_cut.solver = 'EXACT'
        mod_top_cut.object = cutter_bottom
        
        try:
            bpy.ops.object.modifier_apply(modifier=mod_top_cut.name)    # Apply boolean modifier
        except Exception:
            mod_top_cut.solver = 'FAST'                                 # Change solver to Fast
            bpy.ops.object.modifier_apply(modifier=mod_top_cut.name)    # Apply boolean moifier
            
        bpy.data.objects.remove(cutter_bottom, do_unlink=True)          # Delete the cutter cuber

        # --- Create Bottom Object Slicing ---
        bpy.ops.mesh.primitive_cube_add(size=cutter_size, location=(center_x, center_y, cut_z + (cutter_size / 2.0)))
        cutter_top = context.active_object
        
        context.view_layer.objects.active = bottom_obj
        mod_bottom_cut = bottom_obj.modifiers.new(name="CutBottom", type='BOOLEAN')
        mod_bottom_cut.operation = 'DIFFERENCE'
        mod_bottom_cut.solver = 'EXACT'
        mod_bottom_cut.object = cutter_top
        
        try:
            bpy.ops.object.modifier_apply(modifier=mod_bottom_cut.name)
        except Exception:
            mod_bottom_cut.solver = 'FAST'
            bpy.ops.object.modifier_apply(modifier=mod_bottom_cut.name)
            
        bpy.data.objects.remove(cutter_top, do_unlink=True)

        # Generate key and hole
        
        # Create 1x1x1 cube, name, and scale key size
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center_x, center_y, cut_z))
        key_obj = context.active_object
        key_obj.name = "key"
        key_obj.scale = (key_width_xy, key_width_xy, key_height_z) # Scale works because starting cube is 1x1x1. 1 x scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Apply raw clearance to compute the socket widening directly in world units
        hole_width_xy = key_width_xy + clearance_val
        hole_height_z = key_height_z + clearance_val
        
        # Create 1x1x1 cube, name, and scale hole size
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center_x, center_y, cut_z))
        hole_obj = context.active_object
        hole_obj.name = "hole"
        hole_obj.scale = (hole_width_xy, hole_width_xy, hole_height_z)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Apply Union to Bottom Part
        context.view_layer.objects.active = bottom_obj
        mod_union = bottom_obj.modifiers.new(name="KeyUnion", type='BOOLEAN')
        mod_union.operation = 'UNION'
        mod_union.solver = 'EXACT'
        mod_union.object = key_obj
        
        try:
            bpy.ops.object.modifier_apply(modifier=mod_union.name)
        except Exception:
            mod_union.solver = 'FAST'
            bpy.ops.object.modifier_apply(modifier=mod_union.name)

        # Apply Difference to Top Part
        context.view_layer.objects.active = top_obj
        mod_diff = top_obj.modifiers.new(name="HoleDiff", type='BOOLEAN')
        mod_diff.operation = 'DIFFERENCE'
        mod_diff.solver = 'EXACT'
        mod_diff.object = hole_obj
        
        try:
            bpy.ops.object.modifier_apply(modifier=mod_diff.name)
        except Exception:
            mod_diff.solver = 'FAST'
            bpy.ops.object.modifier_apply(modifier=mod_diff.name)

        # Remove key and hole
        bpy.data.objects.remove(key_obj, do_unlink=True)
        bpy.data.objects.remove(hole_obj, do_unlink=True)

        # Leave original selection active and unchanged
        bpy.ops.object.select_all(action='DESELECT')
        orig_obj.select_set(True)
        context.view_layer.objects.active = orig_obj

        self.report({'INFO'}, "Successfully keyed mesh!")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(PrintPrepSettings)
    bpy.utils.register_class(CUTMAKER_PT_Panel)
    bpy.utils.register_class(KEYMAKER_PT_Panel)
    bpy.utils.register_class(CUTMAKER_OT_MakeCuts)
    bpy.utils.register_class(KEYMAKER_OT_MakeKeys)
    
    # Map our unified container class structure to Scene settings
    bpy.types.Scene.PrintPrep3D = bpy.props.PointerProperty(type=PrintPrepSettings)

def unregister():
    bpy.utils.unregister_class(PrintPrepSettings)
    bpy.utils.unregister_class(CUTMAKER_PT_Panel)
    bpy.utils.unregister_class(KEYMAKER_PT_Panel)
    bpy.utils.unregister_class(CUTMAKER_OT_MakeCuts)
    bpy.utils.unregister_class(KEYMAKER_OT_MakeKeys)
    
    del bpy.types.Scene.PrintPrep3D

if __name__ == "__main__":
    register()
