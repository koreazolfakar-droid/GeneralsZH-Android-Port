package com.generalsx.zerohour;

import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;
import android.view.ViewGroup;
import android.widget.PopupMenu;
import android.widget.TextView;
import android.widget.LinearLayout;
import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.google.android.material.button.MaterialButton;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import java.lang.reflect.Field;
import org.junit.Before;
import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.LooperMode;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.shadows.ShadowLooper;
import org.robolectric.shadows.ShadowPopupMenu;
import static org.robolectric.Shadows.shadowOf;
import static org.junit.Assert.*;

// GeneralsX @feature Android port 04/10/2026 Launcher navigation/feature preservation.
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28, qualifiers = "w393dp-h753dp-mdpi")
@LooperMode(LooperMode.Mode.PAUSED)
public class LauncherHomeUiTest {
    @Rule public TemporaryFolder temp = new TemporaryFolder();
    private Context context;
    private File game;
    private ActivityController<SetupActivity> controller;
    private SetupActivity activity;

    @Before public void setUp() throws Exception {
        context = RuntimeEnvironment.getApplication();
        game = temp.newFolder("game");
        context.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE).edit()
            .clear().putString(SetupActivity.PREF_GAME_PATH, game.getAbsolutePath()).commit();
        UpdateManager.setAutoCheckEnabled(context, false);
    }
    @After public void tearDown() {
        if (controller != null) controller.pause().stop().destroy();
    }
    private void open() {
        controller = Robolectric.buildActivity(SetupActivity.class).setup();
        activity = controller.get();
        assertNotNull(field("heroReady")); // material failure must not silently use fallback
    }
    private Object field(String name) {
        try {
            Field f = SetupActivity.class.getDeclaredField(name);
            f.setAccessible(true);
            return f.get(activity);
        } catch (Exception e) { throw new AssertionError(e); }
    }
    private List<View> views(View root) {
        List<View> list = new ArrayList<>();
        list.add(root);
        if (root instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) root;
            for (int i=0;i<group.getChildCount();i++) list.addAll(views(group.getChildAt(i)));
        }
        return list;
    }
    private TextView label(int id) {
        String text = activity.getString(id);
        for (View view : views(activity.getWindow().getDecorView())) {
            if (view instanceof TextView && text.equals(((TextView)view).getText().toString())) return (TextView)view;
        }
        throw new AssertionError("Missing existing feature: " + text);
    }
    private void click(int id) {
        View view = label(id);
        while (!view.isClickable() && view.getParent() instanceof View) view = (View)view.getParent();
        assertTrue("Action must remain clickable", view.performClick());
    }
    private void settings(int destination) {
        for (View view : views(activity.getWindow().getDecorView())) {
            if (activity.getString(R.string.launcher_settings).contentEquals(
                    view.getContentDescription() == null ? "" : view.getContentDescription())) {
                view.performClick();
                PopupMenu popup = ShadowPopupMenu.getLatestPopupMenu();
                assertNotNull(popup);
                assertTrue(popup.getMenu().performIdentifierAction(destination, 0));
                return;
            }
        }
        throw new AssertionError("Settings action unavailable");
    }
    private void completeGame() throws Exception {
        String[] archives = {"INI.big","Terrain.big","Textures.big","W3D.big","Window.big",
            "Shaders.big","Audio.big","Speech.big","Maps.big","Music.big","INIZH.big"};
        byte[] empty = ByteBuffer.allocate(16).put("BIGF".getBytes(StandardCharsets.US_ASCII))
            .putInt(16).putInt(0).putInt(16).array();
        for (String name: archives) Files.write(new File(game,name).toPath(),empty);
        byte[] weather = "Data\\INI\\Default\\Weather.ini".getBytes(StandardCharsets.US_ASCII);
        int header = 16 + 8 + weather.length + 1;
        byte[] ini = ByteBuffer.allocate(header+1).put("BIGF".getBytes(StandardCharsets.US_ASCII))
            .putInt(header+1).putInt(1).putInt(header).putInt(header).putInt(1)
            .put(weather).put((byte)0).put((byte)0).array();
        Files.write(new File(game,"INI.big").toPath(),ini);
    }
    @Test public void readinessUsesExistingIntegrityChecksAndReflectsMissingFiles() throws Exception {
        completeGame();
        open();
        assertEquals(activity.getString(R.string.launcher_ready), ((TextView)field("heroReady")).getText().toString());
        assertTrue(new File(game,"Textures.big").delete());
        controller.pause().resume();
        assertEquals(activity.getString(R.string.launcher_setup_needed), ((TextView)field("heroReady")).getText().toString());
        assertEquals(((TextView)field("heroReady")).getText(), ((TextView)field("homeGameSummary")).getText());
    }
    @Test public void missingGameDataNeverReportsReadyAndOriginalFolderActionsRemain() {
        open();
        assertEquals(activity.getString(R.string.launcher_setup_needed), ((TextView)field("heroReady")).getText().toString());
        click(R.string.setup_card_game_folder);
        assertEquals(View.VISIBLE, ((LinearLayout)field("homeGameData")).getVisibility());
        label(R.string.setup_button_select_game_folder);
        label(R.string.setup_button_select_base_generals);
        label(R.string.setup_button_clear_game_folder);
        assertEquals(game.getAbsolutePath(), SetupActivity.getSavedGamePath(context));
    }
    @Test public void settingsRetainsInterfaceHelpAndLogsDestinations() {
        open();
        settings(SetupActivity.TAB_INTERFACE);
        label(R.string.setup_card_language);
        label(R.string.setup_card_text_size);
        label(R.string.setup_card_interface_scale);
        assertEquals(View.GONE, ((TextView) field("interfaceScaleWarning")).getVisibility());
        ((com.google.android.material.slider.Slider) field("interfaceScaleSlider")).setValue(150f);
        assertEquals(View.VISIBLE, ((TextView) field("interfaceScaleWarning")).getVisibility());
        settings(SetupActivity.TAB_HELP);
        label(R.string.setup_card_how_it_works);
        ((BottomNavigationView)field("bottomNav")).setSelectedItemId(SetupActivity.TAB_TOOLS);
        label(R.string.setup_card_diagnostics);
        click(R.string.setup_button_view_logs);
        assertEquals(LogViewerActivity.class.getName(), shadowOf(activity).getNextStartedActivity().getComponent().getClassName());
    }

    @Test public void toolsReportsRealAudioArchiveReadiness() throws Exception {
        completeGame();
        open();
        ((BottomNavigationView) field("bottomNav")).setSelectedItemId(SetupActivity.TAB_TOOLS);
        assertEquals(activity.getString(R.string.setup_audio_check_ready),
            ((TextView) field("audioArchiveStatus")).getText().toString());
        assertNotNull(label(R.string.setup_switch_gx_audio_trace));
        assertTrue(new File(game, "Audio.big").delete());
        ((BottomNavigationView) field("bottomNav")).setSelectedItemId(SetupActivity.TAB_HOME);
        ((BottomNavigationView) field("bottomNav")).setSelectedItemId(SetupActivity.TAB_TOOLS);
        assertTrue(((TextView) field("audioArchiveStatus")).getText().toString().contains("Audio.big"));
    }
    @Test public void navigationPreservesGraphicsToolsAndModManagerRoutes() {
        open();
        ((BottomNavigationView)field("bottomNav")).setSelectedItemId(SetupActivity.TAB_GRAPHICS);
        label(R.string.setup_card_sim_rate);
        label(R.string.setup_card_render_backend);
        BottomNavigationView nav = (BottomNavigationView)field("bottomNav");
        nav.setSelectedItemId(SetupActivity.TAB_TOOLS);
        label(R.string.setup_card_diagnostics);
        nav.setSelectedItemId(SetupActivity.TAB_HOME);
        nav.setSelectedItemId(SetupActivity.TAB_MODS);
        assertEquals(ModManagerActivity.class.getName(), shadowOf(activity).getNextStartedActivity().getComponent().getClassName());
        assertEquals(game.getAbsolutePath(), SetupActivity.getSavedGamePath(context));
    }
    // GeneralsX @tweak Android port 04/10/2026 Guard against duplicate visible destinations.
    @Test public void homeOffersSingleVisibleEntryForEachNavigationDestination() {
        open();
        int[] destinations = {R.string.mods_title, R.string.nav_tab_graphics, R.string.nav_tab_tools};
        for (int id : destinations) {
            int matches = 0;
            for (View v : views(activity.getWindow().getDecorView())) {
                if (v instanceof TextView && v.isShown()
                        && activity.getString(id).contentEquals(((TextView)v).getText())) matches++;
            }
            assertEquals("Only the bottom navigation should offer this destination", 1, matches);
        }
        assertEquals(activity.getString(R.string.mods_active_vanilla),
            ((TextView)field("heroMod")).getText().toString());
        click(R.string.setup_card_game_folder);
        assertEquals(View.VISIBLE, ((LinearLayout)field("homeGameData")).getVisibility());
        label(R.string.setup_button_select_game_folder);
        settings(SetupActivity.TAB_INTERFACE);
        assertEquals(2, ShadowPopupMenu.getLatestPopupMenu().getMenu().size());
        assertNull(ShadowPopupMenu.getLatestPopupMenu().getMenu().findItem(SetupActivity.TAB_TOOLS));
    }

    // GeneralsX @feature 10/10/2026 Test reference-driven navy and gold Home
    // while guarding original interactive destinations and runtime values.
    @Test public void navyGoldHomeRetainsLiveStateAndLatestUpdateLink() {
        open();
        assertEquals(0xffffc84c, LauncherUi.primary(activity));
        assertNotNull(field("heroMod"));
        assertNotNull(field("homeEngineSummary"));
        assertNotNull(field("homeAccountSummary"));
        assertNotNull(label(R.string.launcher_latest_updates));
        assertNotNull(label(R.string.launcher_play_now));
        assertEquals(activity.getString(R.string.launcher_build_value, UpdateManager.bundledEngineSeq(context)),
            ((TextView) field("homeEngineSummary")).getText().toString());
        click(R.string.launcher_latest_updates);
        assertEquals(View.VISIBLE, ((LinearLayout) field("homeUpdateDetails")).getVisibility());
        label(R.string.setup_button_check_updates);
    }

    @Test public void daylightGoldHomePreservesFolderAndThemeSettings() {
        ThemeHelper.setMode(context, ThemeHelper.LIGHT);
        try {
            open();
            assertFalse(ThemeHelper.isDark(activity));
            assertEquals(0xff895300, LauncherUi.primary(activity));
            click(R.string.setup_card_game_folder);
            assertEquals(View.VISIBLE, ((LinearLayout) field("homeGameData")).getVisibility());
            settings(SetupActivity.TAB_INTERFACE);
            label(R.string.setup_appearance_title);
        } finally {
            ThemeHelper.setMode(context, ThemeHelper.DARK);
        }
    }

    @Test public void onlineAndSignedUpdateControlsRemainReachable() {
        open();
        click(R.string.setup_card_online);
        assertEquals(View.VISIBLE, ((LinearLayout)field("homeOnlineDetails")).getVisibility());
        label(R.string.setup_online_anticheat_note);
        click(R.string.setup_button_online_account);
        assertEquals(GeneralsOnlineActivity.class.getName(), shadowOf(activity).getNextStartedActivity().getComponent().getClassName());
        click(R.string.setup_card_updates);
        assertEquals(View.VISIBLE, ((LinearLayout)field("homeUpdateDetails")).getVisibility());
        label(R.string.setup_button_check_updates);
        label(R.string.setup_switch_auto_updates);
        label(R.string.setup_button_open_online_data);
        assertEquals(activity.getString(R.string.launcher_build_value, UpdateManager.bundledEngineSeq(context)),
            ((TextView)field("homeEngineSummary")).getText().toString());
    }
    @Test @Config(sdk=28, qualifiers="w320dp-h640dp-mdpi")
    public void arabicHomeKeepsTouchTargetsAndModLaunchKeepsSavedChoice() throws Exception {
        LocaleHelper.setSavedLanguageTag(context,"ar");
        File mod = new File(game,"Mods/Long existing installed mod name");
        assertTrue(mod.mkdirs());
        assertTrue(ModManager.setActiveMod(context,mod));
        open();
        assertEquals(View.LAYOUT_DIRECTION_RTL, activity.getResources().getConfiguration().getLayoutDirection());
        View root = activity.getWindow().getDecorView();
        root.measure(View.MeasureSpec.makeMeasureSpec(320,View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(640,View.MeasureSpec.EXACTLY));
        root.layout(0,0,320,640);
        TextView play = label(R.string.launcher_play_now);
        assertTrue(play.getHeight()>=48);
        assertTrue(play.getWidth()>200);
        play.performClick();
        assertEquals(mod,ModManager.getActiveMod(context));
        assertNull(shadowOf(activity).getNextStartedActivity()); // same original rotation gate
        android.content.res.Configuration landscape = new android.content.res.Configuration(activity.getResources().getConfiguration());
        landscape.orientation = android.content.res.Configuration.ORIENTATION_LANDSCAPE;
        activity.onConfigurationChanged(landscape);
        assertEquals(GeneralsZHActivity.class.getName(), shadowOf(activity).getNextStartedActivity().getComponent().getClassName());
    }
    @Test public void playOptionsOpensExistingSimulationSettingsWithoutChangingRate() {
        open();
        int originalHz = SetupActivity.getSimHz(context);
        for (View view : views(activity.getWindow().getDecorView())) {
            if (activity.getString(R.string.launcher_play_options).equals(view.getContentDescription())) {
                view.performClick();
                PopupMenu popup = ShadowPopupMenu.getLatestPopupMenu();
                assertEquals(1, popup.getMenu().size());
                assertTrue(popup.getMenu().performIdentifierAction(SetupActivity.TAB_GRAPHICS, 0));
                label(R.string.setup_card_sim_rate);
                assertEquals(originalHz, SetupActivity.getSimHz(context));
                return;
            }
        }
        fail("Play options are not reachable");
    }

    @Test @GraphicsMode(GraphicsMode.Mode.NATIVE)
    public void renderHomeAndRealInstalledLibraryAtReferenceViewport() throws Exception {
        completeGame();
        File first = new File(game,"Mods/Installed Mod");
        assertTrue(first.mkdirs());
        Files.write(new File(first,"fixture.big").toPath(),new byte[1024]);
        byte[] big = ByteBuffer.allocate(16).put("BIGF".getBytes(StandardCharsets.US_ASCII)).putInt(16).putInt(0).putInt(16).array();
        Files.write(new File(game,"Mods/Another Installed Mod.big").toPath(),big);
        assertTrue(ModManager.setActiveMod(context,first));
        open();
        assertEquals("Installed Mod",((TextView)field("heroMod")).getText().toString());
        capture(activity.getWindow().getDecorView(),"-home.png");
        ActivityController<ModManagerActivity> library = Robolectric.buildActivity(ModManagerActivity.class).setup();
        try {
            Field worker = ModManagerActivity.class.getDeclaredField("libraryWorker");
            worker.setAccessible(true);
            ((ExecutorService)worker.get(library.get())).submit(() -> {}).get(10,TimeUnit.SECONDS);
            ShadowLooper.idleMainLooper();
            capture(library.get().getWindow().getDecorView(),"-library.png");
            assertEquals(2,ModManager.listMods(context).size());
        } finally { library.pause().stop().destroy(); }
    }
    private void capture(View root,String suffix) throws Exception {
        root.measure(View.MeasureSpec.makeMeasureSpec(393,View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(753,View.MeasureSpec.EXACTLY));
        root.layout(0,0,393,753);
        String base = System.getProperty("modUiScreenshot");
        if (base != null) {
            Bitmap bitmap = Bitmap.createBitmap(393,753,Bitmap.Config.ARGB_8888);
            root.draw(new Canvas(bitmap));
            try (FileOutputStream out = new FileOutputStream(base.replace(".png",suffix))) {
                assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG,100,out));
            }
        }
    }
}
