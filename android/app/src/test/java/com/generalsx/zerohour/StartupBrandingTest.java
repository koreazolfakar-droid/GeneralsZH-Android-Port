package com.generalsx.zerohour;

import android.content.Context;
import android.content.res.TypedArray;
import android.graphics.drawable.BitmapDrawable;
import android.view.ContextThemeWrapper;
import android.os.Build;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;
import static org.junit.Assert.*;

// GeneralsX @bugfix Codex 04/10/2026 Startup resources across pre-12/12/current Android.
@RunWith(RobolectricTestRunner.class)
@Config(sdk = {28, 31, 35})
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class StartupBrandingTest {
    @Test public void startupUsesTransparentSquareEmblemAndRestoresMaterialUi() {
        Context context = RuntimeEnvironment.getApplication();
        UpdateManager.setAutoCheckEnabled(context, false);
        BitmapDrawable emblem = (BitmapDrawable) context.getDrawable(R.drawable.startup_emblem);
        assertNotNull(emblem);
        assertEquals(emblem.getIntrinsicWidth(), emblem.getIntrinsicHeight());
        assertTrue(emblem.getBitmap().hasAlpha());
        ContextThemeWrapper startup = new ContextThemeWrapper(context, R.style.Theme_GeneralsZHStartup);
        if (Build.VERSION.SDK_INT >= 31) {
            TypedArray attrs = startup.obtainStyledAttributes(new int[] {
                android.R.attr.windowSplashScreenAnimatedIcon,
                android.R.attr.windowSplashScreenBackground
            });
            try {
                assertEquals(R.drawable.startup_emblem, attrs.getResourceId(0, 0));
                assertEquals(context.getColor(R.color.gzh_startup_background), attrs.getColor(1, 0));
            } finally { attrs.recycle(); }
        }
        try (org.robolectric.android.controller.ActivityController<SetupActivity> controller =
                Robolectric.buildActivity(SetupActivity.class).setup()) {
            SetupActivity activity = controller.get();
            TypedArray attrs = activity.obtainStyledAttributes(new int[] {android.R.attr.windowBackground});
            try { assertEquals(R.color.gzh_background, attrs.getResourceId(0, 0)); }
            finally { attrs.recycle(); }
            assertNotNull(activity.findViewById(android.R.id.content));
        }
    }
}
