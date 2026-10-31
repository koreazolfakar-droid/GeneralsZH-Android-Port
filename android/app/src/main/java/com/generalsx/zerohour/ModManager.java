/*
**  Command & Conquer Generals Zero Hour(tm)
**  Copyright 2025 Electronic Arts Inc.
**
**  This program is free software: you can redistribute it and/or modify
**  it under the terms of the GNU General Public License as published by
**  the Free Software Foundation, either version 3 of the License, or
**  (at your option) any later version.
*/

package com.generalsx.zerohour;

import android.content.Context;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * GeneralsX @feature Android port 04/10/2026 Phase 1 mod-manager state.
 *
 * Mods are isolated under <selected game folder>/Mods/. One direct child can
 * be active at a time. The active choice is stored by child name, never by an
 * arbitrary absolute path, so changing the game folder cannot accidentally
 * keep pointing at files outside the new install.
 *
 * A mod entry may be either a directory (the engine loads every .big inside
 * it through its retail -mod directory path) or one .big archive directly.
 */
final class ModManager {
    private static final String PREF_ACTIVE_MOD = "active_mod";
    private static final String MODS_DIR = "Mods";

    private ModManager() {}

    static File gameRoot(Context ctx) {
        String path = ctx.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE)
            .getString(SetupActivity.PREF_GAME_PATH, null);
        if (path == null || path.trim().isEmpty()) {
            return null;
        }
        return new File(path);
    }

    static File modsRoot(Context ctx) {
        File game = gameRoot(ctx);
        return game == null ? null : new File(game, MODS_DIR);
    }

    static List<File> listMods(Context ctx) {
        File root = modsRoot(ctx);
        if (root == null) {
            return Collections.emptyList();
        }
        if (!root.isDirectory() && !root.mkdirs()) {
            return Collections.emptyList();
        }

        File[] children = root.listFiles(file -> {
            if (file == null || file.isHidden()) {
                return false;
            }
            return file.isDirectory()
                || (file.isFile() && file.getName().toLowerCase(Locale.US).endsWith(".big"));
        });
        if (children == null || children.length == 0) {
            return Collections.emptyList();
        }

        Arrays.sort(children, Comparator.comparing(File::getName, String.CASE_INSENSITIVE_ORDER));
        return new ArrayList<>(Arrays.asList(children));
    }

    static File getActiveMod(Context ctx) {
        String childName = ctx.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE)
            .getString(PREF_ACTIVE_MOD, null);
        if (childName == null || childName.isEmpty()) {
            return null;
        }

        File root = modsRoot(ctx);
        if (root == null) {
            clearActiveMod(ctx);
            return null;
        }

        File candidate = new File(root, childName);
        if (!isDirectChild(root, candidate)
                || (!candidate.isDirectory()
                    && !(candidate.isFile()
                        && candidate.getName().toLowerCase(Locale.US).endsWith(".big")))) {
            clearActiveMod(ctx);
            return null;
        }
        return candidate;
    }

    static String getActiveModPath(Context ctx) {
        File active = getActiveMod(ctx);
        return active == null ? null : active.getAbsolutePath();
    }

    static boolean setActiveMod(Context ctx, File candidate) {
        if (candidate == null) {
            clearActiveMod(ctx);
            return true;
        }

        File root = modsRoot(ctx);
        if (root == null || !isDirectChild(root, candidate)) {
            return false;
        }
        if (!candidate.isDirectory()
                && !(candidate.isFile()
                    && candidate.getName().toLowerCase(Locale.US).endsWith(".big"))) {
            return false;
        }

        ctx.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE).edit()
            .putString(PREF_ACTIVE_MOD, candidate.getName())
            .apply();
        return true;
    }

    static void clearActiveMod(Context ctx) {
        ctx.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE).edit()
            .remove(PREF_ACTIVE_MOD)
            .apply();
    }

    private static boolean isDirectChild(File root, File candidate) {
        try {
            File canonicalRoot = root.getCanonicalFile();
            File canonicalCandidate = candidate.getCanonicalFile();
            File parent = canonicalCandidate.getParentFile();
            return parent != null && parent.equals(canonicalRoot);
        } catch (IOException e) {
            return false;
        }
    }
}
