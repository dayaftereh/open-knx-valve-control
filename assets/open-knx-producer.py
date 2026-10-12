# PlatformIO/SCons pre-script. Canonical product XML is the sole source for
# KNX object numbering and parameter offsets. Errors must fail the build.
Import("env")

import importlib.util
import os
import shutil
import subprocess

project_dir = env.get("PROJECT_DIR")
xml_path = os.path.normpath(
    os.path.join(project_dir, "assets", "open-knx-valve-control.xml"))
header_path = os.path.normpath(
    os.path.join(env.get("PROJECT_INCLUDE_DIR"), "knxprod.hpp"))

producer = os.environ.get("OPENKNX_PRODUCER") or shutil.which("OpenKNXproducer.exe")
if not producer:
    raise RuntimeError("OpenKNXproducer.exe not installed/on PATH")

os.makedirs(os.path.dirname(header_path), exist_ok=True)
subprocess.run([producer, "create", "-h", header_path, xml_path],
               check=True, shell=False)

helper_path = os.path.join(project_dir, "assets", "knxprod_header_fix.py")
spec = importlib.util.spec_from_file_location("knxprod_header_fix", helper_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load header normalization helper")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
normalized = helper.normalize_header(header_path)
print("OpenKNX product header generated and validated:", normalized, "KO")
