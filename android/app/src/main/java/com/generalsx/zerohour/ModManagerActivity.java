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

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.Toast;

import com.google.android.material.button.MaterialButton;

import java.io.File;
import java.util.List;
import java.util.Locale;

/**
 * GeneralsX @feature Android port 04/10/2026 Mod Manager.
 *
 * Phase 1 owns reversible activation. Phase 2 adds a transactional importer:
 * folder trees and .big/.zip documents are copied to a hidden staging area,
 * validated, then atomically renamed into Mods/. No import operation writes
 * into the live game root or an already-installed mod.
 */
public class ModManagerActivity extends Activity {
    private static final int REQUEST_IMPORT_FOLDER = 2101;
    private static final int REQUEST_IMPORT_FILE = 2102;

    private boolean importRunning;
    private AlertDialog importProgress;

    @Override
    protected void attachBaseContext(Context newBase) {
        super.attachBaseContext(LocaleHelper.wrap(newBase));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTitle(R.string.mods_title);
        buildUi();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!importRunning) {
            // Re-read disk state if a file manager changed Mods/ while this
            // Activity was in the background.
            buildUi();
        }
    }

    @Override
    protected void onDestroy() {
        if (importProgress != null) {
            importProgress.dismiss();
            importProgress = null;
        }
        super.onDestroy();
    }

    private void buildUi() {
        LinearLayout shell = new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setBackgroundColor(UiKit.color(this, R.color.gzh_background));
        setContentView(shell);
        InsetUtil.applySafeInsets(shell);

        UiKit.appBar(shell, getString(R.string.setup_title), getString(R.string.mods_title),
            0, null, null);

        FrameLayout host = new FrameLayout(this);
        shell.addView(host, new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        LinearLayout page = UiKit.scrollingPage(host);

        File gameRoot = ModManager.gameRoot(this);
        File modsRoot = ModManager.modsRoot(this);
        if (gameRoot == null || modsRoot == null) {
            LinearLayout card = UiKit.card(page);
            UiKit.sectionHeader(card, R.drawable.ic_gzh_folder,
                getString(R.string.mods_no_game_title), false);
            UiKit.body(card, getString(R.string.mods_no_game_message));
            return;
        }

        if (!modsRoot.isDirectory() && !modsRoot.mkdirs()) {
            LinearLayout card = UiKit.card(page);
            UiKit.sectionHeader(card, R.drawable.ic_gzh_folder,
                getString(R.string.mods_storage_error_title), false);
            UiKit.body(card, getString(R.string.mods_storage_error_message,
                modsRoot.getAbsolutePath()));
            return;
        }

        File active = ModManager.getActiveMod(this);

        LinearLayout status = UiKit.card(page);
        UiKit.sectionHeader(status, R.drawable.ic_gzh_folder,
            getString(R.string.mods_status_title), false);
        UiKit.body(status, active == null
            ? getString(R.string.mods_active_vanilla)
            : getString(R.string.mods_active_mod, active.getName()));
        UiKit.caption(status, getString(R.string.mods_folder_path, modsRoot.getAbsolutePath()));

        String legacy = DataPackInstaller.findDataMod(gameRoot.getAbsolutePath());
        if (legacy != null) {
            UiKit.helpText(status, getString(R.string.mods_legacy_warning, legacy));
        }

        // GeneralsX @feature Android port 04/10/2026 Phase 2 import entry points.
        // The system picker grants read access to the source; ModImportService
        // copies it immediately into our own managed Mods tree.
        LinearLayout importer = UiKit.card(page);
        UiKit.sectionHeader(importer, R.drawable.ic_gzh_folder,
            getString(R.string.mods_import_title), false);
        UiKit.supporting(importer, getString(R.string.mods_import_desc));
        UiKit.button(importer, UiKit.BTN_PRIMARY, R.drawable.ic_gzh_folder,
            getString(R.string.mods_import_folder), this::pickModFolder);
        UiKit.button(importer, UiKit.BTN_TONAL, R.drawable.ic_gzh_folder,
            getString(R.string.mods_import_file), this::pickModFile);
        UiKit.helpText(importer, getString(R.string.mods_import_safety));

        LinearLayout vanilla = UiKit.card(page);
        UiKit.sectionHeader(vanilla, R.drawable.ic_gzh_play,
            getString(R.string.mods_vanilla_title), false);
        UiKit.supporting(vanilla, getString(R.string.mods_vanilla_desc));
        MaterialButton vanillaButton = UiKit.button(vanilla,
            active == null ? UiKit.BTN_TONAL : UiKit.BTN_PRIMARY,
            R.drawable.ic_gzh_play,
            active == null ? getString(R.string.mods_active_button)
                           : getString(R.string.mods_use_vanilla),
            () -> {
                ModManager.clearActiveMod(this);
                Toast.makeText(this, R.string.mods_toast_vanilla, Toast.LENGTH_SHORT).show();
                buildUi();
            });
        vanillaButton.setEnabled(active != null);

        List<File> mods = ModManager.listMods(this);
        if (mods.isEmpty()) {
            LinearLayout empty = UiKit.card(page);
            UiKit.sectionHeader(empty, R.drawable.ic_gzh_folder,
                getString(R.string.mods_empty_title), false);
            UiKit.body(empty, getString(R.string.mods_empty_message, modsRoot.getAbsolutePath()));
            return;
        }

        for (File mod : mods) {
            boolean selected = active != null && active.equals(mod);
            LinearLayout card = UiKit.card(page);
            UiKit.sectionHeader(card, R.drawable.ic_gzh_folder, mod.getName(), false);
            UiKit.supporting(card, mod.isDirectory()
                ? getString(R.string.mods_type_folder)
                : getString(R.string.mods_type_big));

            MaterialButton button = UiKit.button(card,
                selected ? UiKit.BTN_TONAL : UiKit.BTN_PRIMARY,
                R.drawable.ic_gzh_play,
                selected ? getString(R.string.mods_active_button)
                         : getString(R.string.mods_activate_button),
                () -> {
                    if (ModManager.setActiveMod(this, mod)) {
                        Toast.makeText(this,
                            getString(R.string.mods_toast_activated, mod.getName()),
                            Toast.LENGTH_SHORT).show();
                        buildUi();
                    } else {
                        Toast.makeText(this, R.string.mods_toast_activate_failed,
                            Toast.LENGTH_LONG).show();
                    }
                });
            button.setEnabled(!selected);
        }
    }

    private void pickModFolder() {
        if (importRunning) {
            return;
        }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION
            | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try {
            startActivityForResult(intent, REQUEST_IMPORT_FOLDER);
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, R.string.mods_import_picker_missing, Toast.LENGTH_LONG).show();
        }
    }

    private void pickModFile() {
        if (importRunning) {
            return;
        }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION
            | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try {
            startActivityForResult(intent, REQUEST_IMPORT_FILE);
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, R.string.mods_import_picker_missing, Toast.LENGTH_LONG).show();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if ((requestCode != REQUEST_IMPORT_FOLDER && requestCode != REQUEST_IMPORT_FILE)
                || resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }

        Uri uri = data.getData();
        try {
            int takeFlags = data.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION;
            if (takeFlags != 0) {
                getContentResolver().takePersistableUriPermission(uri, takeFlags);
            }
        } catch (SecurityException ignored) {
            // The grant is only needed while we copy. Some providers do not
            // offer persistable grants even when the picker intent requested one.
        }

        beginImport(uri, requestCode == REQUEST_IMPORT_FOLDER);
    }

    private void beginImport(Uri uri, boolean folder) {
        if (importRunning) {
            return;
        }
        importRunning = true;
        importProgress = new AlertDialog.Builder(this)
            .setTitle(R.string.mods_import_working_title)
            .setMessage(R.string.mods_import_working_message)
            .setCancelable(false)
            .create();
        importProgress.show();

        new Thread(() -> {
            try {
                ModImportService.Result result = folder
                    ? ModImportService.importTree(this, uri)
                    : ModImportService.importDocument(this, uri);
                runOnUiThread(() -> finishImportSuccess(result));
            } catch (Exception e) {
                String message = e.getMessage();
                if (message == null || message.trim().isEmpty()) {
                    message = e.getClass().getSimpleName();
                }
                final String detail = message;
                runOnUiThread(() -> finishImportFailure(detail));
            }
        }, "GeneralsX-ModImport").start();
    }

    private void dismissImportProgress() {
        importRunning = false;
        if (importProgress != null) {
            importProgress.dismiss();
            importProgress = null;
        }
    }

    private void finishImportSuccess(ModImportService.Result result) {
        if (isFinishing() || isDestroyed()) {
            return;
        }
        dismissImportProgress();
        buildUi();

        String size = humanBytes(result.bytes);
        new AlertDialog.Builder(this)
            .setTitle(R.string.mods_import_done_title)
            .setMessage(getString(R.string.mods_import_done_message,
                result.installed.getName(), result.bigCount, result.fileCount, size))
            .setPositiveButton(R.string.mods_import_activate, (dialog, which) -> {
                if (ModManager.setActiveMod(this, result.installed)) {
                    Toast.makeText(this,
                        getString(R.string.mods_toast_activated, result.installed.getName()),
                        Toast.LENGTH_SHORT).show();
                }
                buildUi();
            })
            .setNegativeButton(R.string.mods_import_later, null)
            .show();
    }

    private void finishImportFailure(String detail) {
        if (isFinishing() || isDestroyed()) {
            return;
        }
        dismissImportProgress();
        new AlertDialog.Builder(this)
            .setTitle(R.string.mods_import_failed_title)
            .setMessage(getString(R.string.mods_import_failed_message, detail))
            .setPositiveButton(android.R.string.ok, null)
            .show();
    }

    private static String humanBytes(long bytes) {
        if (bytes < 1024) {
            return bytes + " B";
        }
        double value = bytes;
        String[] units = { "KB", "MB", "GB", "TB" };
        int unit = -1;
        do {
            value /= 1024.0;
            unit++;
        } while (value >= 1024.0 && unit < units.length - 1);
        return String.format(Locale.US, "%.1f %s", value, units[unit]);
    }
}
