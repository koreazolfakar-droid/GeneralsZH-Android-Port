package com.generalsx.zerohour;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import android.widget.ProgressBar;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import com.google.android.material.button.MaterialButton;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import org.junit.Before;
import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.LooperMode;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.shadows.ShadowAlertDialog;
import org.robolectric.shadows.ShadowLooper;
import static org.robolectric.Shadows.shadowOf;
import static org.junit.Assert.*;

// GeneralsX @feature Android port 04/10/2026 Android Views/state/launcher regression tests.
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28, qualifiers = "w360dp-h760dp-mdpi")
@LooperMode(LooperMode.Mode.PAUSED)
public class ModManagerUiTest {
    @Rule public TemporaryFolder temp = new TemporaryFolder();
    private Context context;
    private File game, mods;
    private ActivityController<ModManagerActivity> controller;
    private ModManagerActivity activity;

    @Before public void setUp() throws Exception {
        context = RuntimeEnvironment.getApplication();
        game = temp.newFolder("game");
        mods = new File(game, "Mods");
        assertTrue(mods.mkdir());
        context.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE).edit()
            .clear().putString(SetupActivity.PREF_GAME_PATH, game.getAbsolutePath()).commit();
    }

    @After public void tearDown() {
        if (controller != null) controller.pause().stop().destroy();
    }

    private void open() throws Exception {
        controller = Robolectric.buildActivity(ModManagerActivity.class).setup();
        activity = controller.get();
        drain();
    }

    private void drain() throws Exception {
        Field worker = ModManagerActivity.class.getDeclaredField("libraryWorker");
        worker.setAccessible(true);
        ((ExecutorService) worker.get(activity)).submit(() -> {}).get(10, TimeUnit.SECONDS);
        ShadowLooper.idleMainLooper();
    }

    private List<View> views(View root) {
        List<View> list = new ArrayList<>();
        list.add(root);
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i = 0; i < group.getChildCount(); i++) list.addAll(views(group.getChildAt(i)));
        }
        return list;
    }

    private TextView label(String text) {
        for (View v : views(activity.getWindow().getDecorView())) {
            if (v instanceof TextView && ((TextView) v).getText().toString().equals(text)) return (TextView) v;
        }
        throw new AssertionError("Missing label: " + text);
    }

    private MaterialButton button(View root, int string) {
        String text = activity.getString(string);
        for (View v : views(root)) {
            if (v instanceof MaterialButton && ((MaterialButton) v).getText().toString().equals(text)) return (MaterialButton) v;
        }
        throw new AssertionError("Missing button: " + text);
    }

    private View action(View root, int string) {
        String description = activity.getString(string);
        for (View v : views(root)) {
            if (v.getContentDescription() != null
                    && description.contentEquals(v.getContentDescription())) return v;
        }
        throw new AssertionError("Missing action: " + description);
    }

    private View card(File mod) {
        return (View) label(mod.getName()).getParent().getParent().getParent().getParent();
    }

    @Test public void emptyLibraryAndMissingGameFolderAreSafe() throws Exception {
        open();
        label(activity.getString(R.string.mods_empty_title));
        label("0");
        for (View view : views(activity.getWindow().getDecorView())) {
            if (view instanceof TextView) {
                String text = ((TextView)view).getText().toString();
                assertFalse(text.contains("Project X Re"));
                assertFalse(text.contains("Russian Army"));
                assertFalse(text.contains("ShockWave"));
            }
        }
        context.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE).edit()
            .remove(SetupActivity.PREF_GAME_PATH).commit();
        controller.pause().resume();
        drain();
        label(activity.getString(R.string.mods_no_game_title));
        assertFalse(button(activity.getWindow().getDecorView(), R.string.mods_import_title).isEnabled());
    }

    @Test public void activeChoiceSurvivesRestartAndSwitchingWithoutImport() throws Exception {
        File first = new File(mods, "ExistingFixture");
        assertTrue(first.mkdir());
        Files.write(new File(first, "data.big").toPath(), new byte[32]);
        File second = new File(mods, "OtherInstalled.big");
        Files.write(second.toPath(), new byte[16]);
        assertTrue(ModManager.setActiveMod(context, first));
        open();
        assertFalse(button(card(first), R.string.mods_activate_button).isEnabled());
        button(card(second), R.string.mods_activate_button).performClick();
        drain();
        assertEquals(second, ModManager.getActiveMod(context));
        controller.pause().stop().destroy();
        controller = null;
        open();
        assertFalse(button(card(second), R.string.mods_activate_button).isEnabled());
        assertTrue(first.exists());
        assertEquals(2, ModManager.listMods(context).size());
        button(card(first), R.string.mods_launch_button).performClick();
        drain();
        assertEquals(first, ModManager.getActiveMod(context));
        Intent launch = shadowOf(activity).getNextStartedActivity();
        assertEquals(SetupActivity.class.getName(), launch.getComponent().getClassName());
        assertTrue(launch.getBooleanExtra(SetupActivity.EXTRA_LAUNCH_FROM_MODS, false));
        button(activity.getWindow().getDecorView(), R.string.mods_use_vanilla).performClick();
        drain();
        assertNull(ModManager.getActiveMod(context));
        assertNotNull(shadowOf(activity).getNextStartedActivity());
        button(card(second), R.string.mods_launch_button).performClick();
        drain();
        assertEquals(second, ModManager.getActiveMod(context));
        assertEquals(2, ModManager.listMods(context).size());
    }

    // GeneralsX @feature Android port 04/10/2026 Destructive actions stay inside Mods.
    @Test public void confirmedDeleteRemovesOnlyManagedModAndReturnsActiveChoiceToVanilla()
            throws Exception {
        File vanilla = new File(game, "INI.big");
        Files.write(vanilla.toPath(), new byte[] {9,8,7});
        File active = new File(mods, "Delete me");
        assertTrue(active.mkdir());
        Files.write(new File(active, "data.big").toPath(), new byte[] {1,2,3});
        assertTrue(ModManager.setActiveMod(context, active));
        open();

        action(card(active), R.string.mods_delete_button).performClick();
        AlertDialog confirm = ShadowAlertDialog.getLatestAlertDialog();
        assertTrue(((TextView) confirm.findViewById(android.R.id.message)).getText().toString()
            .contains(active.getName()));
        confirm.getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
        assertTrue(active.exists());
        assertEquals(active, ModManager.getActiveMod(context));

        assertTrue(action(card(active), R.string.mods_delete_button).performClick());
        ShadowAlertDialog.getLatestAlertDialog().getButton(AlertDialog.BUTTON_POSITIVE).performClick();
        long deleteDeadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        while (active.exists() && System.nanoTime() < deleteDeadline) {
            drain();
            Thread.sleep(10);
        }
        assertFalse(active.exists());
        assertNull(ModManager.getActiveMod(context));
        assertArrayEquals(new byte[] {9,8,7}, Files.readAllBytes(vanilla.toPath()));
        assertFalse(ModManager.deleteManagedMod(context, vanilla));
        assertFalse(ModManager.deleteManagedMod(context, new File(mods, ".installing")));

        File outside = temp.newFolder("outside-mod");
        File link = new File(mods, "Outside link");
        try {
            Files.createSymbolicLink(link.toPath(), outside.toPath());
            assertFalse(ModManager.deleteManagedMod(context, link));
            assertTrue(outside.exists());
        } catch (UnsupportedOperationException | java.io.IOException ignored) {
            // Some Android test filesystems cannot create symbolic links.
        }
    }

    @Test public void managedDeleteBackendHandlesFilesAndNestedFolders() throws Exception {
        File archive = new File(mods, "Archive.big");
        Files.write(archive.toPath(), new byte[] {1});
        assertTrue(ModManager.deleteManagedMod(context, archive));
        assertFalse(archive.exists());

        File folder = new File(mods, "Folder");
        assertTrue(new File(folder, "nested").mkdirs());
        Files.write(new File(folder, "nested/data.big").toPath(), new byte[] {2});
        assertTrue(ModManager.deleteManagedMod(context, folder));
        assertFalse(folder.exists());
    }

    @Test public void cancellingPickerAndImportChoiceDoesNotTouchExistingFiles() throws Exception {
        File mod = new File(mods, "Existing.big");
        Files.write(mod.toPath(), new byte[] {1,2,3});
        assertTrue(ModManager.setActiveMod(context, mod));
        open();
        button(activity.getWindow().getDecorView(), R.string.mods_import_title).performClick();
        AlertDialog choices = ShadowAlertDialog.getLatestAlertDialog();
        choices.getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
        activity.onActivityResult(2102, Activity.RESULT_CANCELED,
            new Intent().setData(Uri.fromFile(mod)));
        assertArrayEquals(new byte[] {1,2,3}, Files.readAllBytes(mod.toPath()));
        assertEquals(mod, ModManager.getActiveMod(context));
        assertFalse(new File(mods, ".installing").exists());
    }

    @Test @Config(sdk = 28, qualifiers = "w320dp-h640dp-mdpi")
    public void arabicControlsRemainUsableOnNarrowScreens() throws Exception {
        LocaleHelper.setSavedLanguageTag(context, "ar");
        File mod = new File(mods, "Installed fixture");
        assertTrue(mod.mkdir());
        open();
        label(activity.getString(R.string.mods_library_subtitle));
        View root = activity.getWindow().getDecorView();
        root.measure(View.MeasureSpec.makeMeasureSpec(320, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(640, View.MeasureSpec.EXACTLY));
        root.layout(0, 0, 320, 640);
        assertEquals(View.LAYOUT_DIRECTION_RTL, activity.getResources().getConfiguration().getLayoutDirection());
        MaterialButton importMod = button(root, R.string.mods_import_title);
        MaterialButton vanilla = button(root, R.string.mods_use_vanilla);
        assertTrue(importMod.getWidth() >= 130);
        assertTrue(vanilla.getWidth() >= 130);
        assertTrue(importMod.getHeight() >= 48);
        assertTrue(vanilla.getHeight() >= 48);
    }

    @Test public void importProgressIsIndeterminateAndLeavesInstalledStateUntouched() throws Exception {
        File installed = new File(mods, "Installed.big");
        Files.write(installed.toPath(), new byte[] {1,2,3});
        assertTrue(ModManager.setActiveMod(context, installed));
        open();
        java.util.concurrent.CountDownLatch entered = new java.util.concurrent.CountDownLatch(1);
        java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
        Uri uri = Uri.parse("content://test.mod.documents/Controlled.big");
        java.io.InputStream blocked = new java.io.ByteArrayInputStream(new byte[32]) {
            @Override public synchronized int read(byte[] b, int off, int len) {
                entered.countDown();
                try { assertTrue(release.await(10, TimeUnit.SECONDS)); }
                catch (InterruptedException e) { throw new AssertionError(e); }
                return super.read(b, off, len);
            }
        };
        shadowOf(activity.getContentResolver()).registerInputStream(uri, blocked);
        activity.onActivityResult(2102, Activity.RESULT_OK, new Intent().setData(uri));
        assertTrue(entered.await(10, TimeUnit.SECONDS));
        try {
            AlertDialog progress = ShadowAlertDialog.getLatestAlertDialog();
            assertTrue(progress.isShowing());
            boolean spinner = false;
            for (View view : views(progress.getWindow().getDecorView())) {
                if (view instanceof ProgressBar) {
                    assertTrue(((ProgressBar) view).isIndeterminate());
                    spinner = true;
                }
            }
            assertTrue(spinner);
            assertNotNull(progress.getButton(AlertDialog.BUTTON_NEGATIVE));
            assertEquals(activity.getString(R.string.mods_import_cancel_action),
                progress.getButton(AlertDialog.BUTTON_NEGATIVE).getText().toString());
            assertEquals(installed, ModManager.getActiveMod(context));
            assertArrayEquals(new byte[] {1,2,3}, Files.readAllBytes(installed.toPath()));
        } finally {
            release.countDown();
        }
        Field running = ModManagerActivity.class.getDeclaredField("importRunning");
        running.setAccessible(true);
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        while ((boolean) running.get(activity) && System.nanoTime() < deadline) {
            ShadowLooper.idleMainLooper();
            Thread.sleep(10);
        }
        assertFalse((boolean) running.get(activity));
        assertEquals(installed, ModManager.getActiveMod(context));
        assertEquals(1, ModManager.listMods(context).size());
    }

    @Test public void setupKeepsItsExistingRotationGuardBeforeNativeLaunch() {
        Intent intent = new Intent(context, SetupActivity.class)
            .putExtra(SetupActivity.EXTRA_LAUNCH_FROM_MODS, true);
        ActivityController<SetupActivity> setup = Robolectric.buildActivity(SetupActivity.class, intent).setup();
        SetupActivity launcher = setup.get();
        ShadowLooper.idleMainLooper();
        assertNull(shadowOf(launcher).getNextStartedActivity());
        android.content.res.Configuration landscape = new android.content.res.Configuration(
            launcher.getResources().getConfiguration());
        landscape.orientation = android.content.res.Configuration.ORIENTATION_LANDSCAPE;
        launcher.onConfigurationChanged(landscape);
        Intent gameIntent = shadowOf(launcher).getNextStartedActivity();
        assertNotNull(gameIntent);
        assertEquals(GeneralsZHActivity.class.getName(), gameIntent.getComponent().getClassName());
        assertFalse(launcher.getIntent().hasExtra(SetupActivity.EXTRA_LAUNCH_FROM_MODS));
        setup.pause().stop().destroy();
    }

    @Test public void searchFiltersOnlyCachedCardsAndCancelPreservesChoice() throws Exception {
        File first = new File(mods, "ExistingFixture.big");
        File second = new File(mods, "OtherInstalled.big");
        Files.write(first.toPath(), new byte[] {1,2,3});
        Files.write(second.toPath(), new byte[] {4,5,6});
        assertTrue(ModManager.setActiveMod(context, first));
        open();
        View search = null;
        for (View view : views(activity.getWindow().getDecorView())) {
            if (activity.getString(R.string.launcher_search_mods).equals(view.getContentDescription())) search = view;
        }
        assertNotNull(search);
        search.performClick();
        AlertDialog dialog = ShadowAlertDialog.getLatestAlertDialog();
        android.widget.EditText input = null;
        for (View view : views(dialog.getWindow().getDecorView())) {
            if (view instanceof android.widget.EditText) input = (android.widget.EditText)view;
        }
        assertNotNull(input);
        input.setText("OTHER");
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).performClick();
        ShadowLooper.idleMainLooper();
        label(second.getName());
        for (View view : views(activity.getWindow().getDecorView())) {
            if (view instanceof TextView) assertNotEquals(first.getName(), ((TextView)view).getText().toString());
        }
        search.performClick();
        ShadowAlertDialog.getLatestAlertDialog().getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
        label(second.getName());
        assertEquals(first, ModManager.getActiveMod(context));
        assertEquals(2, ModManager.listMods(context).size());
        assertArrayEquals(new byte[]{1,2,3}, Files.readAllBytes(first.toPath()));
    }

    @Test public void libraryNavigationReturnsToExistingGraphicsTabWithoutChangingMod() throws Exception {
        File installed = new File(mods, "Existing.big");
        Files.write(installed.toPath(), new byte[] {1,2,3});
        assertTrue(ModManager.setActiveMod(context, installed));
        open();
        com.google.android.material.bottomnavigation.BottomNavigationView nav = null;
        for (View view : views(activity.getWindow().getDecorView())) {
            if (view instanceof com.google.android.material.bottomnavigation.BottomNavigationView)
                nav = (com.google.android.material.bottomnavigation.BottomNavigationView)view;
        }
        assertNotNull(nav);
        nav.setSelectedItemId(SetupActivity.TAB_GRAPHICS);
        Intent intent = shadowOf(activity).getNextStartedActivity();
        assertEquals(SetupActivity.class.getName(), intent.getComponent().getClassName());
        assertEquals(SetupActivity.TAB_GRAPHICS, intent.getIntExtra(SetupActivity.EXTRA_OPEN_TAB, -1));
        assertEquals(installed, ModManager.getActiveMod(context));
    }

    @Test @GraphicsMode(GraphicsMode.Mode.NATIVE)
    public void longNamesFitSmallScreenAndCaptureActualViews() throws Exception {
        String name = new String(new char[220]).replace('\0', 'M');
        File mod = new File(mods, name);
        assertTrue(mod.mkdir());
        Files.write(new File(mod, "fixture.big").toPath(), new byte[1024]);
        assertTrue(ModManager.setActiveMod(context, mod));
        open();
        TextView title = label(name);
        assertEquals(2, title.getMaxLines());
        View root = activity.getWindow().getDecorView();
        root.measure(View.MeasureSpec.makeMeasureSpec(360, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(760, View.MeasureSpec.EXACTLY));
        root.layout(0, 0, 360, 760);
        for (int id : new int[] {R.string.mods_launch_button, R.string.mods_activate_button}) {
            assertTrue(button(card(mod), id).getWidth() >= 80);
            assertTrue(button(card(mod), id).getHeight() >= 48);
        }
        assertTrue(action(card(mod), R.string.mods_delete_button).getWidth() >= 48);
        assertTrue(action(card(mod), R.string.mods_delete_button).getHeight() >= 48);
        String destination = System.getProperty("modUiScreenshot");
        if (destination != null) {
            Bitmap bitmap = Bitmap.createBitmap(360, 760, Bitmap.Config.ARGB_8888);
            root.draw(new Canvas(bitmap));
            try (FileOutputStream out = new FileOutputStream(destination)) {
                assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, out));
            }
        }
    }
}
