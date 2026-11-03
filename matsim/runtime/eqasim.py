import os, os.path, shutil
from pathlib import Path

import matsim.runtime.git as git
import matsim.runtime.java as java
import matsim.runtime.maven as maven

DEFAULT_EQASIM_VERSION = "2.0.0"
DEFAULT_EQASIM_BRANCH = "develop"
DEFAULT_EQASIM_COMMIT = "1995b11"
DEFAULT_EQASIM_REPOSITORY = "https://github.com/eqasim-org/eqasim-java.git"

def configure(context):
    git.configure(context)
    java.configure(context)
    maven.configure(context)

    context.config("eqasim_version", DEFAULT_EQASIM_VERSION)
    context.config("eqasim_branch", DEFAULT_EQASIM_BRANCH)
    context.config("eqasim_commit", DEFAULT_EQASIM_COMMIT)
    context.config("eqasim_repository", DEFAULT_EQASIM_REPOSITORY)
    context.config("eqasim_path", "")
    context.config("eqasim_local_source", "")

    # ASC values to bake into IDFModeParameters.java at compile time
    context.config("asc_car",  -2.00)
    context.config("asc_bike",  2.00)
    context.config("asc_pt",    0.00)
    context.config("asc_walk",  1.43)

def run(context, command, arguments, cwd = None):
    # Make sure there is a dependency
    jar_path = context.stage("matsim.runtime.eqasim")
    jar_path = "{}/{}".format(context.path("matsim.runtime.eqasim"), jar_path)
    java.run(context, command, arguments, jar_path, cwd=cwd)

def execute(context):
    version = context.config("eqasim_version")
    local_source = context.config("eqasim_local_source")
    jar_path_prebuilt = context.config("eqasim_path")

    if jar_path_prebuilt != "":
        # Case 1: use a prebuilt JAR directly
        print("Using prebuilt eqasim-java JAR: %s" % jar_path_prebuilt)
        os.makedirs("%s/eqasim-java/ile_de_france/target" % context.path())
        shutil.copy(jar_path_prebuilt,
            "%s/eqasim-java/ile_de_france/target/ile_de_france-%s.jar" % (context.path(), version))
        
    elif local_source != "":
        # Case 2: build from a local source folder, no git involved
        print("Building eqasim-java from local source: %s" % local_source)
        maven.run(context, [
            "-Pstandalone", "--projects", "ile_de_france", "--also-make",
            "package", "-DskipTests=true"
        ], cwd=local_source)

        built_jar = "%s/ile_de_france/target/ile_de_france-%s.jar" % (local_source, version)
        if not os.path.exists(built_jar):
            raise RuntimeError("JAR was not created. Wrong eqasim_version specified?")

        # Copy into the cache so the pipeline can find it in the expected place
        os.makedirs("%s/eqasim-java/ile_de_france/target" % context.path(), exist_ok=True)
        shutil.copy(built_jar,
            "%s/eqasim-java/ile_de_france/target/ile_de_france-%s.jar" % (context.path(), version))
        
    else:
        # Case 3: clone from git and build
        print("Cloning and building eqasim-java from git: %s" % context.config("eqasim_repository"))
        branch = context.config("eqasim_branch")
        git.run(context, [
            "clone", "--single-branch", "-b", branch,
            context.config("eqasim_repository"), "eqasim-java"
        ])

        commit = context.config("eqasim_commit")
        git.run(context, [
            "checkout", commit
        ], cwd="%s/eqasim-java" % context.path())

        # ── Patch IDFModeParameters.java with scenario ASC values ──
        idf_path = Path(
            context.path(),
            "eqasim-java", "ile_de_france", "src", "main", "java",
            "org", "eqasim", "ile_de_france",
            "mode_choice", "parameters", "IDFModeParameters.java"
        )
        idf_path.write_text(
            _generate_idf_mode_parameters({
                "car":  context.config("asc_car"),
                "bike": context.config("asc_bike"),
                "pt":   context.config("asc_pt"),
                "walk": context.config("asc_walk"),
            }),
            encoding="utf-8",
        )
        print("IDFModeParameters.java patched with ASC: car=%.4f bike=%.4f pt=%.4f walk=%.4f" % (
            context.config("asc_car"), context.config("asc_bike"),
            context.config("asc_pt"),  context.config("asc_walk"),
        ))
        # ────────────────────────────────────────────────────────────

        maven.run(context, [
            "-Pstandalone", "--projects", "ile_de_france", "--also-make",
            "package", "-DskipTests=true"
        ], cwd="%s/eqasim-java" % context.path())

        if not os.path.exists("%s/eqasim-java/ile_de_france/target/ile_de_france-%s.jar" % (context.path(), version)):
            raise RuntimeError("The JAR was not created correctly. Wrong eqasim_version specified?")

    return "eqasim-java/ile_de_france/target/ile_de_france-%s.jar" % version

def validate(context):
    git.validate(context)
    java.validate(context)
    maven.validate(context)

    # Case 1: prebuilt JAR
    path = context.config("eqasim_path")
    if path != "":
        if not os.path.exists(path):
            raise RuntimeError("Cannot find eqasim JAR at: %s" % path)
        return os.path.getmtime(path)

    # Case 2: local source folder
    local_source = context.config("eqasim_local_source")
    if local_source != "":
        if not os.path.exists(local_source):
            raise RuntimeError("Cannot find local eqasim source at: %s" % local_source)
        # Walk the source tree so any file change triggers a rebuild
        latest_mtime = 0
        for root, dirs, files in os.walk(local_source):
            # skip the target folder — those are build artifacts, not source changes
            dirs[:] = [d for d in dirs if d != "target"]
            for f in files:
                if f.endswith(".java") or f.endswith(".xml"):
                    mtime = os.path.getmtime(os.path.join(root, f))
                    latest_mtime = max(latest_mtime, mtime)
        return latest_mtime

    # Case 3: git — no extra validation needed
    return True

def _generate_idf_mode_parameters(asc: dict) -> str:
    return f"""package org.eqasim.ile_de_france.mode_choice.parameters;

import org.eqasim.core.simulation.mode_choice.parameters.ModeParameters;

public class IDFModeParameters extends ModeParameters {{
    public class IDFCarParameters {{
        public double betaInsideUrbanArea;
        public double betaCrossingUrbanArea;
    }}

    public class IDFBikeParameters {{
        public double betaInsideUrbanArea;
    }}

    public final IDFCarParameters idfCar = new IDFCarParameters();
    public final IDFBikeParameters idfBike = new IDFBikeParameters();

    public static IDFModeParameters buildDefault() {{
        IDFModeParameters parameters = new IDFModeParameters();

        parameters.betaCost_u_MU = -0.206;
        parameters.lambdaCostEuclideanDistance = -0.4;
        parameters.referenceEuclideanDistance_km = 40.0;

        parameters.car.alpha_u = {asc['car']};
        parameters.car.betaTravelTime_u_min = -0.06;
        parameters.car.additionalAccessEgressWalkTime_min = 4.0;
        parameters.car.constantParkingSearchPenalty_min = 4.0;
        parameters.idfCar.betaInsideUrbanArea = -0.5;
        parameters.idfCar.betaCrossingUrbanArea = -1.0;

        parameters.pt.alpha_u = {asc['pt']};
        parameters.pt.betaLineSwitch_u = -0.17;
        parameters.pt.betaInVehicleTime_u_min = -0.017;
        parameters.pt.betaWaitingTime_u_min = -0.0484;
        parameters.pt.betaAccessEgressTime_u_min = -0.0804;

        parameters.bike.alpha_u = {asc['bike']};
        parameters.bike.betaTravelTime_u_min = -0.05;
        parameters.bike.betaAgeOver18_u_a = -0.0496;
        parameters.idfBike.betaInsideUrbanArea = 1.5;

        parameters.walk.alpha_u = {asc['walk']};
        parameters.walk.betaTravelTime_u_min = -0.15;

        return parameters;
    }}
}}
"""