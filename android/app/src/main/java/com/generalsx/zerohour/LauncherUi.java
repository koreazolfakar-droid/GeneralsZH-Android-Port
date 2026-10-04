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
    static final int BACKGROUND = 0xff090d14, SURFACE = 0xff121621,
        OUTLINE = 0xff2b3040, TEXT = 0xfff4f3f9, MUTED = 0xffaaa7bc,
        PURPLE = 0xffb48afa, GOLD = 0xffefc752, GREEN = 0xff58de9b;
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
        body.setBackground(shape(a, SURFACE, OUTLINE, 12));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.topMargin = dp(a, 10);
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
        frame.setBackground(shape(a, SURFACE, OUTLINE, 12));
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
        button.setCornerRadius(dp(a, 10));
        button.setTextColor(BACKGROUND);
        button.setIconTint(ColorStateList.valueOf(BACKGROUND));
        button.setBackgroundTintList(ColorStateList.valueOf(PURPLE));
        button.setStrokeColor(ColorStateList.valueOf(PURPLE));
    }

    static TextView row(Activity a, LinearLayout parent, int icon, int title,
                        CharSequence value, Runnable action) {
        LinearLayout body = panel(a, parent);
        body.setPadding(dp(a, 12), dp(a, 8), dp(a, 12), dp(a, 8));
        ((LinearLayout.LayoutParams)body.getLayoutParams()).topMargin = dp(a, 6);
        body.setOrientation(LinearLayout.HORIZONTAL);
        body.setGravity(Gravity.CENTER_VERTICAL);
        ImageView glyph = new ImageView(a);
        glyph.setImageResource(icon);
        glyph.setImageTintList(ColorStateList.valueOf(PURPLE));
        glyph.setPadding(dp(a, 10), dp(a, 10), dp(a, 10), dp(a, 10));
        glyph.setBackground(shape(a, 0xff242035, 0xff30283f, 10));
        LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(dp(a, 36), dp(a, 36));
        ilp.setMarginEnd(dp(a, 12));
        body.addView(glyph, ilp);
        LinearLayout labels = column(a);
        body.addView(labels, new LinearLayout.LayoutParams(0, -2, 1));
        text(a, labels, a.getString(title), 15, TEXT, true);
        TextView status = text(a, labels, value, 12, MUTED, false);
        if (action != null) {
            ImageView next = new ImageView(a);
            next.setImageResource(R.drawable.ic_gzh_chevron);
            next.setImageTintList(ColorStateList.valueOf(MUTED));
            body.addView(next, new LinearLayout.LayoutParams(dp(a, 18), dp(a, 18)));
            body.setClickable(true);
            body.setFocusable(true);
            body.setOnClickListener(v -> action.run());
            body.setForeground(new android.graphics.drawable.RippleDrawable(
                ColorStateList.valueOf(0x33b48afa), null, shape(a, 0xffffffff, 0xffffffff, 12)));
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
        menu.getMenu().add(0, SetupActivity.TAB_TOOLS, 2, R.string.setup_button_view_logs);
        menu.setOnMenuItemClickListener(item -> { navigate.accept(item.getItemId()); return true; });
        menu.show();
    }

    static BottomNavigationView navigation(Activity a, int selected,
                                            java.util.function.IntConsumer navigate) {
        BottomNavigationView nav = new BottomNavigationView(a);
        nav.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        nav.setTextDirection(View.TEXT_DIRECTION_LOCALE);
        nav.setBackgroundColor(BACKGROUND);
        nav.setElevation(0);
        nav.setMinimumHeight(dp(a, 64));
        nav.setItemPaddingTop(dp(a, 6));
        nav.setItemPaddingBottom(dp(a, 6));
        nav.setLabelVisibilityMode(NavigationBarView.LABEL_VISIBILITY_LABELED);
        nav.setItemIconSize(dp(a, 22));
        ColorStateList tint = new ColorStateList(new int[][]{{android.R.attr.state_checked}, {}},
            new int[]{PURPLE, MUTED});
        nav.setItemTextColor(tint);
        nav.setItemIconTintList(tint);
        nav.setItemActiveIndicatorColor(ColorStateList.valueOf(0xff30204e));
        nav.setItemRippleColor(ColorStateList.valueOf(0x33b48afa));
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
