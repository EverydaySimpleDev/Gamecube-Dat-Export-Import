bl_info = {
    "name": "Gamecube Dat Export - Import Model",
    "author": "EverydaySimpleDev",
    "blender": (2, 83, 9),
    "location": "File > Import-Export",
    "description": "Import-Export Gamecube .dat models",
    "warning": "",
    "category": "Import-Export"}


if "bpy" in locals():
    import importlib
    if "hsd" in locals():
        importlib.reload(hsd)
    if "import_hsd" in locals():
        importlib.reload(import_hsd)
    if "util" in locals():
        importlib.reload(util)


import os
import bpy
from mathutils import Matrix
from bpy.props import (
        CollectionProperty,
        StringProperty,
        BoolProperty,
        EnumProperty,
        FloatProperty,
        IntProperty,
)
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        axis_conversion,
        orientation_helper,
        axis_conversion,
)
from bpy.types import (
    Operator,
    OperatorFileListElement,
)

class ImportHSD(bpy.types.Operator, ImportHelper):
    """Load a HSD scene"""
    bl_idname = "import_scene.hsd"
    bl_label = "Import Dat"
    bl_options = {'UNDO'}

    global_scale: FloatProperty(
        name="Scale",
        soft_min=0.001, soft_max=1000.0,
        min=1e-6, max=1e6,
        default=1.0,
    )

    files: bpy.props.CollectionProperty(name="File Path",
                          description="File path used for importing "
                                      "the HSD file",
                          type=bpy.types.OperatorFileListElement)
    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    section: bpy.props.StringProperty(default = 'scene_data', name = 'Section Name', description = 'Name of the section that should be imported as a scene')
    offset: bpy.props.IntProperty(default = 0, name = 'Offset', description = 'Offset of the Scene data in the file')
    data_type: bpy.props.EnumProperty(
                items = (('SCENE', 'Scene', 'Import Scene'),
                         ('BONE', 'Bone', 'Import Armature')
                        ), name = 'Data Type', description = 'The type of data that is stored in the section')
    import_animation: bpy.props.BoolProperty(default = True, name = 'Import Animation', description = 'Whether to import animation. Off by default while it\'s still very buggy')
    ik_hack: bpy.props.BoolProperty(default = True, name = 'IK Hack', description = 'Shrinks Bones down to 1e-3 to make IK work properly')
    use_max_frame: bpy.props.BoolProperty(default = True, name = 'Use Max Anim Frame', description = 'Limits the sampled animation range to a maximum length')
    max_frame: bpy.props.IntProperty(default = 1000, name = 'Max Anim Frame', description = 'Cutoff frame after which animations aren\'t sampled')

    filename_ext = ".dat"
    filter_glob = StringProperty(default="*.fdat;*.dat;*.rdat;*.pkx", options={'HIDDEN'})

    def execute(self, context):
        if self.files and self.directory:
            paths = [os.path.join(self.directory, file.name) for file in self.files]
        else:
            paths = [self.filepath]

        from . import import_hsd

        scene = context.scene

        global_scale = self.global_scale
        global_scale /= scene.unit_settings.scale_length

        #import trace
        #tracer = trace.Trace(trace=1)

        for path in paths:
            status = import_hsd.load(self, context, path, self.offset, self.section, self.data_type, self.import_animation, self.ik_hack, self.max_frame, self.use_max_frame)
            #tracer.runctx('import_hsd.load(self, context, path, self.offset, self.section)', globals(), locals())
            #r = tracer.results()
            #r.write_results(show_missing=False, coverdir=".")
            if not 'FINISHED' in status:
                return status

        return {'FINISHED'}

@orientation_helper(axis_forward='Y', axis_up='Z')
class ExportHSD(bpy.types.Operator, ExportHelper):

    bl_idname = "export_scene.dat"
    bl_label = "Export Dat"
    filename_ext = ".dat"

    filter_glob = StringProperty(default="*.dat", options={'HIDDEN'})

    use_selection: BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=False,
    )
    global_scale: FloatProperty(
        name="Scale",
        min=0.01, max=1000.0,
        default=1.0,
    )
    use_scene_unit: BoolProperty(
        name="Scene Unit",
        description="Apply current scene's unit (as defined by unit scale) to exported data",
        default=False,
    )
    ascii: BoolProperty(
        name="Ascii",
        description="Save the file in ASCII file format",
        default=False,
    )
    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply the modifiers before saving",
        default=True,
    )
    batch_mode: EnumProperty(
        name="Batch Mode",
        items=(
            ('OFF', "Off", "All data in one file"),
            ('OBJECT', "Object", "Each object as a file"),
        ),
    )

    use_mesh_modifiers = BoolProperty(
            name="Apply Modifiers",
            description="Apply Modifiers to the exported mesh",
            default=True,
            )
    # use_normals = BoolProperty(
    #         name="Normals",
    #         description="Export Normals for smooth and "
    #                     "hard shaded faces "
    #                     "(hard shaded faces will be exported "
    #                     "as individual faces)",
    #         default=True,
    #         )
    # use_uv_coords = BoolProperty(
    #         name="UVs",
    #         description="Export the active UV layer",
    #         default=True,
    #         )
    # use_colors = BoolProperty(
    #         name="Vertex Colors",
    #         description="Export the active vertex color layer",
    #         default=True,
    #         )


    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        import os
        import itertools
        from mathutils import Matrix
        from . import stl_utils
        from . import blender_utils
        # from . import export_ply

        scene = context.scene
        if self.use_selection:
            data_seq = context.selected_objects
        else:
            data_seq = scene.objects

        keywords = self.as_keywords(
            ignore=(
                "axis_forward",
                "axis_up",
                "use_selection",
                "global_scale",
                "check_existing",
                "filter_glob",
                "use_scene_unit",
                "use_mesh_modifiers",
                "batch_mode"
            ),
        )

        global_scale = self.global_scale
        global_scale *= scene.unit_settings.scale_length

        global_matrix = axis_conversion(
            to_forward=self.axis_forward,
            to_up=self.axis_up,
        ).to_4x4() @ Matrix.Scale(global_scale, 4)

    
        # global_matrix = axis_conversion(to_forward=self.axis_forward,
        #                                 to_up=self.axis_up,
        #                                 ).to_4x4() * Matrix.Scale(self.global_scale, 4)

        prefix = os.path.splitext(self.filepath)[0]
        keywords_temp = keywords.copy()

        faces = itertools.chain.from_iterable(
                blender_utils.faces_from_mesh(ob, global_matrix, self.use_mesh_modifiers)
                for ob in data_seq)

        stl_utils.write_stl(faces=faces, **keywords)

        # For each object make a file
        # for ob in data_seq:
        #     faces = blender_utils.faces_from_mesh(ob, global_matrix, self.use_mesh_modifiers)
        #     keywords_temp["filepath"] = prefix + bpy.path.clean_name(ob.name) + ".dat"
        #     stl_utils.write_stl(faces=faces, **keywords_temp)

        # keywords["global_matrix"] = global_matrix

        # filepath = self.filepath
        # filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        return {'FINISHED'}

        # return export_ply.save(self, context, **keywords)

    def draw(self, context):
        pass

        # layout = self.layout

        # row = layout.row()
        # row.prop(self, "use_mesh_modifiers")
        # row.prop(self, "use_normals")
        # row = layout.row()
        # row.prop(self, "use_uv_coords")
        # row.prop(self, "use_colors")

        # layout.prop(self, "axis_forward")
        # layout.prop(self, "axis_up")
        # layout.prop(self, "global_scale")

def menu_func_import(self, context):
    self.layout.operator(ImportHSD.bl_idname, text="Gamecube Dat Model (.dat)")


def menu_func_export(self, context):
    self.layout.operator(ExportHSD.bl_idname, text="Gamecube Dat Model (.dat)")


classes = (
    ImportHSD,
    ExportHSD,
    )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()