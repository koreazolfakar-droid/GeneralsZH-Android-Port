package com.generalsx.zerohour;

import android.app.Activity;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.Menu;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.PopupMenu;
import android.widget.TextView;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.google.android.material.navigation.NavigationBarView;

// GeneralsX @feature Android port 04/10/2026 Shared native launcher presentation only.
// No game, storage, import, update, account, or renderer state is owned here.
final class LauncherUi {
    // GeneralsX @feature 10/10/2026 Resolve semantic tokens from the Activity's selected theme.
    static int background(Activity a) { return UiKit.color(a, R.color.gzh_background); }
    static int surface(Activity a) { return UiKit.color(a, R.color.gzh_surface_container); }
    static int outline(Activity a) { return UiKit.color(a, R.color.gzh_outline); }
    static int textColor(Activity a) { return UiKit.color(a, R.color.gzh_on_surface); }
    static int muted(Activity a) { return UiKit.color(a, R.color.gzh_on_surface_variant); }
    static int primary(Activity a) { return UiKit.color(a, R.color.gzh_primary); }
    static int warning(Activity a) { return UiKit.color(a, R.color.gzh_status_warn); }
    static int success(Activity a) { return UiKit.color(a, R.color.gzh_status_ok); }
    private LauncherUi() {}

    static int dp(Activity a, int value) { return UiKit.dp(a, value); }

    static LinearLayout column(Activity a) {
        LinearLayout v = new LinearLayout(a);
        v.setOrientation(LinearLayout.VERTICAL);
        return v;
    }

    static GradientDrawable shape(Activity a, int fill, int border, int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fill);
        d.setCornerRadius(dp(a, radius));
        d.setStroke(dp(a, 1), border);
        return d;
    }

    static LinearLayout panel(Activity a, LinearLayout parent) {
        LinearLayout body = column(a);
        body.setPadding(dp(a, 12), dp(a, 12), dp(a, 12), dp(a, 12));
        body.setBackground(shape(a, surface(a), outline(a), 16));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.topMargin = dp(a, 12);
        parent.addView(body, lp);
        return body;
    }

    static TextView text(Activity a, LinearLayout parent, CharSequence label,
                         int size, int color, boolean bold) {
        TextView v = new TextView(a);
        v.setText(label);
        v.setTextSize(size);
        v.setTextColor(color);
        if (bold) v.setTypeface(Typeface.DEFAULT_BOLD);
        v.setMaxLines(2);
        v.setEllipsize(TextUtils.TruncateAt.END);
        parent.addView(v, new LinearLayout.LayoutParams(-1, -2));
        return v;
    }

    static FrameLayout artwork(Activity a, LinearLayout parent, int height) {
        FrameLayout frame = new FrameLayout(a);
        frame.setBackground(shape(a, surface(a), outline(a), 18));
        frame.setClipToOutline(true);
        parent.addView(frame, new LinearLayout.LayoutParams(-1, dp(a, height)));
        ImageView image = new ImageView(a);
        image.setImageResource(R.drawable.launcher_battlefield);
        image.setScaleType(ImageView.ScaleType.CENTER_CROP);
        image.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        frame.addView(image, new FrameLayout.LayoutParams(-1, -1));
        return frame;
    }

    static void purple(Activity a, MaterialButton button) {
        // Legacy method name retained for old callers; the color is now warm gold.
        button.setCornerRadius(dp(a, 15));
        button.setTextColor(UiKit.color(a, R.color.gzh_on_primary));
        button.setIconTint(ColorStateList.valueOf(UiKit.color(a, R.color.gzh_on_primary)));
        button.setBackgroundTintList(ColorStateList.valueOf(primary(a)));
        button.setStrokeColor(ColorStateList.valueOf(primary(a)));
    }

    /** Gold-accented illustrated destination card; the entire row is tappable. */
    // GeneralsX @feature ChatGPT 10/10/2026 Real linked rows, not decoration-only cards.
    static TextView row(Activity a, LinearLayout parent, int icon, int title,
                        CharSequence value, Runnable action) {
        boolean dark = ThemeHelper.isDark(a);
        FrameLayout frame = new FrameLayout(a);
        frame.setClipToOutline(true);
        frame.setBackground(shape(a, surface(a), outline(a), 18));
        LinearLayout.LayoutParams frameParams = new LinearLayout.LayoutParams(-1, -2);
        frameParams.topMargin = dp(a, 10);
        parent.addView(frame, frameParams);

        ImageView battlefield = new ImageView(a);
        battlefield.setImageResource(R.drawable.launcher_battlefield);
        battlefield.setScaleType(ImageView.ScaleType.CENTER_CROP);
        battlefield.setAlpha(dark ? 0.18f : 0.055f);
        battlefield.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        frame.addView(battlefield, new FrameLayout.LayoutParams(-1, -1));

        LinearLayout body = new LinearLayout(a);
        body.setOrientation(LinearLayout.HORIZONTAL);
        body.setGravity(Gravity.CENTER_VERTICAL);
        body.setPadding(dp(a, 14), dp(a, 13), dp(a, 14), dp(a, 13));
        GradientDrawable scrim = new GradientDrawable(
            GradientDrawable.Orientation.LEFT_RIGHT,
            dark ? new int[]{0xff081724,0xf00a1b2b,0x9b0a1b2b}
                 : new int[]{0xffffffff,0xfaf7f9fc,0xdbf7f9fc});
        body.setBackground(scrim);
        frame.addView(body, new FrameLayout.LayoutParams(-1, -2));

        ImageView glyph = new ImageView(a);
        glyph.setImageResource(icon);
        glyph.setImageTintList(ColorStateList.valueOf(primary(a)));
        glyph.setPadding(dp(a, 12), dp(a, 12), dp(a, 12), dp(a, 12));
        glyph.setBackground(shape(a, dark ? 0xff132435 : 0xfffcefd4,
            dark ? 0xff77582a : 0xffbd9957, 14));
        LinearLayout.LayoutParams glyphParams = new LinearLayout.LayoutParams(dp(a, 52), dp(a, 52));
        glyphParams.setMarginEnd(dp(a, 13));
        body.addView(glyph, glyphParams);

        LinearLayout labels = column(a);
        body.addView(labels, new LinearLayout.LayoutParams(0, -2, 1));
        TextView heading = text(a, labels, a.getString(title), 17, textColor(a), true);
        heading.setMaxLines(2);
        TextView status = text(a, labels, value, 12, muted(a), false);
        status.setMaxLines(3);

        if (action != null) {
            ImageView next = new ImageView(a);
            next.setImageResource(R.drawable.ic_gzh_chevron);
            next.setImageTintList(ColorStateList.valueOf(muted(a)));
            body.addView(next, new LinearLayout.LayoutParams(dp(a, 20), dp(a, 20)));
            body.setContentDescription(a.getString(title));
            body.setClickable(true);
            body.setFocusable(true);
            body.setOnClickListener(v -> action.run());
            body.setForeground(new android.graphics.drawable.RippleDrawable(
                UiKit.tint(a, R.color.gzh_ripple_primary), null,
                shape(a, 0xffffffff, 0xffffffff, 18)));
        }
        return status;
    }

    static void open(Activity a, int tab) {
        a.startActivity(new Intent(a, SetupActivity.class).putExtra(SetupActivity.EXTRA_OPEN_TAB, tab));
    }

    static void settings(Activity a, View anchor, java.util.function.IntConsumer navigate) {
        PopupMenu menu = new PopupMenu(a, anchor);
        menu.getMenu().add(0, SetupActivity.TAB_INTERFACE, 0, R.string.nav_tab_interface);
        menu.getMenu().add(0, SetupActivity.TAB_HELP, 1, R.string.nav_tab_help);
        menu.setOnMenuItemClickListener(item -> { navigate.accept(item.getItemId()); return true; });
        menu.show();
    }

    // Bottom rail stays distinct from the scrolling Home background.
    private static int darkNavigationColor(Activity a) {
        return ThemeHelper.isDark(a) ? 0xff091826 : UiKit.color(a, R.color.gzh_surface);
    }

    static BottomNavigationView navigation(Activity a, int selected,
                                            java.util.function.IntConsumer navigate) {
        BottomNavigationView nav = new BottomNavigationView(a);
        nav.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        nav.setTextDirection(View.TEXT_DIRECTION_LOCALE);
        nav.setBackground(shape(a, darkNavigationColor(a), outline(a), 22));
        nav.setElevation(0);
        nav.setMinimumHeight(dp(a, 68));
        nav.setItemPaddingTop(dp(a, 6));
        nav.setItemPaddingBottom(dp(a, 6));
        nav.setLabelVisibilityMode(NavigationBarView.LABEL_VISIBILITY_LABELED);
        nav.setItemIconSize(dp(a, 24));
        ColorStateList tint = new ColorStateList(new int[][]{{android.R.attr.state_checked}, {}},
            new int[]{primary(a), muted(a)});
        nav.setItemTextColor(tint);
        nav.setItemIconTintList(tint);
        nav.setItemActiveIndicatorColor(UiKit.tint(a, R.color.gzh_primary_container));
        nav.setItemRippleColor(UiKit.tint(a, R.color.gzh_ripple_primary));
        Menu menu = nav.getMenu();
        menu.add(0, SetupActivity.TAB_HOME, 0, R.string.nav_tab_home).setIcon(R.drawable.ic_gzh_home);
        menu.add(0, SetupActivity.TAB_MODS, 1, R.string.mods_title).setIcon(R.drawable.ic_gzh_folder);
        menu.add(0, SetupActivity.TAB_GRAPHICS, 2, R.string.nav_tab_graphics).setIcon(R.drawable.ic_gzh_display);
        menu.add(0, SetupActivity.TAB_TOOLS, 3, R.string.nav_tab_tools).setIcon(R.drawable.ic_gzh_wrench);
        nav.setSelectedItemId(selected);
        nav.setOnItemSelectedListener(item -> {
            navigate.accept(item.getItemId());
            return item.getItemId() != SetupActivity.TAB_MODS || selected == SetupActivity.TAB_MODS;
        });
        return nav;
    }
}
