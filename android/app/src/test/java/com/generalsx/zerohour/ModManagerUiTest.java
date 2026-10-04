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

    private View card(File mod) { return (View) label(mod.getName()).getParent().getParent().getParent(); }

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
        assertTrue(button(card(mod), R.string.mods_launch_button).getWidth() > 100);
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
