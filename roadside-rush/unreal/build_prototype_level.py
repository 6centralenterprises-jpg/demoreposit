"""
Roadside Rush - prototype level builder (a 6 Central Enterprises portfolio project)

Run this INSIDE the Unreal Editor (UE5) on a project made from the Vehicle
template. It builds a first test course in front of the Player Start:

  * two rows of traffic cones that the car can knock over (physics on)
  * a "stranded driver" car at the end of the road
  * a checkpoint trigger box in front of the stranded car
  * a floating sign so you can find it

How to run:
  1. Edit > Plugins > search "Python Editor Script Plugin" > Enabled > restart.
  2. Tools > Execute Python Script... > pick this file.
  3. Press Play and drive forward.

Safe to run again: it deletes what it built last time (everything in the
"RoadsideRush" Outliner folder) and rebuilds. One Ctrl+Z undoes the whole run.
It only uses engine shapes and, if present, Starter Content materials, so it
does not create or change any asset files.
"""

import unreal

FOLDER = "RoadsideRush"

# Course layout, in Unreal units (100 units = 1 metre).
CONE_START = 1000      # first cones, distance ahead of the Player Start
CONE_END = 12000       # last cones
CONE_SPACING = 800
LANE_HALF_WIDTH = 700  # cones sit this far left and right of the centre line
CHECKPOINT_AT = 13000
STRANDED_CAR_AT = 14000

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def load(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    return None


def first_existing(*paths):
    for p in paths:
        asset = load(p)
        if asset:
            return asset
    return None


CONE_MESH = load("/Engine/BasicShapes/Cone.Cone")
CUBE_MESH = load("/Engine/BasicShapes/Cube.Cube")
CONE_MAT = first_existing(
    "/Game/StarterContent/Materials/M_Metal_Gold.M_Metal_Gold",
    "/Game/StarterContent/Materials/M_Brick_Clay_New.M_Brick_Clay_New",
)
CAR_MAT = first_existing(
    "/Game/StarterContent/Materials/M_Metal_Burnished_Steel.M_Metal_Burnished_Steel",
    "/Game/StarterContent/Materials/M_Metal_Steel.M_Metal_Steel",
)


def clear_previous_build():
    removed = 0
    for a in actors.get_all_level_actors():
        if str(a.get_folder_path()).startswith(FOLDER):
            actors.destroy_actor(a)
            removed += 1
    if removed:
        unreal.log(f"[RoadsideRush] Removed {removed} actors from the last build.")


def find_player_start():
    for a in actors.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart):
            return a
    return None


def place(origin, fwd, right, ahead, side, up):
    """World position `ahead` units forward, `side` units right, `up` units up."""
    return unreal.Vector(
        origin.x + fwd.x * ahead + right.x * side,
        origin.y + fwd.y * ahead + right.y * side,
        origin.z + up,
    )


def tag(actor, label, subfolder=""):
    actor.set_actor_label(label)
    actor.set_folder_path(FOLDER + ("/" + subfolder if subfolder else ""))


def spawn_mesh(mesh, material, location, yaw, scale, label, subfolder, physics):
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, location, unreal.Rotator(roll=0, pitch=0, yaw=yaw)
    )
    comp = actor.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(mesh)
    if material:
        comp.set_material(0, material)
    actor.set_actor_scale3d(scale)
    if physics:
        # Spawned a little above the ground; they drop into place when you press Play.
        comp.set_simulate_physics(True)
    tag(actor, label, subfolder)
    return actor


def build():
    start = find_player_start()
    if start is None:
        unreal.log_error(
            "[RoadsideRush] No Player Start in this level. Open the Vehicle "
            "template's map (or add a Player Start) and run again."
        )
        return

    origin = start.get_actor_location()
    fwd = start.get_actor_forward_vector()
    right = start.get_actor_right_vector()
    yaw = start.get_actor_rotation().yaw

    count = 0

    # 1. Cone-lined lane
    d, i = CONE_START, 1
    while d <= CONE_END:
        for side, name in ((-LANE_HALF_WIDTH, "L"), (LANE_HALF_WIDTH, "R")):
            spawn_mesh(
                CONE_MESH, CONE_MAT,
                place(origin, fwd, right, d, side, 50),
                yaw, unreal.Vector(0.4, 0.4, 0.6),
                f"RR_Cone_{name}{i:02d}", "Cones", physics=True,
            )
            count += 1
        d += CONE_SPACING
        i += 1

    # 2. Stranded driver's car (a placeholder block for now)
    spawn_mesh(
        CUBE_MESH, CAR_MAT,
        place(origin, fwd, right, STRANDED_CAR_AT, 400, 120),
        yaw + 15, unreal.Vector(4.5, 2.0, 1.4),
        "RR_StrandedCar", "Mission", physics=True,
    )
    count += 1

    # 3. Checkpoint trigger: tall, so it works even if the ground is uneven
    trigger = actors.spawn_actor_from_class(
        unreal.TriggerBox,
        place(origin, fwd, right, CHECKPOINT_AT, 0, 0),
        unreal.Rotator(roll=0, pitch=0, yaw=yaw),
    )
    trigger.set_actor_scale3d(unreal.Vector(4.0, 20.0, 15.0))
    tag(trigger, "RR_Checkpoint_StrandedDriver", "Mission")
    count += 1

    # 4. Floating sign facing the driver
    sign = actors.spawn_actor_from_class(
        unreal.TextRenderActor,
        place(origin, fwd, right, STRANDED_CAR_AT, 400, 700),
        unreal.Rotator(roll=0, pitch=0, yaw=yaw + 180),
    )
    text = sign.text_render
    text.set_editor_property("text", "STRANDED DRIVER - HELP NEEDED")
    text.set_editor_property("world_size", 120.0)
    text.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    text.set_editor_property("text_render_color", unreal.Color(r=255, g=140, b=0, a=255))
    tag(sign, "RR_Sign_StrandedDriver", "Mission")
    count += 1

    unreal.log(f"[RoadsideRush] Built {count} actors in Outliner folder '{FOLDER}'. Press Play.")


with unreal.ScopedEditorTransaction("Build Roadside Rush prototype"):
    clear_previous_build()
    build()
