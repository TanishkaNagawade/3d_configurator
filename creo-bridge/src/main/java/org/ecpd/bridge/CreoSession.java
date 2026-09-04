package org.ecpd.bridge;

import java.io.File;

/**
 * Real Creo Object TOOLKIT Java integration points. The class deliberately
 * contains no invented toolkit signatures: it resolves the environment
 * (install dir, toolkit jars, Java session) and then throws structured
 * capability-report errors when it is truly missing. The actual model /
 * traversal / tessellation calls must be implemented against the locally
 * installed Object TOOLKIT Java API (see PLACEHOLDER block at the bottom).
 */
public final class CreoSession {

    public static boolean environmentAvailable() {
        if (System.getenv("CREO_INSTALL_DIR") == null) return false;
        if (System.getenv("CREO_TOOLKIT_JAVA_DIR") == null) return false;
        if (System.getenv("JAVA_HOME") == null) return false;
        return true;
    }

    /** Milestone 1: environment check + capability probe. */
    public static void verify(MockAssembly.Log log) {
        String creo = System.getenv("CREO_INSTALL_DIR");
        String toolkit = System.getenv("CREO_TOOLKIT_JAVA_DIR");
        String javaH = System.getenv("JAVA_HOME");
        if (creo == null) {
            throw new Bridge.BridgeError("CREO_NOT_INSTALLED",
                "CREO_INSTALL_DIR is unset — point it at a licensed Creo Parametric installation.");
        }
        if (javaH == null) {
            throw new Bridge.BridgeError("TOOLKIT_NOT_AVAILABLE",
                "JAVA_HOME must point to a JDK compatible with the local Creo Object TOOLKIT Java version.");
        }
        if (toolkit == null) {
            throw new Bridge.BridgeError("TOOLKIT_NOT_AVAILABLE",
                "CREO_TOOLKIT_JAVA_DIR unset — needs the Object TOOLKIT (pfc.jar) from the installation.");
        }
        File pfc = new File(toolkit, "pfc.jar");
        if (!pfc.exists()) {
            throw new Bridge.BridgeError("TOOLKIT_NOT_AVAILABLE",
                "pfc.jar not found in CREO_TOOLKIT_JAVA_DIR=" + toolkit);
        }
        log.info("Environment ok; reaching into the Creo session is not possible "
                + "without implementing synchronous/async session setup — see PLACEHOLDER.");
        System.out.println("{\"ok\":false,\"code\":\"CREO_SESSION_UNAVAILABLE\","
            + "\"message\":\"Toolkit verified; session plumbing not implemented yet.\"}");
    }

    public static void extract(java.nio.file.Path input, java.nio.file.Path outDir,
            MockAssembly.Log log) {
        // Placeholder for genuine Object TOOLKIT Java extraction. The methods
        // below intentionally avoid fabricated signatures; they document the
        // shape that the real implementation will have (against local API docs).
        throw new Bridge.BridgeError("CREO_SESSION_UNAVAILABLE",
            "Native toolkit extraction not yet wired: use --mock or install/configure Creo. "
            + "The bridge stage expects <zipDir> and <outDir> like mock mode.");
    }
}
