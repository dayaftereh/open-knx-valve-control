Import("env")
from platformio.builder.tools.piolib import ProjectAsLibBuilder, PackageItem, LibBuilderBase

import os
import subprocess

exe = "OpenKNXproducer.exe"

xmlFileName = "./assets/open-knx-valve-control.xml"
projectDir = env.get("PROJECT_DIR")
xmlPath = os.path.normpath(os.path.join(projectDir, xmlFileName))

includeDir = env.get("PROJECT_INCLUDE_DIR")
os.makedirs(includeDir, exist_ok=True)
hardwareIncludeFileName = "knxprod.hpp"
hardwareIncludePath = os.path.normpath(os.path.join(includeDir, hardwareIncludeFileName))

try:
   result = subprocess.run([exe, 'create', "-h", hardwareIncludePath, xmlPath], shell=True, check=True)
 
except subprocess.CalledProcessError:
    pass