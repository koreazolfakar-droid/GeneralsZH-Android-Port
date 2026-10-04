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
import android.widget.TextView;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.view.View;
import android.view.ViewGroup;
import android.view.Gravity;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.content.res.ColorStateList;
import android.text.TextUtils;

import com.google.android.material.button.MaterialButton;

import java.io.File;
import java.util.List;
import java.util.Locale;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * GeneralsX @feature Android port 04/10/2026 Mod Manager.
 *
 * Phase 1 owns reversible activation. Phase 2 adds a transactional importer:
 * folder trees and .big/.zip documents are copied to a hidden staging area,
 * validated, then atomically renamed into Mods/. No import operation writes
 * into the live game root or an already-installed mod. Import can be cancelled
 * before commit, and installed entries can be deleted only through ModManager's
 * canonical managed-root check.
 */
public class ModManagerActivity extends Activity {
    private static final int REQUEST_IMPORT_FOLDER = 2101;
    private static final int REQUEST_IMPORT_FILE = 2102;

    private boolean importRunning;
    private AlertDialog importProgress;
    private ModImportService.CancellationSignal importCancellation;
    private Thread importThread;

    // GeneralsX @feature Android port 04/10/2026 Tactical Views-only library.
    // Filesystem discovery and size accounting never run on the UI thread.
    private static final int BACKGROUND = LauncherUi.BACKGROUND;
    private static final int SURFACE = LauncherUi.SURFACE;
    private static final int OUTLINE = LauncherUi.OUTLINE;
    private static final int GOLD = 0xffefc752;
    private static final int TEXT = LauncherUi.TEXT;
    private static final int MUTED = LauncherUi.MUTED;
    private final ExecutorService libraryWorker = Executors.newSingleThreadExecutor(
        task -> new Thread(task, "GeneralsX-ModLibrary"));
    private LinearLayout library;
    private TextView countValue, storageValue, freeValue, selection;
    private MaterialButton importButton, vanillaButton;
    private ProgressBar libraryProgress;
    private Snapshot snapshot;
    private int scanGeneration;
    private boolean actionRunning;
    private String libraryQuery = "";

    private static final class Entry {
        final File file;
        final long bytes;
        final boolean directory;
        Entry(File file, long bytes) {
            this.file = file;
            this.bytes = bytes;
            directory = file.isDirectory();
        }
    }

    private static final class Snapshot {
        File root, active;
        String legacy;
        boolean storageReady;
        long total, free;
        final List<Entry> entries = new ArrayList<>();
    }

    @Override
    protected void attachBaseContext(Context newBase) {
        super.attachBaseContext(LocaleHelper.wrap(newBase));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTitle(R.string.mods_title);
        if (savedInstanceState != null) libraryQuery = savedInstanceState.getString("mods_ui_query", "");
        buildUi();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putString("mods_ui_query", libraryQuery);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!importRunning) {
            // Re-read disk state if a file manager changed Mods/ while this
            // Activity was in the background.
            refreshLibrary();
        }
    }

    @Override
    protected void onDestroy() {
        if (importCancellation != null) importCancellation.cancel();
        if (importThread != null) importThread.interrupt();
        if (importProgress != null) {
            importProgress.dismiss();
            importProgress = null;
        }
        scanGeneration++;
        libraryWorker.shutdownNow();
        super.onDestroy();
    }

    private void buildUi() {
        getWindow().setStatusBarColor(BACKGROUND);
        getWindow().setNavigationBarColor(BACKGROUND);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE);
        LinearLayout shell = column();
        shell.setBackgroundColor(BACKGROUND);
        setContentView(shell);
        InsetUtil.applySafeInsets(shell);

        FrameLayout host = new FrameLayout(this);
        shell.addView(host, new LinearLayout.LayoutParams(-1, 0, 1f));
        LinearLayout page = UiKit.scrollingPage(host);
        page.setPadding(dp(16), dp(12), dp(16), dp(12));
        FrameLayout battlefield = LauncherUi.artwork(this, page, 140);
        ((ImageView) battlefield.getChildAt(0)).setImageResource(R.drawable.launcher_mods_battlefield);
        LinearLayout header = column();
        header.setPadding(dp(14), dp(12), dp(14), dp(14));
        header.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
            new int[] {0x99090d14, 0x00090d14, 0xdd090d14}));
        battlefield.addView(header, new FrameLayout.LayoutParams(-1, -1));
        LinearLayout tools = new LinearLayout(this);
        tools.setGravity(Gravity.CENTER_VERTICAL);
        header.addView(tools, new LinearLayout.LayoutParams(-1, -2));
        TextView title = new TextView(this);
        title.setText(R.string.mods_title);
        title.setTextSize(32);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(TEXT);
        tools.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
        tools.addView(UiKit.iconButton(this, android.R.drawable.ic_menu_search,
            getString(R.string.launcher_search_mods), this::searchLibrary));
        View settings = UiKit.iconButton(this, R.drawable.ic_gzh_sliders,
            getString(R.string.launcher_settings), () -> LauncherUi.open(this, SetupActivity.TAB_INTERFACE));
        settings.setOnClickListener(v -> LauncherUi.settings(this, v, tab -> LauncherUi.open(this, tab)));
        tools.addView(settings);
        text(header, getString(R.string.mods_library_subtitle), 13, TEXT, false);

        LinearLayout summary = panel(page, false);
        summary.setOrientation(LinearLayout.HORIZONTAL);
        summary.setPadding(dp(12), dp(16), dp(12), dp(16));
        countValue = metric(summary, R.string.mods_library_title);
        storageValue = metric(summary, R.string.mods_storage_used);
        freeValue = metric(summary, R.string.mods_free_space);
        selection = text(page, getString(R.string.mods_library_loading), 13, MUTED, false);
        selection.setPadding(dp(2), dp(8), 0, dp(6));
        libraryProgress = new ProgressBar(this);
        libraryProgress.setIndeterminate(true);
        libraryProgress.setIndeterminateTintList(ColorStateList.valueOf(GOLD));
        page.addView(libraryProgress, new LinearLayout.LayoutParams(dp(28), dp(28)));
        library = column();
        page.addView(library, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout footer = column();
        footer.setPadding(dp(16), dp(10), dp(16), dp(12));
        footer.setBackgroundColor(BACKGROUND);
        shell.addView(footer, new LinearLayout.LayoutParams(-1, -2));
        LinearLayout actions = UiKit.buttonRow(footer);
        importButton = action(actions, R.string.mods_import_title, R.drawable.ic_gzh_download,
            true, this::showImportChoices);
        vanillaButton = action(actions, R.string.mods_use_vanilla, R.drawable.ic_gzh_play,
            false, () -> selectMod(null, true));
        importButton.setEnabled(false);
        vanillaButton.setEnabled(false);
        LauncherUi.purple(this, importButton);
        shell.addView(LauncherUi.navigation(this, SetupActivity.TAB_MODS, tab -> {
            if (tab != SetupActivity.TAB_MODS) {
                LauncherUi.open(this, tab);
                finish();
            }
        }), new LinearLayout.LayoutParams(-1, dp(68)));
    }

    private void searchLibrary() {
        android.widget.EditText query = new android.widget.EditText(this);
        query.setSingleLine(true);
        query.setInputType(android.text.InputType.TYPE_CLASS_TEXT);
        query.setHint(R.string.launcher_search_mods);
        query.setText(libraryQuery);
        query.setSelectAllOnFocus(true);
        query.setPadding(dp(20), dp(10), dp(20), dp(10));
        new AlertDialog.Builder(this).setTitle(R.string.launcher_search_mods).setView(query)
            .setPositiveButton(android.R.string.ok, (dialog, which) -> {
                libraryQuery = query.getText().toString().trim();
                renderLibrary();
            }).setNegativeButton(android.R.string.cancel, null).show();
    }

    private void refreshLibrary() {
        if (isFinishing() || isDestroyed() || libraryWorker.isShutdown()) return;
        final int generation = ++scanGeneration;
        libraryProgress.setVisibility(View.VISIBLE);
        libraryWorker.execute(() -> {
            Snapshot next = new Snapshot();
            File game = ModManager.gameRoot(this);
            next.root = ModManager.modsRoot(this);
            try {
                if (game != null && next.root != null) {
                    next.storageReady = next.root.isDirectory() || next.root.mkdirs();
                    if (next.storageReady) {
                        next.active = ModManager.getActiveMod(this);
                        next.legacy = DataPackInstaller.findDataMod(game.getAbsolutePath());
                        next.free = next.root.getUsableSpace();
                        for (File mod : ModManager.listMods(this)) {
                            if (Thread.currentThread().isInterrupted()) return;
                            if (!ModLibraryInfo.isManagedEntry(next.root, mod)) continue;
                            long bytes = ModLibraryInfo.measure(mod);
                            next.entries.add(new Entry(mod, bytes));
                            next.total = next.total < 0 || bytes < 0 ? -1 : next.total + bytes;
                        }
                    }
                }
            } catch (SecurityException e) {
                next.storageReady = false;
            }
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed() || generation != scanGeneration) return;
                snapshot = next;
                libraryProgress.setVisibility(View.GONE);
                renderLibrary();
            });
        });
    }

    private void renderLibrary() {
        if (snapshot == null) return;
        library.removeAllViews();
        countValue.setText(snapshot.storageReady
            ? String.format(Locale.getDefault(), "%d", snapshot.entries.size())
            : getString(R.string.mods_size_unknown));
        storageValue.setText(snapshot.storageReady ? sizeLabel(snapshot.total) : getString(R.string.mods_size_unknown));
        freeValue.setText(snapshot.storageReady ? sizeLabel(snapshot.free) : getString(R.string.mods_size_unknown));
        selection.setText(snapshot.active == null ? getString(R.string.mods_active_vanilla)
            : getString(R.string.mods_active_mod, snapshot.active.getName()));
        selection.setMaxLines(2);
        selection.setEllipsize(TextUtils.TruncateAt.END);
        boolean enabled = snapshot.storageReady && !importRunning && !actionRunning;
        importButton.setEnabled(enabled);
        vanillaButton.setEnabled(enabled);
        if (!snapshot.storageReady) {
            LinearLayout error = panel(library, false);
            text(error, getString(snapshot.root == null ? R.string.mods_no_game_title
                : R.string.mods_storage_error_title), 18, TEXT, true);
            text(error, snapshot.root == null ? getString(R.string.mods_no_game_message)
                : getString(R.string.mods_storage_error_message, snapshot.root.getAbsolutePath()), 14, MUTED, false);
            return;
        }
        if (snapshot.legacy != null) {
            text(library, getString(R.string.mods_legacy_warning, snapshot.legacy), 13, GOLD, false);
        }
        if (snapshot.entries.isEmpty()) {
            LinearLayout empty = panel(library, false);
            text(empty, getString(R.string.mods_empty_title), 20, TEXT, true);
            text(empty, getString(R.string.mods_library_empty), 14, MUTED, false);
        }
        int shown = 0;
        List<Entry> ordered = new ArrayList<>(snapshot.entries);
        ordered.sort((a, b) -> Boolean.compare(b.file.equals(snapshot.active), a.file.equals(snapshot.active)));
        for (Entry entry : ordered) {
            if (!entry.file.getName().toLowerCase(Locale.ROOT).contains(libraryQuery.toLowerCase(Locale.ROOT))) continue;
            shown++;
            boolean active = entry.file.equals(snapshot.active);
            LinearLayout card = panel(library, active);
            LinearLayout heading = new LinearLayout(this);
            heading.setGravity(Gravity.CENTER_VERTICAL);
            card.addView(heading, new LinearLayout.LayoutParams(-1, -2));
            FrameLayout preview = new FrameLayout(this);
            preview.setBackground(shape(0xff242035, OUTLINE));
            preview.setClipToOutline(true);
            ImageView artwork = new ImageView(this);
            artwork.setImageResource(R.drawable.launcher_mods_battlefield);
            artwork.setScaleType(ImageView.ScaleType.CENTER_CROP);
            artwork.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
            preview.addView(artwork, new FrameLayout.LayoutParams(-1, -1));
            // Shared decorative artwork, never claimed as mod-specific cover metadata.
            ImageView icon = new ImageView(this);
            icon.setImageResource(R.drawable.ic_gzh_folder);
            icon.setImageTintList(ColorStateList.valueOf(active ? GOLD : LauncherUi.PURPLE));
            icon.setBackground(shape(0xdd121621, OUTLINE));
            icon.setPadding(dp(5), dp(5), dp(5), dp(5));
            FrameLayout.LayoutParams glyph = new FrameLayout.LayoutParams(dp(28), dp(28), Gravity.BOTTOM | Gravity.END);
            glyph.setMargins(dp(4), dp(4), dp(4), dp(4));
            preview.addView(icon, glyph);
            LinearLayout.LayoutParams imageParams = new LinearLayout.LayoutParams(dp(68), dp(104));
            imageParams.setMarginEnd(dp(12));
            heading.addView(preview, imageParams);
            LinearLayout info = column();
            heading.addView(info, new LinearLayout.LayoutParams(0, -2, 1f));
            LinearLayout titleRow = new LinearLayout(this);
            titleRow.setGravity(Gravity.CENTER_VERTICAL);
            info.addView(titleRow, new LinearLayout.LayoutParams(-1, -2));
            TextView name = new TextView(this);
            name.setText(entry.file.getName());
            name.setTextSize(16);
            name.setTextColor(TEXT);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            name.setMaxLines(2);
            name.setEllipsize(TextUtils.TruncateAt.END);
            titleRow.addView(name, new LinearLayout.LayoutParams(0, -2, 1));
            TextView badge = new TextView(this);
            badge.setText(active ? R.string.mods_active_button : R.string.mods_installed_badge);
            badge.setTextSize(10);
            badge.setTypeface(Typeface.DEFAULT_BOLD);
            badge.setTextColor(active ? GOLD : LauncherUi.GREEN);
            badge.setPadding(dp(6), dp(4), dp(6), dp(4));
            badge.setBackground(shape(active ? 0xff292417 : 0xff0d2520,
                active ? GOLD : 0xff28674f));
            LinearLayout.LayoutParams badgeLp = new LinearLayout.LayoutParams(-2, -2);
            badgeLp.setMarginStart(dp(6));
            titleRow.addView(badge, badgeLp);
            View delete = UiKit.iconButton(this, android.R.drawable.ic_menu_delete,
                getString(R.string.mods_delete_button), () -> confirmDelete(entry.file, active));
            delete.setLayoutParams(new LinearLayout.LayoutParams(dp(48), dp(48)));
            ((ImageView) delete).setImageTintList(new ColorStateList(
                new int[][] { {-android.R.attr.state_enabled}, {} },
                new int[] { MUTED, 0xffff6b78 }));
            delete.setEnabled(enabled);
            titleRow.addView(delete);
            TextView type = text(info, sizeLabel(entry.bytes) + "  ·  " + getString(entry.directory
                ? R.string.mods_type_folder : R.string.mods_type_big), 11, MUTED, false);
            type.setPadding(0, dp(4), 0, 0);
            LinearLayout actions = UiKit.buttonRow(info);
            MaterialButton launch = action(actions, R.string.mods_launch_button, R.drawable.ic_gzh_play,
                active, () -> selectMod(entry.file, true));
            MaterialButton activate = action(actions, R.string.mods_activate_button, R.drawable.ic_gzh_refresh,
                false, () -> selectMod(entry.file, false));
            launch.setEnabled(enabled);
            activate.setEnabled(enabled && !active);
        }
        if (shown == 0 && !snapshot.entries.isEmpty()) {
            text(library, getString(R.string.launcher_no_matches), 14, MUTED, false);
        }
        TextView path = text(library, getString(R.string.mods_folder_path,
            snapshot.root.getAbsolutePath()), 11, MUTED, false);
        path.setPadding(dp(2), dp(14), dp(2), dp(4));
    }

    private void selectMod(File mod, boolean launch) {
        if (importRunning || actionRunning || snapshot == null || !snapshot.storageReady) return;
        actionRunning = true;
        renderLibrary();
        libraryWorker.execute(() -> {
            boolean success = ModManager.setActiveMod(this, mod);
            File active = ModManager.getActiveMod(this);
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed()) return;
                actionRunning = false;
                snapshot.active = active;
                renderLibrary();
                if (!success) {
                    Toast.makeText(this, R.string.mods_toast_activate_failed, Toast.LENGTH_LONG).show();
                } else if (launch) {
                    // Reuse Setup's existing orientation/launcher path; never construct -mod arguments here.
                    startActivity(new Intent(this, SetupActivity.class)
                        .putExtra(SetupActivity.EXTRA_LAUNCH_FROM_MODS, true));
                } else {
                    Toast.makeText(this, mod == null ? getString(R.string.mods_toast_vanilla)
                        : getString(R.string.mods_toast_activated, mod.getName()), Toast.LENGTH_SHORT).show();
                }
            });
        });
    }

    // GeneralsX @feature Android port 04/10/2026 Confirmed, managed-root-only deletion.
    private void confirmDelete(File mod, boolean active) {
        if (importRunning || actionRunning || snapshot == null || !snapshot.storageReady) return;
        new AlertDialog.Builder(this)
            .setTitle(R.string.mods_delete_confirm_title)
            .setMessage(getString(active ? R.string.mods_delete_active_confirm
                : R.string.mods_delete_confirm, mod.getName()))
            .setPositiveButton(R.string.mods_delete_button, (dialog, which) -> deleteMod(mod))
            .setNegativeButton(android.R.string.cancel, null)
            .show();
    }

    private void deleteMod(File mod) {
        actionRunning = true;
        renderLibrary();
        libraryWorker.execute(() -> {
            boolean deleted = ModManager.deleteManagedMod(this, mod);
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed()) return;
                actionRunning = false;
                Toast.makeText(this, getString(deleted ? R.string.mods_delete_success
                    : R.string.mods_delete_failed, mod.getName()), Toast.LENGTH_LONG).show();
                refreshLibrary();
            });
        });
    }

    private void showImportChoices() {
        if (importRunning || actionRunning) return;
        new AlertDialog.Builder(this).setTitle(R.string.mods_import_title)
            .setItems(new CharSequence[] { getString(R.string.mods_import_folder),
                getString(R.string.mods_import_file) }, (dialog, which) -> {
                    if (which == 0) pickModFolder(); else pickModFile();
                }).setNegativeButton(android.R.string.cancel, null).show();
    }

    private LinearLayout column() {
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        return column;
    }

    private int dp(int value) { return UiKit.dp(this, value); }

    private GradientDrawable shape(int fill, int stroke) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(fill);
        shape.setCornerRadius(dp(10));
        shape.setStroke(dp(1), stroke);
        return shape;
    }

    private LinearLayout panel(LinearLayout parent, boolean active) {
        LinearLayout panel = column();
        panel.setPadding(dp(14), dp(14), dp(14), dp(14));
        panel.setBackground(shape(active ? 0xff1b211d : SURFACE, active ? GOLD : OUTLINE));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.topMargin = dp(12);
        parent.addView(panel, lp);
        return panel;
    }

    private TextView text(LinearLayout parent, CharSequence value, int sp, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        if (bold) view.setTypeface(Typeface.DEFAULT_BOLD);
        view.setLineSpacing(0, 1.15f);
        parent.addView(view, new LinearLayout.LayoutParams(-1, -2));
        return view;
    }

    private TextView metric(LinearLayout parent, int label) {
        LinearLayout cell = column();
        cell.setPadding(dp(3), 0, dp(3), 0);
        parent.addView(cell, new LinearLayout.LayoutParams(0, -2, 1f));
        TextView value = text(cell, getString(R.string.mods_size_unknown), 18, TEXT, true);
        TextView caption = text(cell, getString(label), 10, MUTED, false);
        caption.setMaxLines(2);
        return value;
    }

    private MaterialButton action(LinearLayout row, int label, int icon, boolean primary, Runnable run) {
        boolean first = row.getChildCount() == 0;
        MaterialButton button = UiKit.button(row, UiKit.BTN_TONAL, icon, getString(label), run);
        UiKit.share(button, first);
        button.setCornerRadius(dp(8));
        button.setTextSize(13);
        button.setStrokeWidth(dp(1));
        button.setStrokeColor(ColorStateList.valueOf(primary ? GOLD : OUTLINE));
        int foreground = primary ? BACKGROUND : TEXT;
        button.setTextColor(new ColorStateList(new int[][] { {-android.R.attr.state_enabled}, {} },
            new int[] { MUTED, foreground }));
        button.setIconTint(button.getTextColors());
        button.setBackgroundTintList(new ColorStateList(new int[][] { {-android.R.attr.state_enabled}, {} },
            new int[] { SURFACE, primary ? GOLD : 0xff1b2a3a }));
        return button;
    }

    private String sizeLabel(long bytes) {
        return bytes < 0 ? getString(R.string.mods_size_unknown) : humanBytes(bytes);
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
                // The nonzero masked value above is exactly this same read-only flag.
                getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
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
        renderLibrary();
        LinearLayout progressSurface = column();
        progressSurface.setPadding(dp(24), dp(12), dp(24), dp(20));
        ProgressBar spinner = new ProgressBar(this);
        spinner.setIndeterminate(true);
        spinner.setIndeterminateTintList(ColorStateList.valueOf(GOLD));
        LinearLayout.LayoutParams spinnerParams = new LinearLayout.LayoutParams(dp(48), dp(48));
        spinnerParams.gravity = Gravity.CENTER_HORIZONTAL;
        progressSurface.addView(spinner, spinnerParams);
        TextView progressMessage = text(progressSurface, getString(R.string.mods_import_working_message), 14, TEXT, false);
        progressMessage.setPadding(0, dp(18), 0, 0);
        importProgress = new AlertDialog.Builder(this)
            .setTitle(R.string.mods_import_working_title)
            .setView(progressSurface)
            .setNegativeButton(R.string.mods_import_cancel_action, null)
            .setCancelable(false)
            .create();
        importProgress.show();

        importCancellation = new ModImportService.CancellationSignal();
        importProgress.getButton(AlertDialog.BUTTON_NEGATIVE).setOnClickListener(v -> {
            if (importCancellation == null || importCancellation.isCancelled()) return;
            importCancellation.cancel();
            if (importThread != null) importThread.interrupt();
            progressMessage.setText(R.string.mods_import_cancelling);
            v.setEnabled(false);
        });

        importThread = new Thread(() -> {
            try {
                ModImportService.Result result = folder
                    ? ModImportService.importTree(this, uri, importCancellation)
                    : ModImportService.importDocument(this, uri, importCancellation);
                runOnUiThread(() -> finishImportSuccess(result));
            } catch (ModImportService.ImportCancelledException e) {
                runOnUiThread(this::finishImportCancelled);
            } catch (Exception e) {
                String message = e.getMessage();
                if (message == null || message.trim().isEmpty()) {
                    message = e.getClass().getSimpleName();
                }
                final String detail = message;
                runOnUiThread(() -> finishImportFailure(detail));
            }
        }, "GeneralsX-ModImport");
        importThread.start();
    }

    private void dismissImportProgress() {
        importRunning = false;
        importCancellation = null;
        importThread = null;
        if (importProgress != null) {
            importProgress.dismiss();
            importProgress = null;
        }
    }

    private void finishImportCancelled() {
        if (isFinishing() || isDestroyed()) return;
        dismissImportProgress();
        renderLibrary();
        Toast.makeText(this, R.string.mods_import_cancelled, Toast.LENGTH_LONG).show();
        refreshLibrary();
    }

    private void finishImportSuccess(ModImportService.Result result) {
        if (isFinishing() || isDestroyed()) {
            return;
        }
        dismissImportProgress();
        refreshLibrary();

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
                refreshLibrary();
            })
            .setNegativeButton(R.string.mods_import_later, null)
            .show();
    }

    private void finishImportFailure(String detail) {
        if (isFinishing() || isDestroyed()) {
            return;
        }
        dismissImportProgress();
        renderLibrary();
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
