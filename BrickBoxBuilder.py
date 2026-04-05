bl_info = {
    "name": "BrickBoxBuilder",
    "author": "Saintmedium",
    "version": (1, 0),
    "blender": (5, 1, 0),
    "location": "3D View > Sidebar > Create",
    "category": "Mesh",
}

import bpy
import bmesh
from math import radians, ceil


# ===================== SAFE UPDATE SYSTEM =====================

def safe_update(func):
    def wrapper(self, context):
        if not context or not hasattr(context, "scene"):
            return
        
        props = context.scene.block_grid_props
        
        if props.is_updating:
            return
        
        props.is_updating = True
        try:
            func(self, context, props)
        finally:
            props.is_updating = False
    
    return wrapper


def update_total_blocks_count(props):
    """Обновляет подсчет общего количества блоков"""
    blocks_per_row = (props.count_length * 2) + (props.count_width * 2)
    props.total_blocks = blocks_per_row * props.count_rows


def calculate_actual_box_size(props):
    """Вычисляет реальные размеры коробки с учетом швов"""
    # Ширина коробки (X): (количество блоков по ширине * длина блока) + (швы между блоками)
    actual_width = (props.count_width * props.block_length) + ((props.count_width) * props.seam_thick) + props.block_width
    
    # Длина коробки (Y): (количество блоков по длине * длина блока) + (швы между блоками)
    actual_length = (props.count_length * props.block_length) + ((props.count_length) * props.seam_thick) + props.block_width
    
    # Высота коробки (Z): (количество рядов * высота блока) + (швы между рядами)
    actual_height = (props.count_rows * props.block_height) + ((props.count_rows - 1) * props.seam_thick)
    
    return actual_width, actual_length, actual_height


def update_display_sizes(props):
    """Обновляет отображаемые размеры коробки в свойствах"""
    actual_width, actual_length, actual_height = calculate_actual_box_size(props)
    props.display_width = actual_width
    props.display_length = actual_length
    props.display_height = actual_height


# ===================== UPDATE FUNCTIONS =====================

@safe_update
def update_count_width(self, context, props):
    """При изменении количества блоков пересчитывает ширину коробки"""
    actual_width, actual_length, actual_height = calculate_actual_box_size(props)
    props.display_width = actual_width
    props.display_length = actual_length
    props.display_height = actual_height
    update_total_blocks_count(props)


@safe_update
def update_count_length(self, context, props):
    """При изменении количества блоков пересчитывает длину коробки"""
    actual_width, actual_length, actual_height = calculate_actual_box_size(props)
    props.display_width = actual_width
    props.display_length = actual_length
    props.display_height = actual_height
    update_total_blocks_count(props)


@safe_update
def update_count_rows(self, context, props):
    """При изменении количества рядов пересчитывает высоту коробки"""
    actual_width, actual_length, actual_height = calculate_actual_box_size(props)
    props.display_width = actual_width
    props.display_length = actual_length
    props.display_height = actual_height
    update_total_blocks_count(props)


@safe_update
def update_block_width(self, context, props):
    """При изменении ширины блока пересчитывает размеры коробки"""
    if props.block_width > 0:
        update_display_sizes(props)


@safe_update
def update_block_length(self, context, props):
    """При изменении длины блока пересчитывает размеры коробки"""
    if props.block_length > 0:
        update_display_sizes(props)


@safe_update
def update_block_height(self, context, props):
    """При изменении высоты блока пересчитывает высоту коробки"""
    if props.block_height > 0:
        update_display_sizes(props)


@safe_update
def update_seam_thick(self, context, props):
    """При изменении толщины шва пересчитывает все размеры коробки"""
    update_display_sizes(props)


# ===================== BLOCK CREATION =====================

def create_block(block_width, block_length, block_height, block_name, collection_name, color=None, bevel_amount=0.001):
    """Создаёт отдельный блок с заданными размерами, центр тяжести в нижнем углу"""
    # Получаем или создаем коллекцию
    if collection_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(new_collection)
    else:
        new_collection = bpy.data.collections[collection_name]
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    
    # Масштабируем куб до нужных размеров
    for vertex in bm.verts:
        vertex.co.x *= block_width / 2.0
        vertex.co.y *= block_length / 2.0
        vertex.co.z *= block_height / 2.0
    
    # Смещаем чтобы нижний угол оказался в точке (0,0,0)
    for vertex in bm.verts:
        vertex.co.x += block_width / 2.0
        vertex.co.y += block_length / 2.0
        vertex.co.z += block_height / 2.0
    
    mesh = bpy.data.meshes.new(block_name)
    bm.to_mesh(mesh)
    bm.free()
    
    block_object = bpy.data.objects.new(block_name, mesh)
    new_collection.objects.link(block_object)
    
    # Применяем модификатор Bevel к блоку
    bevel_modifier = block_object.modifiers.new(name="Bevel", type='BEVEL')
    bevel_modifier.width = bevel_amount
    bevel_modifier.segments = 1
    bevel_modifier.limit_method = 'ANGLE'
    bevel_modifier.angle_limit = radians(30)
    
    # Применяем цвет к блоку
    if color:
        # Создаем уникальное имя материала на основе цвета
        material_name = f"BrickBox_Material_{int(color[0]*255)}_{int(color[1]*255)}_{int(color[2]*255)}"
        
        if material_name not in bpy.data.materials:
            material = bpy.data.materials.new(material_name)
            material.use_nodes = True
            
            # Очищаем стандартные ноды
            material.node_tree.nodes.clear()
            
            # Создаем нод Principle BSDF
            bsdf = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
            bsdf.location = (0, 0)
            
            # Создаем нод вывода материала
            output = material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (200, 0)
            
            # Связываем ноды
            material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
            
            # Устанавливаем цвет
            bsdf.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
            
            # Включаем отображение материала во вьюпорте
            material.diffuse_color = (color[0], color[1], color[2], 1.0)
        else:
            material = bpy.data.materials[material_name]
        
        # Назначаем материал блоку
        if len(block_object.data.materials) == 0:
            block_object.data.materials.append(material)
        else:
            block_object.data.materials[0] = material
        
        block_object.data.materials[0].use_fake_user = False
        block_object.show_wire = False
        block_object.display_type = 'TEXTURED'
    
    return block_object


# ===================== OPERATOR =====================

class OT_PlaceBlockGrid(bpy.types.Operator):
    """Создаёт сетку блоков с заданными размерами и швами"""
    bl_idname = "object.place_block_grid"
    bl_label = "Создать коробку"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.block_grid_props
        collection_name = props.collection_name
        
        # Если имя коллекции пустое, используем "BrickBox" по умолчанию
        if not collection_name:
            collection_name = "BrickBox"
        
        block_width = props.block_width
        block_length = props.block_length
        block_height = props.block_height
        blocks_count_x = props.count_width
        blocks_count_y = props.count_length
        rows_count = props.count_rows
        seam_thickness = props.seam_thick
        bevel_amount = props.bevel_amount
        
        # Получаем цвет
        block_color = props.block_color
        
        # Проверяем нужно ли применять цвет
        apply_color = props.apply_color
        
        # Базовое смещение по оси Y для первого ряда
        y_base_offset = block_width + seam_thickness
        
        for current_row in range(rows_count):
            # Вертикальное смещение для текущего ряда
            z_offset = current_row * (block_height + seam_thickness)
            
            # Проверяем четность ряда (начиная с 0)
            is_even_row = (current_row % 2 == 0)
            row_shift = block_width + seam_thickness
            
            # ==================== СТЕНА 1 (нижняя, по оси Y) ====================
            for i in range(blocks_count_y):
                y_position = (block_length * i) + (seam_thickness * i) if i > 0 else 0
                y_position = y_position + y_base_offset
                
                if is_even_row:
                    y_position = y_position - row_shift
                
                color = block_color if apply_color else None
                block = create_block(block_width, block_length, block_height, f"Wall1_Row{current_row}_Block{i}", collection_name, color, bevel_amount)
                block.location = (0, y_position, z_offset)
            
            # ==================== СТЕНА 2 (правая, по оси X), поворот 270° ====================
            wall2_start_x = block_width + seam_thickness
            wall2_total_y = (block_length * blocks_count_y) + (seam_thickness * (blocks_count_y - 1)) + y_base_offset
            
            for j in range(blocks_count_x):
                x_position = wall2_start_x + (block_length * j) + (seam_thickness * j)
                
                if is_even_row:
                    x_position = x_position - row_shift
                
                color = block_color if apply_color else None
                block = create_block(block_width, block_length, block_height, f"Wall2_Row{current_row}_Block{j}", collection_name, color, bevel_amount)
                block.location = (x_position, wall2_total_y, z_offset)
                block.rotation_euler.z = radians(270)
            
            # ==================== СТЕНА 3 (верхняя, по оси Y) ====================
            wall3_start_x = (blocks_count_x * block_length) + (blocks_count_x * seam_thickness)
            wall3_start_y = ((blocks_count_y - 1) * block_length) - block_width + ((blocks_count_y - 2) * seam_thickness) + y_base_offset
            
            for k in range(blocks_count_y):
                y_position = wall3_start_y - (block_length * k) - (seam_thickness * k)
                
                if is_even_row:
                    y_position = y_position + row_shift
                
                color = block_color if apply_color else None
                block = create_block(block_width, block_length, block_height, f"Wall3_Row{current_row}_Block{k}", collection_name, color, bevel_amount)
                block.location = (wall3_start_x, y_position, z_offset)
            
            # ==================== СТЕНА 4 (левая, по оси X), поворот 270° ====================
            wall4_start_y = -seam_thickness + y_base_offset
            
            for m in range(blocks_count_x):
                x_position = (block_length * m) + (seam_thickness * m)
                
                if is_even_row:
                    x_position = x_position + row_shift
                
                color = block_color if apply_color else None
                block = create_block(block_width, block_length, block_height, f"Wall4_Row{current_row}_Block{m}", collection_name, color, bevel_amount)
                block.location = (x_position, wall4_start_y, z_offset)
                block.rotation_euler.z = radians(270)
        
        # Обновляем отображаемые размеры коробки с учетом швов после создания
        actual_width, actual_length, actual_height = calculate_actual_box_size(props)
        props.display_width = actual_width
        props.display_length = actual_length
        props.display_height = actual_height
        
        update_total_blocks_count(props)
        
        if apply_color:
            self.report({'INFO'}, f"Создано блоков: {props.total_blocks} в коллекции '{collection_name}' | Размер коробки: {actual_width:.3f} x {actual_length:.3f} x {actual_height:.3f}")
        else:
            self.report({'INFO'}, f"Создано блоков: {props.total_blocks} в коллекции '{collection_name}' | Размер коробки: {actual_width:.3f} x {actual_length:.3f} x {actual_height:.3f}")
        
        return {'FINISHED'}


# ===================== PROPERTIES =====================

class BlockGridProperties(bpy.types.PropertyGroup):
    """Группа свойств для настройки сетки блоков"""
    
    is_updating: bpy.props.BoolProperty(default=False)
    
    collection_name: bpy.props.StringProperty(
        name="",
        default="BrickBox",
        description="Имя коллекции для хранения блоков"
    )
    
    # Отображаемые размеры коробки (только для чтения)
    display_width: bpy.props.FloatProperty(
        name="Ширина коробки (X)",
        default=2.2,
        description="Общая ширина коробки (вычисляется автоматически)"
    )
    
    display_length: bpy.props.FloatProperty(
        name="Длина коробки (Y)",
        default=2.2,
        description="Общая длина коробки (вычисляется автоматически)"
    )
    
    display_height: bpy.props.FloatProperty(
        name="Высота коробки (Z)",
        default=0.2,
        description="Общая высота коробки (вычисляется автоматически)"
    )
    
    # Размеры блока
    block_width: bpy.props.FloatProperty(
        name="Ширина блока (X)",
        default=0.3,
        min=0.01,
        step=0.01,
        precision=3,
        description="Размер блока по оси X",
        update=update_block_width
    )
    
    block_length: bpy.props.FloatProperty(
        name="Длина блока (Y)",
        default=0.6,
        min=0.01,
        step=0.01,
        precision=3,
        description="Размер блока по оси Y",
        update=update_block_length
    )
    
    block_height: bpy.props.FloatProperty(
        name="Высота блока (Z)",
        default=0.25,
        min=0.01,
        step=0.01,
        precision=3,
        description="Высота блока",
        update=update_block_height
    )
    
    # Количество блоков
    count_width: bpy.props.IntProperty(
        name="Кол-во по ширине",
        default=3,
        min=1,
        description="Количество блоков вдоль оси X",
        update=update_count_width
    )
    
    count_length: bpy.props.IntProperty(
        name="Кол-во по длине",
        default=3,
        min=1,
        description="Количество блоков вдоль оси Y",
        update=update_count_length
    )
    
    count_rows: bpy.props.IntProperty(
        name="Количество рядов",
        default=3,
        min=1,
        description="Количество рядов по высоте",
        update=update_count_rows
    )
    
    seam_thick: bpy.props.FloatProperty(
        name="Толщина шва",
        default=0.01,
        min=0.0,
        step=0.001,
        precision=3,
        description="Зазор между блоками",
        update=update_seam_thick
    )
    
    bevel_amount: bpy.props.FloatProperty(
        name="Bevel Amount",
        default=0.001,
        min=0.001,
        step=0.001,
        precision=3,
        description="Величина скругления краев блоков"
    )
    
    total_blocks: bpy.props.IntProperty(
        name="Всего блоков",
        default=0,
        description="Общее количество созданных блоков"
    )
    
    # Включение/выключение цвета
    apply_color: bpy.props.BoolProperty(
        name="Применить цвет",
        default=True,
        description="Применить выбранный цвет к блокам"
    )
    
    # Цвет блоков
    block_color: bpy.props.FloatVectorProperty(
        name="Цвет блоков",
        subtype='COLOR',
        default=(0.8, 0.2, 0.2),
        min=0.0,
        max=1.0,
        description="Цвет всех блоков"
    )


# ===================== UI =====================

class VIEW3D_PT_BlockPanel(bpy.types.Panel):
    bl_label = "BrickBoxBuilder"
    bl_idname = "VIEW3D_PT_block_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BrickBoxBuilder"

    def draw(self, context):
        layout = self.layout
        props = context.scene.block_grid_props

        # Текстовый бокс без метки
        layout.prop(props, "collection_name")
        layout.separator()
        
        # Размеры коробки (только для чтения)
        box = layout.box()
        box.label(text="Размеры коробки:", icon="MESH_CUBE")
        row = box.row()
        row.enabled = False  # Делаем поля только для чтения
        row.prop(props, "display_width")
        row = box.row()
        row.enabled = False
        row.prop(props, "display_length")
        row = box.row()
        row.enabled = False
        row.prop(props, "display_height")
        
        layout.separator(factor=0.5)
        
        # Размеры блоков
        box = layout.box()
        box.label(text="Размеры блоков:", icon="CUBE")
        box.prop(props, "block_width")
        box.prop(props, "block_length")
        box.prop(props, "block_height")
        
        layout.separator(factor=0.5)
        
        # Количество блоков
        box = layout.box()
        box.label(text="Количество блоков:", icon="GRID")
        box.prop(props, "count_width")
        box.prop(props, "count_length")
        box.prop(props, "count_rows")
        
        layout.separator(factor=0.5)
        
        # Остальные параметры
        column = layout.column(align=True)
        column.prop(props, "seam_thick")
        column.separator(factor=0.5)
        column.prop(props, "bevel_amount")
        column.separator(factor=0.5)
        
        # Настройки цвета
        box = layout.box()
        box.label(text="Настройки цвета:", icon="COLOR")
        box.prop(props, "apply_color")
        
        if props.apply_color:
            box.prop(props, "block_color")
            
            # Подсказка
            col = box.column(align=True)
            col.scale_y = 0.7
            col.label(text="Совет: Включите 'Viewport Shading'", icon="INFO")
            col.label(text="в режим 'Material Preview' или 'Rendered'")
        
        column.separator(factor=0.5)
        
        # Отображение количества блоков
        row = layout.row()
        row.label(text=f"Всего блоков: {props.total_blocks}")
        
        column.separator(factor=0.5)
        layout.operator("object.place_block_grid", text="Создать коробку", icon="GRID")


# ===================== REGISTER =====================

classes = (
    BlockGridProperties,
    OT_PlaceBlockGrid,
    VIEW3D_PT_BlockPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.block_grid_props = bpy.props.PointerProperty(type=BlockGridProperties)
    
    # Инициализируем отображаемые размеры
    def init_props():
        props = bpy.context.scene.block_grid_props
        if props:
            update_display_sizes(props)
            update_total_blocks_count(props)
    
    # Отложенная инициализация
    bpy.app.timers.register(lambda: init_props() or None, first_interval=0.1)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.block_grid_props


if __name__ == "__main__":
    register()
