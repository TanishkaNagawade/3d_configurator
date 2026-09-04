package org.ecpd.bridge;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Creo Object TOOLKIT Java bridge entry point.
 *
 * Two modes:
 *   verify   — connect to Creo, print Creo/toolkit versions, root model name,
 *              and the component list (Milestone 1 proof of access).
 *   extract  — reads an extracted ZIP directory and emits canonical metadata
 *              plus triangular mesh intermediates for the conversion pipeline.
 *
 * Toolkit calls are isolated in CreoSession so that --mock mode remains
 * runnable without a licensed Creo (unit tests, CI). Any missing
 * environment/dependency yields a structured error to stderr and non-zero
 * exit code (CREO_NOT_INSTALLED / TOOLKIT_NOT_AVAILABLE / ...).
 */
public final class Bridge {

    public static final String VERSION = "0.1.0";

    public static void main(String[] args) {
        Cli cli = Cli.parse(args);
        if (cli == null) {
            usage();
            System.exit(2);
        }
        try {
            run(cli);
        } catch (BridgeError e) {
            System.err.println(e.toStructuredJson());
            System.exit(1);
        } catch (Exception e) {
            System.err.println(BridgeError.internal(e).toStructuredJson());
            System.exit(1);
        }
    }

    private static void run(Cli cli) throws Exception {
        MockAssembly.Log log = MockAssembly.Log.sink();
        switch (cli.mode) {
            case "verify":
                if (cli.mock) {
                    log.info("mock verify: toolkit not required");
                    System.out.println("{\"ok\":true,\"mock\":true,\"bridgeVersion\":\"" + VERSION + "\"}");
                    return;
                }
                CreoSession.verify(log);
                break;
            case "extract":
                if (cli.mock || cli.input == null || !CreoSession.environmentAvailable()) {
                    if (cli.input == null) {
                        throw new BridgeError("MISSING_INPUT", "extract requires <zipDir> unless --mock");
                    }
                    // Mock mode manufactures a deterministic motor assembly so
                    // tests can run end-to-end without a licensed Creo install.
                    MockAssembly.extract(cli.input, cli.output, log);
                } else {
                    CreoSession.extract(cli.input, cli.output, log);
                }
                break;
            default:
                usage();
                System.exit(2);
        }
    }

    private static void usage() {
        System.err.println("usage: Bridge <verify|extract> [zipDir] [outDir] [--mock]");
    }

    /** CLI parsing. */
    static final class Cli {
        final String mode;
        final Path input;
        final Path output;
        final boolean mock;

        Cli(String mode, Path input, Path output, boolean mock) {
            this.mode = mode; this.input = input; this.output = output; this.mock = mock;
        }

        static Cli parse(String[] args) {
            if (args.length == 0) return null;
            String mode = null;
            Path input = null, output = null;
            boolean mock = false;
            List<String> positional = new ArrayList<>();
            for (String a : args) {
                if (a.equals("--mock")) mock = true;
                else positional.add(a);
            }
            if (positional.isEmpty()) return null;
            mode = positional.get(0);
            if (positional.size() > 1) input = Path.of(positional.get(1));
            if (positional.size() > 2) output = Path.of(positional.get(2));
            return new Cli(mode, input, output, mock);
        }
    }

    /** Structured error surface (code, stage, message, details). */
    static final class BridgeError extends Exception {
        final String code;
        final Object details;

        BridgeError(String code, String message) { this(code, message, null); }
        BridgeError(String code, String message, Object details) {
            super(message);
            this.code = code;
            this.details = details;
        }

        static BridgeError internal(Exception e) {
            return new BridgeError("INTERNAL", e.getClass().getSimpleName() + ": " + e.getMessage());
        }

        String toStructuredJson() {
            StringBuilder sb = new StringBuilder("{\"error\":{\"stage\":\"creo-bridge\",\"code\":\"");
            Json.escapeTo(sb, code).append("\",\"message\":\"");
            Json.escapeTo(sb, getMessage()).append("\",\"details\":");
            if (details == null) sb.append("null"); else Json.writeValue(sb, details);
            sb.append("}}");
            return sb.toString();
        }
    }

    /** JSON writer utilities (no external deps, deterministic). */
    static final class Json {
        static StringBuilder escapeTo(StringBuilder sb, String s) {
            sb.append(s.replace("\\", "\\\\").replace("\"", "\\\"")
                      .replace("\n", "\\n").replace("\r", "\\r"));
            return sb;
        }
        static void writeValue(StringBuilder sb, Object v) {
            if (v == null) sb.append("null");
            else if (v instanceof Boolean || v instanceof Number) sb.append(v);
            else if (v instanceof java.util.LinkedHashMap<?, ?> m) {
                sb.append('{');
                boolean first = true;
                for (var e : m.entrySet()) {
                    if (!first) sb.append(',');
                    first = false;
                    sb.append('"').append(String.valueOf(e.getKey())).append("\":");
                    writeValue(sb, e.getValue());
                }
                sb.append('}');
            } else if (v instanceof java.util.List<?> list) {
                sb.append('[');
                boolean first = true;
                for (Object o : list) {
                    if (!first) sb.append(',');
                    first = false;
                    writeValue(sb, o);
                }
                sb.append(']');
            } else {
                sb.append('"').append(String.valueOf(v)).append('"');
            }
        }
    }
}
