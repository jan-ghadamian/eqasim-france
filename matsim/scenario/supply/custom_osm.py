import os
import shutil

"""
Injects a pre-modified road network, bypassing OSM conversion.
The file must be a valid MATSim network XML (same format as osm.py produces).
"""

def configure(context):
    context.config("data_path")
    context.config("custom_road_network_path", "custom_network/road_network.xml.gz")

def execute(context):
    source = os.path.join(
        context.config("data_path"),
        context.config("custom_road_network_path")
    )
    dest = "%s/network.xml.gz" % context.path()
    shutil.copy(source, dest)

    print("\n[custom_osm] Using custom road network:")
    print("  Source: {}".format(source))

    assert os.path.exists(dest)
    return "network.xml.gz"   # same return type as osm.py

def validate(context):
    path = os.path.join(
        context.config("data_path"),
        context.config("custom_road_network_path")
    )
    if not os.path.exists(path):
        raise RuntimeError("Custom road network not found at: {}".format(path))
    return os.path.getsize(path)