package org.ecpd.bridge;

import java.io.FileWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Deterministic synthetic motor assembly used in --mock mode. Geometry is a
 * simple indexed box mesh repeated across definitions so downstream tooling
 * can validate transforms/hierarchy without geometry fidelity. Identifiers
 * mimic a typical Creo motor package (root assembly + parts).
 */
public final class MockAssembly {

    public static final String[] PARTS = {
        "housing.prt", "stator.prt", "rotor.prt", "shaft.prt",
        "front_bearing.prt", "rear_bearing.prt", "fan.prt", "cover.prt"
    };

    public static void extract(Path input, Path outDir, Log log) {
        log.info("mock extract: reading " + (input == null ? "synthetic" : input));
        if (input != null && !Files.isDirectory(input)) {
            throw new Bridge.BridgeError("MISSING_INPUT",
                "mock mode expects <zipDir> as the (pre-extracted) directory");
        }
        Path inter = outDir.resolve("intermediate.json");
        write(inter, canonicalJson(input));
        Path mesh = outDir.resolve("meshes");
        writeMeshes(mesh);
        log.info("mock extract: wrote " + inter + " and 1 shared mesh buffer per part");
    }

    static String canonicalJson(Path input) {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("schemaVersion", "1.0");
        root.put("projectId", "mock-job");
        root.put("name", "Mock Motor");
        root.put("source", "Creo (mock bridge)");
        root.put("rootAssemblyDefinitionId", "motor.asm");
        Map<String, Object> units = new LinkedHashMap<>();
        units.put("sourceLength", "mm");
        units.put("runtimeLength", "mm");
        units.put("sourceToRuntimeScale", 1.0);
        root.put("units", units);

        Map<String, Object> defs = new LinkedHashMap<>();
        for (String p : PARTS) {
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("definitionId", p.toUpperCase());
            d.put("modelType", "part");
            d.put("name", p);
            d.put("sourceFile", p);
            d.put("partNumber", "MOCK-" + p.replace(".prt", "").toUpperCase());
            d.put("description", "Mock " + p);
            d.put("parameters", new LinkedHashMap<>());
            d.put("units", "mm");
            d.put("materials", List.of());
            Map<String, Object> mass = new LinkedHashMap<>();
            mass.put("mass", 0.0); mass.put("density", 0.0); mass.put("volume", 0.0);
            mass.put("surfaceArea", 0.0);
            mass.put("centerOfGravity", List.of(0.0, 0.0, 0.0));
            mass.put("inertiaTensor", List.of());
            d.put("massProperties", mass);
            Map<String, Object> bounds = new LinkedHashMap<>();
            bounds.put("min", List.of(-20.0, -20.0, -20.0));
            bounds.put("max", List.of(20.0, 20.0, 20.0));
            d.put("bounds", bounds);
            d.put("geometryRef", "mesh_" + p.replace(".prt", ""));
            defs.put(p.toUpperCase(), d);
        }
        root.put("definitions", defs);

        Map<String, Object> occs = new LinkedHashMap<>();
        int idx = 0;
        for (String p : PARTS) {
            Map<String, Object> o = new LinkedHashMap<>();
            o.put("occurrenceId", "MOOTOR/" + (idx++));
            o.put("definitionId", p.toUpperCase());
            o.put("parentOccurrenceId", null);
            o.put("children", List.of());
            o.put("componentPath", List.of(idx));
            double[][] t = identity();
            o.put("transform", flatten(t));
            o.put("visible", true);
            o.put("suppressed", false);
            o.put("skeleton", false);
            occs.put(o.get("occurrenceId").toString(), o);
        }
        root.put("occurrences", occs);
        root.put("explodedStates", List.of());
        root.put("mechanisms", List.of());
        root.put("workingPrinciple", List.of());
        Map<String, Object> conversion = new LinkedHashMap<>();
        conversion.put("bridgeVersion", Bridge.VERSION);
        conversion.put("mode", "mock");
        conversion.put("input", input == null ? "synthetic" : input.toString());
        root.put("conversion", conversion);

        StringBuilder sb = new StringBuilder();
        Bridge.Json.writeValue(sb, root);
        return sb.toString();
    }

    static void writeMeshes(Path meshDir) {
        try {
            Files.createDirectories(meshDir);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        for (String p : PARTS) {
            Path f = meshDir.resolve(p.replace(".prt", "") + ".mesh");
            write(f, simpleBoxMesh());
        }
        Path idx = meshDir.resolve("index.json");
        write(idx, "{\"meshDir\":\"" + meshDir + "\"}");
    }

    static String simpleBoxMesh() {
        // 8 verts, 6 quads -> triangles (36 indices)
        StringBuilder sb = new StringBuilder();
        sb.append("{\"vertices\":[[-20,-20,-20],[20,-20,-20],[20,20,-20],[-20,20,-20],[-20,-20,20],[20,-20,20],[20,20,20],[-20,20,20]],"
            + "\"indices\":[0,1,2,0,2,3,4,6,5,4,7,6,0,5,1,0,4,5,2,6,1,1,6,5,4,3,7,4,0,3,2,6,3,3,6,7]]}");
        return sb.toString();
    }

    static void write(Path p, String body) {
        try {
            Files.createDirectories(p.getParent());
            try (FileWriter w = new FileWriter(p.toFile(), StandardCharsets.UTF_8)) {
                w.write(body);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    static double[][] identity() {
        return new double[][]{{1,0,0,0},{0,1,0,0},{0,0,1,0},{0,0,0,1}};
    }

    static List<Double> flatten(double[][] m) {
        java.util.List<Double> out = new java.util.ArrayList<>(16);
        for (double[] row : m) for (double v : row) out.add(v);
        return out;
    }

    /** Trivial log abstraction. */
    static final class Log {
        public static Log sink() { return new Log(); }
        public void info(String msg) { System.err.println("[creo-bridge] " + msg); }
    }
}
