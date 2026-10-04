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
import android.content.Context;
import android.os.Bundle;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import com.google.android.material.button.MaterialButton;

import java.io.File;
import java.util.List;

/**
 * GeneralsX @feature Android port 04/10/2026 Mod Manager Phase 1.
 *
 * This first slice deliberately does only the reversible core: discover mods,
 * select one, disable it, and let the existing engine -mod path load it on the
 * next launch. Import/delete/load-order are separate follow-up slices so a file
 * operation can never be the reason basic activation stops working.
 */
public class ModManagerActivity extends Activity {

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
        // Re-read disk state if the player used a file manager while this
        // Activity was in the background.
        buildUi();
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
}
